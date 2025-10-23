import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
genre_index_table = dynamodb.Table(os.environ['GENRE_INDEX_TABLE'])
artist_index_table = dynamodb.Table(os.environ['ARTIST_INDEX_TABLE'])

def handler(event, context):
    body = event
    
    content_id = body.get('contentId')
    content_type = body.get('contentType')
    content = body.get('content')
    
    content_key = f"{content_type}-{content_id}"

    item = {
        'contentKey': content_key,
        'contentId': content_id,
        'contentType': content_type,
        'content': content,
    }

    content_genres = content['genres']

    if content_type == 'artist':
        for genre in content_genres:
            genre_item = item.copy()
            genre_item.pop("contentArtists")
            genre_item['genreName'] = genre
            genre_index_table.put_item(Item=genre_item)
    
    elif content_type in ['single', 'album']:
        content_artists = content['artistIds']
        for genre in content_genres:
            genre_item = item.copy()
            genre_item['genreName'] = genre
            genre_index_table.put_item(Item=genre_item)
        
        for artist in content_artists:
            artist_item = item.copy()
            artist_item['artistId'] = artist
            artist_index_table.put_item(Item=artist_item)