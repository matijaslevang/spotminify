# import os
# import json
# import boto3

# dynamodb = boto3.resource("dynamodb")
# TABLE_NAME = os.environ["SINGLE_TABLE"]
# table = dynamodb.Table(TABLE_NAME)

# def handler(event, context):
#     single_id = event['queryStringParameters']['singleId']
#     print(single_id)
#     response = table.get_item(Key={"singleId": single_id})
#     if "Item" in response:
#         single = response['Item']
#         print(single)
#         single['artistIds'] = list(single['artistIds'])
#         single['genres'] = list(single['genres'])
#         return {
#             "statusCode": 200,
#             "body": json.dumps(single),
#             "headers": cors_headers()
#         }
#     else:
#         return {
#             "statusCode": 404,
#             "body": json.dumps({"message": "Artist not found"}),
#             "headers": cors_headers()
#         }
    
# def cors_headers():
#     return {
#         "Access-Control-Allow-Origin": "*",
#         "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#         "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
#     }
import os
import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
# Očekujemo da je naziv tabele singlova u environment varijabli
TABLE_NAME = os.environ["SINGLE_TABLE"] 
table = dynamodb.Table(TABLE_NAME)

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def handler(event, context):
    try:
        # 1. Provera ulaznih parametara
        # singleId se čita iz query string parametara
        if 'queryStringParameters' not in event or 'singleId' not in event['queryStringParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing singleId query parameter"}),
                "headers": cors_headers()
            }
        
        single_id = event['queryStringParameters']['singleId']
        
        # 2. QUERY na GSI (SingleIdIndex)
        # Koristimo GSI jer je primarni ključ kompozitan (artistId, singleId)
        # a mi imamo samo singleId.
        response = table.query(
            IndexName='SingleIdIndex', # Ime GSI-ja iz backend_stack.py
            KeyConditionExpression=Key('singleId').eq(single_id)
        )
        
        item = response.get('Items', [None])[0]
        
        if item:
            # DynamoDB Set tip (Set(['pop', 'rock'])) mora se konvertovati u Python listu
            if 'genres' in item:
                item['genres'] = list(item['genres'])
                
            return {
                "statusCode": 200,
                "body": json.dumps(item),
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
        # Vraćanje 500 sa CORS headerima
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "headers": cors_headers()
        }