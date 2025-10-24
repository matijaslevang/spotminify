import os, json, uuid, base64, boto3, datetime

s3  = boto3.client("s3")
ddb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
sns = boto3.client("sns")
sqs_client = boto3.client('sqs')

ALBUMS_TABLE  = os.environ["ALBUMS_TABLE"]
SINGLES_TABLE = os.environ["SINGLES_TABLE"]
AUDIO_BUCKET  = os.environ["AUDIO_BUCKET"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]
FILTER_ADD_LAMBDA = os.environ["FILTER_ADD_LAMBDA"]
NEW_CONTENT_TOPIC_ARN = os.environ["NEW_CONTENT_TOPIC_ARN"]
queue_url = os.environ["QUEUE_URL"]
convert_queue_url = os.environ["CONVERT_QUEUE_URL"]

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def _exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key); return True
    except: return False

def handler(event, _):
    try:
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode":403,"headers":cors(),"body":json.dumps({"error":"forbidden"})}

        data = json.loads(event.get("body") or "{}")

        title     = (data.get("title") or data.get("ContentName") or "").strip()
        artistIds = data.get("artistIds") or data.get("Artists") or []
        artistNames = data.get("artistNames") or []
        genres    = data.get("genres")    or data.get("Genres")  or []
        coverKey  = data.get("coverKey")
        tracks    = data.get("tracks") or []

        if not title:  return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"title required"})}
        if not artistIds: return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"artistIds required"})} # <--- DODATO: Validacija za PK
        if not tracks: return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"tracks required"})}
        
        # KLJUČNA IZMENA 1: Ekstrakcija Partition Key-a
        pk_artist_id = artistIds[0]
        
        albumId = f"alb-{uuid.uuid4()}"
        now = datetime.datetime.utcnow().isoformat()

        # album item
        album = {
            "artistId":  {"S": pk_artist_id},      # <--- DODATO: Partition Key za ALBUMS_TABLE
            "albumId":   {"S": albumId},           # <--- Sort Key za ALBUMS_TABLE
            "title":     {"S": title},
            "artistIds": {"SS": artistIds} if artistIds else {"SS":[]},
            "artistNames": {"SS": artistNames} if artistNames else {"SS":[]},
            "genres":    {"SS": genres}    if genres    else {"SS":[]},
            "createdAt": {"S": now},
        }
        if coverKey:
            # opciono HEAD provera
            album["coverKey"] = {"S": f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{coverKey}"}
     
        ddb.put_item(TableName=ALBUMS_TABLE, Item=album)

        content = {
            "artistId":  pk_artist_id,      
            "albumId":   albumId,           
            "title":     title,
            "artistIds":  artistIds if artistIds else [],
            "artistNames": artistNames if artistNames else [],
            "genres":     genres    if genres   else [],
            "createdAt": now,
        }
        if coverKey:
            content["coverKey"] = f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{coverKey}"

        payload_filter = {
            "contentId": albumId,
            "contentType": "album",
            "content": content,
        }
        lambda_client.invoke(
            FunctionName=FILTER_ADD_LAMBDA,
            InvocationType="Event",
            Payload=json.dumps(payload_filter)
        )

        payload_feed = {
            "content": content,
            "contentId": albumId,
            "contentType": "album",
            "genres": json.dumps(list(genres)),
        }
        print("send message")
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload_feed)
        )

        # kreiraj single stavke
        created = []
        for t in tracks:
            stitle  = (t.get("title") or "").strip() or "Track"
            sgenres = t.get("genres")    or []
            sarts   = t.get("artistIds") or artistIds
            sartNames = t.get("artistNames") or artistNames
            akey    = t.get("audioKey")
            trno    = t.get("trackNo")
            ikey    = t.get("imageKey")

            if not akey:
                continue
            if not _exists(AUDIO_BUCKET, akey):
                continue

            single_pk_artist_id = sarts[0] if sarts else pk_artist_id # Koristi se za Single PK
            
            singleId = f"sin-{uuid.uuid4()}"
            item = {
                "artistId":  {"S": single_pk_artist_id}, # <--- DODATO: Partition Key za SINGLES_TABLE
                "singleId":  {"S": singleId},            # <--- Sort Key za SINGLES_TABLE
                "title":     {"S": stitle},
                "artistIds": {"SS": sarts}  if sarts  else {"SS":[]},
                "artistNames": {"SS": sartNames} if sartNames else {"SS":[]},
                "genres":    {"SS": sgenres}if sgenres else {"SS":[]},
                "audioKey":  {"S": f"https://{AUDIO_BUCKET}.s3.amazonaws.com/{akey}"},
                "albumId":   {"S": albumId},
                "createdAt": {"S": now},
            }
            if trno is not None: item["trackNo"] = {"N": str(int(trno))}
            if ikey: item["imageKey"] = {"S": f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{ikey}"}

            ddb.put_item(TableName=SINGLES_TABLE, Item=item)
            created.append({"singleId": singleId, "trackNo": trno})

            content_single = {
                "artistId":  single_pk_artist_id,
                "singleId":  singleId,           
                "title":     stitle,
                "artistIds": sarts if sarts  else [],
                "artistNames": sartNames if sartNames else [],
                "genres":    sgenres if sgenres else [],
                "audioKey":  f"https://{AUDIO_BUCKET}.s3.amazonaws.com/{akey}",
                "albumId":   albumId,
                "createdAt": now,
            }
            if trno is not None: content_single["trackNo"] = int(trno)
            if ikey: content_single["imageKey"] = f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{ikey}"

            payload_filter_single = {
                "contentId": singleId,
                "contentType": "single",
                "content": content_single,
            }
            lambda_client.invoke(
                FunctionName=FILTER_ADD_LAMBDA,
                InvocationType="Event",
                Payload=json.dumps(payload_filter_single)
            )

            payload_feed_two = {
                "content": content_single,
                "contentId": singleId,
                "contentType": "single",
                "genres": json.dumps(list(sgenres)),
            }
            print("send message")
            sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(payload_feed_two)
            )
            payload_convert = {
                "bucket": os.environ["AUDIO_BUCKET"],
                "key": akey,
                "singleId": singleId
            }
            sqs_client.send_message(
                QueueUrl=convert_queue_url,
                MessageBody=json.dumps(payload_convert)
            )

            try:
                sns_message = {
                    'contentType': 'album',
                    'contentId': albumId,
                    'title': title,
                    'artistIds': artistIds, 
                    'artistNames': sartNames,
                    'genres': genres
                }
                sns.publish(
                    TopicArn=NEW_CONTENT_TOPIC_ARN,
                    Message=json.dumps({'default': json.dumps(sns_message)}),
                    MessageStructure='json'
                )
                print(f"Published SNS message for album {albumId}")
            except Exception as sns_error:
                print(f"Error publishing SNS message for album {albumId}: {str(sns_error)}")

        return {"statusCode":201,"headers":cors(),"body":json.dumps({"albumId": albumId, "tracks": created})}
    except Exception as e:
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error":str(e)})}
