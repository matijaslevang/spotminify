import os
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:        
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username")

        if not username:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        body = json.loads(event.get("body", "{}"))
        target_id = body.get("targetId")
        target_name = body.get("targetName")
        subscription_type = body.get("subscriptionType")

        if not target_id or not subscription_type:
            return {"statusCode": 400, "body": json.dumps({"error": "targetId and subscriptionType are required"})}

        table.put_item(
            Item={
                'username': username,
                'targetId': target_id,
                'targetName': target_name,
                'subscriptionType': subscription_type,
                'subscribedAt': datetime.utcnow().isoformat()
            }
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