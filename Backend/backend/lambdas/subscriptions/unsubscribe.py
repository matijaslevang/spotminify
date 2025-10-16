import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username")

        if not username:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        target_id = event.get("pathParameters", {}).get("targetId")

        if not target_id:
            return {"statusCode": 400, "body": json.dumps({"error": "targetId is required in path"})}

        table.delete_item(
            Key={
                'username': username,
                'targetId': target_id
            }
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