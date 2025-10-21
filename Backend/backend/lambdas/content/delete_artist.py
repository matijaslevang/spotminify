import json
import os
import boto3
from boto3.dynamodb.conditions import Key

# Inicijalizacija AWS klijenata
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Dobijanje imena resursa iz environment varijabli
ARTISTS_TABLE_NAME = os.environ['ARTISTS_TABLE']
ALBUMS_TABLE_NAME = os.environ['ALBUMS_TABLE']
SINGLES_TABLE_NAME = os.environ['SINGLES_TABLE']
IMAGES_BUCKET_NAME = os.environ['IMAGES_BUCKET']
AUDIO_BUCKET_NAME = os.environ['AUDIO_BUCKET']
GENRE_INDEX_TABLE_NAME = os.environ['GENRE_INDEX_TABLE']
ARTIST_INDEX_TABLE_NAME = os.environ['ARTIST_INDEX_TABLE']

artists_table = dynamodb.Table(ARTISTS_TABLE_NAME)
albums_table = dynamodb.Table(ALBUMS_TABLE_NAME)
singles_table = dynamodb.Table(SINGLES_TABLE_NAME)
genre_index_table = dynamodb.Table(GENRE_INDEX_TABLE_NAME)
artist_index_table = dynamodb.Table(ARTIST_INDEX_TABLE_NAME)


def cors_headers():
    """Definiše kompletne CORS headere za sve odgovore."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE",
        "Content-Type": "application/json"
    }

def delete_from_index(table, partition_key_value, sort_key_value, partition_key_name, sort_key_name):
    """Generička funkcija za brisanje iz DynamoDB index tabela."""
    try:
        table.delete_item(
            Key={
                partition_key_name: partition_key_value,
                sort_key_name: sort_key_value
            }
        )
    except Exception as e:
        print(f"Error deleting from index {table.name}: {e}")

def handler(event, context):
    artist_id = event.get('pathParameters', {}).get('artistId')

    # 1. Provera Autorizacije
    try:
        user_role = event['requestContext']['authorizer']['claims']['custom:role']
        if user_role != 'Admin':
            return {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'}), 'headers': cors_headers()}
    except KeyError:
        return {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'}), 'headers': cors_headers()}

    if not artist_id:
        return {'statusCode': 400, 'body': json.dumps({'message': 'Missing artistId'}), 'headers': cors_headers()}

    # 2. Dohvatanje Umetnika radi imageKey-a
    try:
        artist_response = artists_table.get_item(Key={'artistId': artist_id})
        artist_item = artist_response.get('Item')
        
        if not artist_item:
            return {'statusCode': 204, 'body': '', 'headers': cors_headers()}

        artist_image_key = artist_item.get('imageKey')

    except Exception as e:
        print(f"Error fetching artist: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error while reading artist data.'}), 'headers': cors_headers()}


    # 3. Dohvatanje SVIH Sadržaja Umetnika
    all_songs = []
    
    try:
        # A. Dohvatanje svih ALBUMA umetnika (Pretpostavka: ArtistId je PK na Albums tabeli)
        # Nije potreban GSI, jer je artistId sada Partition Key primarnog indeksa (PK).
        albums_response = albums_table.query(
        KeyConditionExpression=Key('artistId').eq(artist_id)
        )
        albums_to_delete = albums_response.get('Items', [])
        
        # B. Dohvatanje svih SINGLOVA umetnika (Pretpostavka: ArtistId je PK na Singles tabeli)
        singles_response = singles_table.query(
            KeyConditionExpression=Key('artistId').eq(artist_id)
        )
        all_songs.extend(singles_response.get('Items', []))

    except Exception as e:
        print(f"Error querying albums/singles: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error during content query.'}), 'headers': cors_headers()}
    # 4. Kaskadno brisanje (Singlovi i Albumi)

    # A. Brisanje SVAKOG pronađenog singla i njegovih resursa
    # Oprez: Proverite da li pesma već postoji u listi (da ne bi duplirali brisanje)
    processed_single_ids = set()
    
    for song in all_songs:
        single_id = song.get('singleId')
        if single_id in processed_single_ids:
            continue
        processed_single_ids.add(single_id)

        audio_key = song.get('audioKey')
        image_key = song.get('imageKey')
        genres = song.get('genres', [])
        
        # Brisanje iz Singles tabele
        try:
            singles_table.delete_item(
                Key={
                    'artistId': artist_id, # <--- DODAT PK (Partition Key)
                    'singleId': single_id  # <-- SK (Sort Key)
                 }
            )
        except Exception as e:
            print(f"Error deleting single {single_id}: {e}")

        # Brisanje iz Index tabela (GenreIndex i ArtistIndex)
        content_key = f"single#{single_id}"
        for genre_name in genres:
            delete_from_index(genre_index_table, genre_name, content_key, 'genreName', 'contentKey')
        # Brisanje iz Artist Indexa za tog Umetnika (za sve ostale umetnike ostaje)
        delete_from_index(artist_index_table, artist_id, content_key, 'artistId', 'contentKey')

        # Brisanje S3 fajlova
        if audio_key:
            try: s3.delete_object(Bucket=AUDIO_BUCKET_NAME, Key=audio_key)
            except Exception as e: print(f"Error deleting audio {audio_key}: {e}")
        if image_key:
             try: s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=image_key)
             except Exception as e: print(f"Error deleting image {image_key}: {e}")


    # B. Brisanje SVAKOG pronađenog albuma
    for album in albums_to_delete:
        album_id = album.get('albumId')
        album_image_key = album.get('coverKey')

        try:
            albums_table.delete_item(
            Key={
                'artistId': artist_id, # <--- DODAT PK (Partition Key)
                'albumId': album_id    # <-- SK (Sort Key)
                }
            )
            
            # Brisanje slike albuma
            if album_image_key:
                s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=album_image_key)
                
        except Exception as e:
            print(f"Error deleting album {album_id}: {e}")


    # 5. Konačno Brisanje Umetnika
    try:
        artists_table.delete_item(Key={'artistId': artist_id})
        
        # Brisanje slike umetnika
        if artist_image_key:
            s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=artist_image_key)
            
    except Exception as e:
        print(f"Fatal error deleting artist {artist_id}: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error during final artist deletion.'}), 'headers': cors_headers()}


    # 6. Uspešan odgovor
    return {
        'statusCode': 204,
        'body': '',
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
        }
    }