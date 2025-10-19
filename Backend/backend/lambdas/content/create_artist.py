import os
import boto3
import json
import uuid
import base64

s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

BUCKET = os.environ["BUCKET_NAME"]
TABLE = os.environ["TABLE_NAME"]
FILTER_ADD_LAMBDA = os.environ["FILTER_ADD_LAMBDA"]

artist_id = str(uuid.uuid4())

def handler(event, context):
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        role = claims.get("custom:role", "")
        if role != "Admin":
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "User does not have permission"})
            }

        body = event.get("body")

        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")

        data = json.loads(body)

        name = data["name"]
        biography = data.get("biography", "")
        genres = data.get("genres", [])
        image_base64 = data["image"]
        image_type = data.get("imageType", "jpg")

        image_bytes = base64.b64decode(image_base64)

        file_name = f"{name}-{uuid.uuid4()}.{image_type}"
        key = f"artists/{file_name}"

        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType=f"image/{image_type}"
        )
        image_url = f"https://{BUCKET}.s3.amazonaws.com/{key}"

        dynamodb.put_item(
            TableName=TABLE,
            Item={
                "artistId": {"S": artist_id},
                "name": {"S": name},
                "biography": {"S": biography},
                "genres": {"SS": genres},
                "imageUrl": {"S": image_url}
            }
        )

        payload = {
            "contentId": artist_id,
            "contentType": "artist",
            "contentName": name,
            "imageUrl": image_url,
            "contentGenres": genres,
        }
        lambda_client.invoke(
            FunctionName=FILTER_ADD_LAMBDA,
            InvocationType="Event",
            Payload=json.dumps(payload)
        )

        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({"message": "Artist created", "imageUrl": image_url})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers(),
            "body": json.dumps({"error": str(e)})
        }


def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }
