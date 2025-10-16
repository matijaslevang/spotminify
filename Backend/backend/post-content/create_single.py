import os, json, uuid, base64, boto3, datetime

s3  = boto3.client("s3")
ddb = boto3.client("dynamodb")

# TABLE_NAME = os.environ["TABLE_NAME"]
# BUCKET     = os.environ["BUCKET_NAME"]
SINGLES_TABLE = os.environ["SINGLES_TABLE"]


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
        genres    = data.get("genres")    or data.get("Genres")  or []
        audioKey  = data.get("audioKey")
        imageKey  = data.get("imageKey")
        albumId   = data.get("albumId")
        trackNo   = data.get("trackNo")
        explicit  = bool(data.get("explicit", False))

        if not title:    return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"title required"})}
        if not audioKey: return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"audioKey required"})}

        # Validacija da objekat postoji (opciono: izvuci ContentLength/ContentType)
        audio_bucket, audio_key = audioKey.split("/", 1) if audioKey.startswith("s3://") else (os.environ["AUDIO_BUCKET"], audioKey)
        if not _head_exists(audio_bucket, audio_key):
            return {"statusCode":400,"headers":cors(),"body":json.dumps({"error":"audio object missing in S3"})}

        now = datetime.datetime.utcnow().isoformat()
        singleId = f"sin-{uuid.uuid4()}"

        item = {
            "singleId":  {"S": singleId},
            "title":     {"S": title},
            "artistIds": {"SS": artistIds} if artistIds else {"SS":[]},
            "genres":    {"SS": genres}    if genres    else {"SS":[]},
            "audioKey":  {"S": audio_key},
            "explicit":  {"BOOL": explicit},
            "createdAt": {"S": now},
        }
        if imageKey:
            # opciono HEAD i ovde
            img_bucket, img_key = imageKey.split("/", 1) if imageKey.startswith("s3://") else (os.environ["IMAGES_BUCKET"], imageKey)
            item["imageKey"] = {"S": img_key}
        if albumId: item["albumId"] = {"S": albumId}
        if trackNo is not None: item["trackNo"] = {"N": str(int(trackNo))}

        ddb.put_item(TableName=SINGLES_TABLE, Item=item)
        return {"statusCode":201,"headers":cors(),"body":json.dumps({"singleId": singleId})}
    except Exception as e:
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error":str(e)})}
