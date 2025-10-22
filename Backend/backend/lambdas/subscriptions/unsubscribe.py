import os
import json
import boto3

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

        targetId = event.get("pathParameters", {}).get("targetId")
        body = json.loads(event.get("body", "{}"))
        genres = body.get("genres")
        subType = "artsub" if body.get("subType") == "ARTIST" else "gensub"

        if not targetId:
            return {"statusCode": 400, "body": json.dumps({"error": "targetId is required in path"})}

        table.delete_item(
            Key={
                'username': username,
                'targetId': targetId
            }
        )

        print("send message")
        payload = {
            "username": username,
            "type": subType,
            "incomingScore": -1,
            "genres": json.dumps(list(genres))
        }
        print(payload)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload)
        )
        
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Unsubscribed successfully"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }