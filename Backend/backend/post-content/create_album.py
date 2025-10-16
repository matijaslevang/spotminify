import os, json, uuid, base64, boto3, datetime

s3  = boto3.client("s3")
ddb = boto3.client("dynamodb")

# BUCKET = os.environ["BUCKET_NAME"]
# TABLE  = os.environ["TABLE_NAME"]
ALBUMS_TABLE  = os.environ["ALBUMS_TABLE"]
SINGLES_TABLE = os.environ["SINGLES_TABLE"]
AUDIO_BUCKET  = os.environ["AUDIO_BUCKET"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]

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
        genres    = data.get("genres")    or data.get("Genres")  or []
        coverKey  = data.get("coverKey")
        tracks    = data.get("tracks") or []

        if not title:  return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"title required"})}
        if not tracks: return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"tracks required"})}

        albumId = f"alb-{uuid.uuid4()}"
        now = datetime.datetime.utcnow().isoformat()

        # album item
        album = {
            "albumId":   {"S": albumId},
            "title":     {"S": title},
            "artistIds": {"SS": artistIds} if artistIds else {"SS":[]},
            "genres":    {"SS": genres}    if genres    else {"SS":[]},
            "createdAt": {"S": now},
        }
        if coverKey:
            # opciono HEAD provera
            album["coverKey"] = {"S": coverKey}
     
        ddb.put_item(TableName=ALBUMS_TABLE, Item=album)

        # kreiraj single stavke
        created = []
        for t in tracks:
            stitle  = (t.get("title") or "").strip() or "Track"
            sgenres = t.get("genres")    or []
            sarts   = t.get("artistIds") or artistIds
            akey    = t.get("audioKey")
            trno    = t.get("trackNo")
            ikey    = t.get("imageKey")

            if not akey:
                continue
            if not _exists(AUDIO_BUCKET, akey):
                continue

            singleId = f"sin-{uuid.uuid4()}"
            item = {
                "singleId":  {"S": singleId},
                "title":     {"S": stitle},
                "artistIds": {"SS": sarts}  if sarts  else {"SS":[]},
                "genres":    {"SS": sgenres}if sgenres else {"SS":[]},
                "audioKey":  {"S": akey},
                "albumId":   {"S": albumId},
                "createdAt": {"S": now},
            }
            if trno is not None: item["trackNo"] = {"N": str(int(trno))}
            if ikey: item["imageKey"] = {"S": ikey}

            ddb.put_item(TableName=SINGLES_TABLE, Item=item)
            created.append({"singleId": singleId, "trackNo": trno})

        return {"statusCode":201,"headers":cors(),"body":json.dumps({"albumId": albumId, "tracks": created})}
    except Exception as e:
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error":str(e)})}
