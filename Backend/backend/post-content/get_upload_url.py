import os, json, uuid, boto3
from botocore.config import Config

s3 = boto3.client("s3", region_name="eu-central-1", 
    config=Config(signature_version='s3v4'))
AUDIO_BUCKET  = os.environ["AUDIO_BUCKET"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]

def _cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def handler(event, _):
    try:
        body = json.loads(event.get("body") or "{}")
        bt   = (body.get("bucketType") or "").lower()    # 'audio' | 'image'
        ctype= body.get("contentType") or "application/octet-stream"
        fname= body.get("fileName") or "file"

        if bt not in ("audio","image"):
            return {"statusCode":400,"headers":_cors(),"body":json.dumps({"error":"bucketType must be 'audio' or 'image'"})}

        bucket = AUDIO_BUCKET if bt=="audio" else IMAGES_BUCKET
        prefix = "audio" if bt=="audio" else "covers"
        key    = f"{prefix}/{uuid.uuid4()}_{fname}"

        url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": ctype},
            ExpiresIn=900
        )

        return {
            "statusCode": 200,
            "headers": _cors(),
            "body": json.dumps({
                "url": url,
                "bucket": bucket,
                "key": key,
                # pomoćno:
                "s3Uri": f"s3://{bucket}/{key}",
                "httpUrl": f"https://{bucket}.s3.amazonaws.com/{key}"
            })
        }
    except Exception as e:
        return {"statusCode":500,"headers":_cors(),"body":json.dumps({"error":str(e)})}
