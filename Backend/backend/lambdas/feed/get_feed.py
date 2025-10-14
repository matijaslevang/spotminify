import os
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table_feed_cache = dynamodb.Table(os.environ["FEED_TABLE_NAME"])

def handler(event, context):
    try:
        # get username of currently logged in user
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
        username = claims.get("cognito:username", "")
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
        user_feed = response.get("Items", [])

        # neatly organize it
        rec_artists = [item for item in user_feed if item["contentType"] == "artist"]
        rec_songs = [item for item in user_feed if item["contentType"] == "song"]
        rec_albums = [item for item in user_feed if item["contentType"] == "album"]

        # return it
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": json.dumps({"recommendedArtists": rec_artists, "recommendedAlbums": rec_albums, "recommendedSongs": rec_songs})
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