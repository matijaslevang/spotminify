import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["SINGLE_TABLE"]
GSI_NAME = os.environ["SINGLES_GSI"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    album_id = event['queryStringParameters']['albumId']
    print(album_id)
    response = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key('albumId').eq(album_id)
    )
    if "Items" in response:
        singles = response['Items']
        print(singles)
        for single in singles:
            single['artistIds'] = list(single['artistIds'])
            single['genres'] = list(single['genres'])
            single['trackNo'] = int(single['trackNo'])
        return {
            "statusCode": 200,
            "body": json.dumps(singles),
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