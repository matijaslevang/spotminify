import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ALBUM_TABLE"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    album_id = event['queryStringParameters']['albumId']
    print(album_id)
    response = table.get_item(Key={"albumId": album_id})
    if "Item" in response:
        album = response['Item']
        print(album)
        album['artistIds'] = list(album['artistIds'])
        album['genres'] = list(album['genres'])
        return {
            "statusCode": 200,
            "body": json.dumps(album),
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