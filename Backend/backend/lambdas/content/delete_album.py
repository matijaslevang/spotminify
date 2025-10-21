import json
import os
import boto3
from boto3.dynamodb.conditions import Attr, Key

# Inicijalizacija AWS klijenata
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Dobijanje imena resursa iz environment varijabli (postavljenih u CDK-u)
ALBUMS_TABLE_NAME = os.environ['ALBUMS_TABLE']
SINGLES_TABLE_NAME = os.environ['SINGLES_TABLE']
IMAGES_BUCKET_NAME = os.environ['IMAGES_BUCKET']
AUDIO_BUCKET_NAME = os.environ['AUDIO_BUCKET']
GENRE_INDEX_TABLE_NAME = os.environ['GENRE_INDEX_TABLE']
ARTIST_INDEX_TABLE_NAME = os.environ['ARTIST_INDEX_TABLE']

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
        # Ne zaustavljamo se zbog greške u indeksu

def handler(event, context):
    album_id = event.get('pathParameters', {}).get('albumId')

    # Provera Admin uloge (kao i ranije)
    try:
        user_role = event['requestContext']['authorizer']['claims']['custom:role']
        if user_role != 'Admin':
            return {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'}), 'headers': cors_headers()}
    except KeyError:
        return {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'}), 'headers': cors_headers()}

    if not album_id:
        return {'statusCode': 400, 'body': json.dumps({'message': 'Missing albumId'}), 'headers': cors_headers()}

    # KORAK 1: Dohvatanje albuma i svih singlova vezanih za album
    try:
        album_scan_response = albums_table.scan(
            FilterExpression=Attr('albumId').eq(album_id),
            Limit=1
        )
        album_item = album_scan_response.get('Items', [])
        
        if not album_item:
            # Vraćamo 204 ako album ne postoji (idiempotentnost)
            return {'statusCode': 204, 'body': '', 'headers': cors_headers()}

        # Album je pronađen. Izvuci ključeve i podatke.
        album_data = album_item[0]
        artist_id = album_data.get('artistId') # <--- NOVI PK ZA ALBUM
        album_image_key = album_data.get('coverKey') # Ime atributa je 'coverKey', a ne 'imageKey' (provereno iz create_album.py)
        
        if not artist_id:
             raise Exception("Album found but missing required artistId (Partition Key).")

        # B. Dohvatanje SVIH singlova koji pripadaju albumu (pretpostavka: AlbumIndex postoji)
        # OVO OSTAVLJAMO JER KOD VEĆ KORISTI GSI, ŠTO JE EFIKASNO
        singles_response = singles_table.query(
            IndexName='by-album-id', # <-- ISPRAVKA
            KeyConditionExpression=Key('albumId').eq(album_id)
        )
        songs_to_delete = singles_response.get('Items', [])
        
    except Exception as e:
        print(f"Error fetching album or singles: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error while reading data.'}), 'headers': cors_headers()}


    # KORAK 2: Kaskadno brisanje Singlova (i njihovih resursa)
    for song in songs_to_delete:
        single_id = song.get('singleId')
        audio_key = song.get('audioKey')
        single_artist_id = song.get('artistId')
        genres = song.get('genres', [])
        artist_ids = song.get('artistIds', [])
        content_key = f"single#{single_id}"

        # 2a. Brisanje iz Singles tabele
        try:
            singles_table.delete_item(
                Key={
                    'artistId': single_artist_id, # <--- PK singla
                    'singleId': single_id         # <--- SK singla
                }
            )
        except Exception as e:
            print(f"Error deleting single {single_id}: {e}")

        # 2b. Brisanje iz Index tabela (GenreIndex, ArtistIndex)
        for genre_name in genres:
            delete_from_index(genre_index_table, genre_name, content_key, 'genreName', 'contentKey')
        for artist_id in artist_ids:
            delete_from_index(artist_index_table, artist_id, content_key, 'artistId', 'contentKey')

        # 2c. Brisanje audio fajla iz S3
        if audio_key:
            try:
                s3.delete_object(Bucket=AUDIO_BUCKET_NAME, Key=audio_key)
            except Exception as e:
                print(f"Error deleting audio file {audio_key}: {e}")

        # NAPOMENA: Preskačemo brisanje imageKey singlova jer su verovatno svi isti kao album imageKey.
        # Ako svaki singl ima svoju sliku, ovde treba dodati brisanje song.get('imageKey').
        # U ovom rešenju pretpostavljamo da je imageKey singla isti kao imageKey albuma.

    
    # KORAK 3: Brisanje Albuma
    try:
        # 3a. Brisanje iz Albums tabele
        albums_table.delete_item(
            Key={
                'artistId': artist_id, # <--- PK albuma
                'albumId': album_id    # <--- SK albuma
            }
        )
        
        # 3b. Brisanje slike albuma iz S3
        if album_image_key:
            s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=album_image_key)
        
    except Exception as e:
        print(f"Fatal error deleting album {album_id}: {e}")
        # Vraćamo 500 ako glavno brisanje albuma ne uspe
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error during final album deletion.'}), 'headers': cors_headers()}


    # KORAK 4: Uspešan odgovor
    return {
        'statusCode': 204,
        'body': '',
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
        }
    }