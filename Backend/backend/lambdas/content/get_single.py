import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal 

dynamodb = boto3.resource("dynamodb")

SINGLE_TABLE_NAME = os.environ['SINGLE_TABLE']
RATINGS_TABLE_NAME = os.environ['RATINGS_TABLE'] 

singles_table = dynamodb.Table(SINGLE_TABLE_NAME)
ratings_table = dynamodb.Table(RATINGS_TABLE_NAME)

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET", 
        "Content-Type": "application/json" 
    }

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError("Type %s not serializable" % type(obj))

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

        total_rating = sum(item['rating'] for item in ratings)
        count = len(ratings)
        average = total_rating / count
       
        return round(float(average), 2), count
        
    except Exception as e:
        print(f"Error calculating average rating for {content_id}: {e}")
        return None, 0
    
def handler(event, context):
    try:
        if 'queryStringParameters' not in event or 'singleId' not in event['queryStringParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing singleId query parameter"}),
                "headers": cors_headers()
            }
        
        single_id = event['queryStringParameters']['singleId']
        
        response = singles_table.query(
            IndexName='SingleIdIndexV2',
            KeyConditionExpression=Key('singleId').eq(single_id)
        )
        
        item = response.get('Items', [None])[0]
        
        if item:
            average_rating, rating_count = calculate_average_rating(single_id)
            
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
                "body": json.dumps({"message": f"Single with ID {single_id} not found"}),
                "headers": cors_headers()
            }
            
    except Exception as e:
        print(f"Error in get_single handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "headers": cors_headers()
        }