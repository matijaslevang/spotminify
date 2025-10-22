import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal 

dynamodb = boto3.resource("dynamodb")

ALBUM_TABLE_NAME = os.environ['ALBUM_TABLE']
RATINGS_TABLE_NAME = os.environ['RATINGS_TABLE']  

albums_table = dynamodb.Table(ALBUM_TABLE_NAME)
ratings_table = dynamodb.Table(RATINGS_TABLE_NAME)  


def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError("Type %s not serializable" % type(obj))

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def calculate_average_rating(content_id):
    """Izvodi Query na Ratings tabli i izračunava prosečnu ocenu."""
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

def handler(event, context):
    try:
        if 'queryStringParameters' not in event or 'albumId' not in event['queryStringParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing albumId query parameter"}),
                "headers": cors_headers()
            }
        
        album_id = event['queryStringParameters']['albumId']
        
        response = albums_table.query(
            IndexName='AlbumIdIndexV2', 
            KeyConditionExpression=Key('albumId').eq(album_id)
        )
        
        item = response.get('Items', [None])[0]
        
        if item:

            average_rating, rating_count = calculate_average_rating(album_id)
            
            item['averageRating'] = average_rating 
            item['ratingCount'] = rating_count
            
            return {
                "statusCode": 200,
                "body": json.dumps(item, default=custom_json_serializer),
                "headers": cors_headers()
            }
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": f"Album with ID {album_id} not found"}),
                "headers": cors_headers()
            }
            
    except Exception as e:
        print(f"Error in get_album handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "headers": cors_headers()
        }