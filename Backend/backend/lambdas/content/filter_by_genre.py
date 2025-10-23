import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['GENRE_INDEX_TABLE']
table = dynamodb.Table(table_name)

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
    genre_name = event['queryStringParameters']['genreName']
    
    response = table.query(
        KeyConditionExpression='genreName = :genreName',
        ExpressionAttributeValues={
            ':genreName': genre_name
        }
    )

    result_albums = []
    result_artists = []
    result_songs = []

    for item in response['Items']:
        content_type = item.get('contentType')
        
        if content_type == 'album':
            result_albums.append(item)
        elif content_type == 'artist':
            result_artists.append(item)
        elif content_type == 'single':
            result_songs.append(item)
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'resultAlbums': result_albums,
            'resultArtists': result_artists,
            'resultSongs': result_songs
        }, default=custom_json_serializer)
    }

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }