# import os
# import json
# import boto3

# dynamodb = boto3.resource("dynamodb")
# TABLE_NAME = os.environ["ALBUM_TABLE"]
# table = dynamodb.Table(TABLE_NAME)

# def handler(event, context):
#     album_id = event['queryStringParameters']['albumId']
#     print(album_id)
#     response = table.get_item(Key={"albumId": album_id})
#     if "Item" in response:
#         album = response['Item']
#         print(album)
#         album['artistIds'] = list(album['artistIds'])
#         album['genres'] = list(album['genres'])
#         return {
#             "statusCode": 200,
#             "body": json.dumps(album),
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
# Uvozimo Decimal za serijalizaciju
from decimal import Decimal 

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ALBUM_TABLE"] 
table = dynamodb.Table(TABLE_NAME)

# NOVO: Funkcija za rešavanje problema sa serijalizacijom Decimal i Set tipova
def custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        # Pretvaranje Decimal u int ili float, u zavisnosti od toga da li ima decimalni deo
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, set):
        # Pretvaranje DynamoDB Set tipa u Python listu
        return list(obj)
    # Ako naiđe na drugi nepoznati tip, baca grešku
    raise TypeError("Type %s not serializable" % type(obj))

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def handler(event, context):
    try:
        if 'queryStringParameters' not in event or 'albumId' not in event['queryStringParameters']:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": "Missing albumId query parameter"}),
                "headers": cors_headers()
            }
        
        album_id = event['queryStringParameters']['albumId']
        
        response = table.query(
            IndexName='AlbumIdIndex', 
            KeyConditionExpression=Key('albumId').eq(album_id)
        )
        print(response)
        item = response.get('Items', [None])[0]
        
        if item:
            # Uklonili smo ručnu konverziju žanrova jer je sada u custom_json_serializer-u.
            # Važno: Ako je album_id upisan kao Decimal (broj), ova konverzija ga rešava.
            return {
                "statusCode": 200,
                # KORISTIMO NOVI SERIJALIZATOR!
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
        # Vraćanje 500 sa CORS headerima. Ova greška bi sada trebalo da se prikaže umesto 502
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"}),
            "headers": cors_headers()
        }