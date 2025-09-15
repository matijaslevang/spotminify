import os, json, uuid, boto3
s3 = boto3.client("s3")
def handler(event, _):
    b = json.loads(event.get("body") or "{}")
    bt = b.get("bucketType")
    bucket = os.environ["AUDIO_BUCKET"] if bt=="audio" else os.environ["IMAGES_BUCKET"]
    key = ("audio" if bt=="audio" else "covers") + f"/{uuid.uuid4()}_{b.get('fileName','file')}"
    url = s3.generate_presigned_url("put_object",
            Params={"Bucket":bucket,"Key":key,"ContentType":b.get("contentType","application/octet-stream")},
            ExpiresIn=900)
    return {"statusCode":200,"headers":{"Access-Control-Allow-Origin":"*"},
            "body":json.dumps({"url":url,"key":key,"bucket":bucket})}
