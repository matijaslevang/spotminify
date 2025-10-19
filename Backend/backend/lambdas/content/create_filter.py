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
    content_name = body.get('contentName')
    image_url = body.get('imageUrl')
    content_genres = body.get('contentGenres', [])
    content_artists = body.get('contentArtists', [])
    
    content_key = f"{content_type}-{content_id}"

    item = {
        'contentKey': content_key,
        'contentId': content_id,
        'contentType': content_type,
        'contentName': content_name,
        'imageUrl': image_url,
        'contentGenres': content_genres,
        'contentArtists': content_artists
    }

    if content_type == 'artist':
        for genre in content_genres:
            genre_item = item.copy()
            genre_item.pop("contentArtists")
            genre_item['genreName'] = genre
            genre_index_table.put_item(Item=genre_item)
    
    elif content_type in ['single', 'album']:
        for genre in content_genres:
            genre_item = item.copy()
            genre_item['genreName'] = genre
            genre_index_table.put_item(Item=genre_item)
        
        for artist in content_artists:
            artist_item = item.copy()
            artist_item['artistId'] = artist
            artist_index_table.put_item(Item=artist_item)