# import os
# import json
# import boto3
# from boto3.dynamodb.conditions import Key
# from decimal import Decimal 

# dynamodb = boto3.resource("dynamodb")
# # Očekujemo da je naziv tabele singlova u environment varijabli
# # TABLE_NAME = os.environ["SINGLE_TABLE"] 
# # table = dynamodb.Table(TABLE_NAME)

# SINGLE_TABLE_NAME = os.environ['SINGLE_TABLE']
# RATINGS_TABLE_NAME = os.environ['RATINGS_TABLE'] # NOVO

# singles_table = dynamodb.Table(SINGLE_TABLE_NAME)
# ratings_table = dynamodb.Table(RATINGS_TABLE_NAME)

# def cors_headers():
#     return {
#         "Access-Control-Allow-Origin": "*",
#         "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#         "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
#     }

# def custom_json_serializer(obj):
#     if isinstance(obj, Decimal):
#         # Pretvaranje Decimal u int ili float, u zavisnosti od toga da li ima decimalni deo
#         if obj % 1 == 0:
#             return int(obj)
#         else:
#             return float(obj)
#     if isinstance(obj, set):
#         # Pretvaranje DynamoDB Set tipa u Python listu
#         return list(obj)
#     # Ako naiđe na drugi nepoznati tip, baca grešku
#     raise TypeError("Type %s not serializable" % type(obj))

# def calculate_average_rating(content_id):
#     """Izvodi Query na Ratings tabli i izračunava prosečnu ocenu."""
#     try:
#         # Tabela Ratings ima PK: contentId, SK: username
#         response = ratings_table.query(
#             KeyConditionExpression=Key('contentId').eq(content_id)
#         )
        
#         ratings = response.get('Items', [])
        
#         if not ratings:
#             return None, 0 # Nema ocena

#         # DynamoDB vraca brojeve kao Decimal, sumiramo ih
#         total_rating = sum(item['rating'] for item in ratings)
#         count = len(ratings)
#         average = total_rating / count
        
#         # Zaokruživanje na npr. 2 decimale
#         return round(float(average), 2), count
        
#     except Exception as e:
#         print(f"Error calculating average rating for {content_id}: {e}")
#         return None, 0
    
# def handler(event, context):
#     try:
#         # 1. Provera ulaznih parametara
#         # singleId se čita iz query string parametara
#         if 'queryStringParameters' not in event or 'singleId' not in event['queryStringParameters']:
#             return {
#                 "statusCode": 400,
#                 "body": json.dumps({"message": "Missing singleId query parameter"}),
#                 "headers": cors_headers()
#             }
        
#         single_id = event['queryStringParameters']['singleId']
        
#         # 2. QUERY na GSI (SingleIdIndex)
#         # Koristimo GSI jer je primarni ključ kompozitan (artistId, singleId)
#         # a mi imamo samo singleId.
#         response = singles_table.query(
#             IndexName='SingleIdIndexV2', # Ime GSI-ja iz backend_stack.py
#             KeyConditionExpression=Key('singleId').eq(single_id)
#         )
        
#         item = response.get('Items', [None])[0]
        
#         if item:
#             # DynamoDB Set tip (Set(['pop', 'rock'])) mora se konvertovati u Python listu
#             if 'genres' in item:
#                 item['genres'] = list(item['genres'])
            
            
#             return {
#                 "statusCode": 200,
#                 "body": json.dumps(item, default=custom_json_serializer),
#                 "headers": cors_headers()
#             }
#         else:
#             return {
#                 "statusCode": 404,
#                 "body": json.dumps({"message": f"Single with ID {single_id} not found"}),
#                 "headers": cors_headers()
#             }
            
#     except Exception as e:
#         print(f"Error in get_single handler: {e}")
#         # Vraćanje 500 sa CORS headerima
#         return {
#             "statusCode": 500,
#             "body": json.dumps({"message": "Internal Server Error"}),
#             "headers": cors_headers()
#         }

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
        "Access-Control-Allow-Methods": "OPTIONS,GET", # Promenjeno u GET
        "Content-Type": "application/json" # Dodato
    }

def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, set):
        # Pretvaranje DynamoDB Set tipa u Python listu
        return list(obj)
    # Ako naiđe na drugi nepoznati tip, baca grešku
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
            return None, 0 # Nema ocena

        total_rating = sum(item['rating'] for item in ratings)
        count = len(ratings)
        average = total_rating / count
        
        # Zaokruživanje na 2 decimale
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
        
        # 2. QUERY na GSI za dohvatanje pesme
        response = singles_table.query(
            IndexName='SingleIdIndexV2', # Ime GSI-ja iz backend_stack.py
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