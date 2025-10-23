import os, json, uuid, base64, boto3, datetime

s3  = boto3.client("s3")
ddb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
sns = boto3.client("sns")
sqs_client = boto3.client('sqs')

SINGLES_TABLE = os.environ["SINGLES_TABLE"]
FILTER_ADD_LAMBDA = os.environ["FILTER_ADD_LAMBDA"]
NEW_CONTENT_TOPIC_ARN = os.environ["NEW_CONTENT_TOPIC_ARN"]
queue_url = os.environ["QUEUE_URL"]

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def _head_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except:
        return False

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
        audioKey  = data.get("audioKey")
        imageKey  = data.get("imageKey")
        albumId   = data.get("albumId")
        trackNo   = data.get("trackNo")
        explicit  = bool(data.get("explicit", False))

        if not title:       return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"title required"})}
        if not artistIds:   return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"artistIds required"})} # <--- DODATO: Validacija za artistId listu
        if not audioKey:    return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"audioKey required"})}
        
        pk_artist_id = artistIds[0]
        
        # Validacija da objekat postoji (opciono: izvuci ContentLength/ContentType)
        audio_bucket, audio_key = audioKey.split("/", 1) if audioKey.startswith("s3://") else (os.environ["AUDIO_BUCKET"], audioKey)
        if not _head_exists(audio_bucket, audio_key):
            return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"audio object missing in S3"})}

        now = datetime.datetime.utcnow().isoformat()
        singleId = f"sin-{uuid.uuid4()}"

        item = {
            "artistId":  {"S": pk_artist_id},      # <--- DODATO: Partition Key (PK)
            "singleId":  {"S": singleId},          # <--- Sort Key (SK)
            "title":     {"S": title},
            "artistIds": {"SS": artistIds} if artistIds else {"SS":[]},
            "artistNames": {"SS": artistNames} if artistNames else {"SS":[]}, 
            "genres":    {"SS": genres}    if genres    else {"SS":[]},
            "audioKey":  {"S": f"https://{audio_bucket}.s3.amazonaws.com/{audio_key}"},
            "explicit":  {"BOOL": explicit},
            "createdAt": {"S": now},
        }
        if imageKey:
            # opciono HEAD i ovde
            img_bucket, img_key = imageKey.split("/", 1) if imageKey.startswith("s3://") else (os.environ["IMAGES_BUCKET"], imageKey)
            item["imageKey"] = {"S": f"https://{img_bucket}.s3.amazonaws.com/{img_key}"}
        if albumId: item["albumId"] = {"S": albumId}
        if trackNo is not None: item["trackNo"] = {"N": str(int(trackNo))}

        ddb.put_item(TableName=SINGLES_TABLE, Item=item)

        content = {
            "artistId":  pk_artist_id,      # <--- DODATO: Partition Key (PK)
            "singleId":  singleId,          # <--- Sort Key (SK)
            "title":     title,
            "artistIds": artistIds if artistIds else [],
            "artistNames": artistNames if artistNames else [], 
            "genres":     genres    if genres    else [],
            "audioKey":  f"https://{audio_bucket}.s3.amazonaws.com/{audio_key}",
            "explicit":  explicit,
            "createdAt": now,
        }
        if imageKey:
            # opciono HEAD i ovde
            img_bucket, img_key = imageKey.split("/", 1) if imageKey.startswith("s3://") else (os.environ["IMAGES_BUCKET"], imageKey)
            content["imageKey"] = f"https://{img_bucket}.s3.amazonaws.com/{img_key}"
        if albumId: content["albumId"] = albumId
        if trackNo is not None: content["trackNo"] = str(int(trackNo))

        payload_filter = {
            "contentId": singleId,
            "contentType": "single",
            "content": content,
        }
        lambda_client.invoke(
            FunctionName=FILTER_ADD_LAMBDA,
            InvocationType="Event",
            Payload=json.dumps(payload_filter)
        )

        payload_feed = {
            "content": item,
            "contentId": singleId,
            "contentType": "single",
            "genres": json.dumps(list(genres)),
        }
        print("send message")
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload_feed)
        )

        try:
            sns_message = {
                'contentType': 'single',
                'contentId': singleId,
                'title': title,
                'artistIds': artistIds,
                'artistNames': artistNames,
                'genres': genres,
            }
            sns.publish(
                TopicArn=NEW_CONTENT_TOPIC_ARN,
                Message=json.dumps({'default': json.dumps(sns_message)}),
                MessageStructure='json'
            )
            print(f"Published SNS message for single {singleId}")
        except Exception as sns_error:
            print(f"Error publishing SNS message for single {singleId}: {str(sns_error)}")

        return {"statusCode":201,"headers":cors(),"body":json.dumps({"singleId": singleId})}
    except Exception as e:
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error":str(e)})}
