import os
import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username")

        if not username:
            return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

        response = table.query(
            KeyConditionExpression=Key('username').eq(username)
        )
        
        subscriptions = response.get('Items', [])
        
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps(subscriptions)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }