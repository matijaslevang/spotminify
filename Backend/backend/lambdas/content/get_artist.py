import os
import json
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ARTIST_TABLE"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    artist_id = event['queryStringParameters']['artistId']
    response = table.get_item(Key={"artistId": artist_id})
    if "Item" in response:
        artist = response['Item']
        print(artist)
        artist['genres'] = list(artist['genres'])
        return {
            "statusCode": 200,
            "body": json.dumps(artist),
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