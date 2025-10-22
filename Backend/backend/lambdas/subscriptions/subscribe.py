import os
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client('sqs')
TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
queue_url = os.environ["QUEUE_URL"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:        
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username")

        if not username:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        body = json.loads(event.get("body", "{}"))
        targetId = body.get("targetId")
        subscription_type = body.get("subscriptionType")
        artist_name = body.get("artistName")
        image_url = body.get("imageUrl")
        genres = body.get("genres")
        subType = "artsub" if subscription_type == "ARTIST" else "gensub"

        if not targetId or not subscription_type:
            return {"statusCode": 400, "body": json.dumps({"error": "targetId and subscriptionType are required"})}

        table.put_item(
            Item={
                'username': username,
                'targetId': targetId,
                'artistName': artist_name,
                'imageUrl': image_url,
                'subscriptionType': subscription_type,
                'subscribedAt': datetime.utcnow().isoformat(),
                'genres': genres
            }
        )
        
        print("send message")
        payload = {
            "username": username,
            "type": subType,
            "incomingScore": 1,
            "genres": json.dumps(list(genres))
        }
        print(payload)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload)
        )

        return {
            "statusCode": 201,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Subscribed successfully"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }