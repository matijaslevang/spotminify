import os
import json
import boto3
from decimal import Decimal 

dynamodb = boto3.resource('dynamodb')
table_feed_cache = dynamodb.Table(os.environ["FEED_TABLE_NAME"])

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError("Type %s not serializable" % type(obj))

def handler(event, context):
    try:
        # get username of currently logged in user
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username", "")
        print(username)
        if username == "":
            return {
                "statusCode": 401,
                "headers": cors_headers(),
                "body": json.dumps({"User authentication failed, couldn't get feed"})
            }
        
        # get their feed
        response = table_feed_cache.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('username').eq(username)
        )
        print(response)
        user_feed = response.get("Items", [])
        print(user_feed)
        # neatly organize it
        rec_artists = [item for item in user_feed if item["contentType"] == "artist"]
        rec_songs = [item for item in user_feed if item["contentType"] == "single"]
        rec_albums = [item for item in user_feed if item["contentType"] == "album"]

        print(rec_artists)
        print(rec_songs)
        print(rec_albums)
        # return it
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({"recommendedArtists": rec_artists, "recommendedAlbums": rec_albums, "recommendedSongs": rec_songs}, default=custom_json_serializer)
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