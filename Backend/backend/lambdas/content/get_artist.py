import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")

ARTIST_TABLE_NAME = os.environ["ARTIST_TABLE"]
RATINGS_TABLE_NAME = os.environ.get("RATINGS_TABLE") 

artists_table = dynamodb.Table(ARTIST_TABLE_NAME)
ratings_table = dynamodb.Table(RATINGS_TABLE_NAME) if RATINGS_TABLE_NAME else None

def calculate_average_rating(content_id):
    """Izvodi Query na Ratings tabli i izračunava prosečnu ocenu."""
    if not ratings_table:
        print("ERROR: Ratings table is not configured.")
        return None, 0

    try:
        print(f"DEBUG: Querying ratings for contentId: '{content_id}'")
        
        response = ratings_table.query(
            KeyConditionExpression=Key('contentId').eq(content_id)
        )
    
        ratings = response.get('Items', [])
        
        print(f"DEBUG: DynamoDB Response Count: {response.get('Count', 0)}")
        
        if not ratings:
            return None, 0 

        total_rating = sum(float(item['rating']) for item in ratings)
        count = len(ratings)
        average = total_rating / count
        
        return round(average, 2), count
        
    except Exception as e:
        print(f"Error calculating average rating for {content_id}: {e}")
        return None, 0

def custom_json_serializer(obj):
    """Rešava problem serijalizacije DynamoDB Decimal i Set tipova."""
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
        if 'queryStringParameters' not in event or 'artistId' not in event['queryStringParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing artistId query parameter"}),
                "headers": cors_headers()
            }

        artist_id = event['queryStringParameters']['artistId']
    
        response = artists_table.get_item(Key={"artistId": artist_id})
        
        if "Item" in response:
            artist = response['Item']
            
            if 'genres' in artist and isinstance(artist['genres'], set):
                artist['genres'] = list(artist['genres'])
            
            average_rating, rating_count = calculate_average_rating(artist_id)
            
            artist['averageRating'] = average_rating 
            artist['ratingCount'] = rating_count
            
            return {
                "statusCode": 200,
                "body": json.dumps(artist, default=custom_json_serializer),
                "headers": cors_headers()
            }
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Artist not found"}),
                "headers": cors_headers()
            }
            
    except Exception as e:
        print(f"Error in get_artist handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "headers": cors_headers()
        }

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }