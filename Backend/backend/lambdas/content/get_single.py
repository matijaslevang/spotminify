import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SINGLE_TABLE"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    single_id = event['queryStringParameters']['singleId']
    print(single_id)
    response = table.get_item(Key={"singleId": single_id})
    if "Item" in response:
        single = response['Item']
        print(single)
        single['artistIds'] = list(single['artistIds'])
        single['genres'] = list(single['genres'])
        return {
            "statusCode": 200,
            "body": json.dumps(single),
            "headers": cors_headers()
        }
    else:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Artist not found"}),
            "headers": cors_headers()
        }
    
def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }