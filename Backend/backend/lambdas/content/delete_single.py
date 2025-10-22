import json
import os
import boto3
# Uvozimo Key za Query na GSI, Attr više nije potreban
from boto3.dynamodb.conditions import Key 

# Inicijalizacija AWS klijenata
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Dobijanje imena resursa iz environment varijabli (postavljenih u CDK-u)
SINGLES_TABLE_NAME = os.environ['SINGLES_TABLE']
AUDIO_BUCKET_NAME = os.environ['AUDIO_BUCKET']
IMAGES_BUCKET_NAME = os.environ['IMAGES_BUCKET']
GENRE_INDEX_TABLE_NAME = os.environ['GENRE_INDEX_TABLE']
ARTIST_INDEX_TABLE_NAME = os.environ['ARTIST_INDEX_TABLE']

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
        print(f"Successfully deleted item from {table.name} with {partition_key_name}={partition_key_value} and {sort_key_name}={sort_key_value}")
    except Exception as e:
        print(f"Error deleting from index {table.name}: {e}")

def handler(event, context):
    print("Received event:", json.dumps(event))
    
    # 1. Provera Admin Uloge (Ostaje nepromenjeno)
    try:
        user_role = event['requestContext']['authorizer']['claims']['custom:role']
        if user_role != 'Admin':
            return {
                'statusCode': 403,
                'body': json.dumps({'message': 'Forbidden: Only administrators can delete content.'}),
                'headers': cors_headers()
            }
    except KeyError:
        return {
            'statusCode': 403,
            'body': json.dumps({'message': 'Forbidden: User role not found.'}),
            'headers': cors_headers()
        }

    # 2. Dobijanje singleId iz putanje
    single_id = event.get('pathParameters', {}).get('singleId')

    if not single_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing singleId in path.'}),
            'headers': cors_headers()
        }

    # KORAK 3: PRONALAŽENJE Partition Key-a (artistId) pomoću GSI Query-ja
    # 💥 OVO JE IZMENJENI DEO 💥
    try:
        # Koristimo QUERY na GSI (SingleIdIndexV2) za brzo pronalaženje itema
        # GSI koristi singleId kao Partition Key
        response = singles_table.query(
            IndexName='SingleIdIndexV2', 
            KeyConditionExpression=Key('singleId').eq(single_id)
        )
        
        song_item = response.get('Items', [])
        print("Found item:", song_item)
        
        if not song_item:
            return {
                'statusCode': 404, 
                'body': json.dumps({'message': 'Song not found, potentially already deleted.'}),
                'headers': cors_headers()
            }
        
        # Ekstrakcija oba ključa i podataka
        song_data = song_item[0]
        artist_id = song_data.get('artistId') # <--- OBAVEZNI artistId (PK)
        audio_key = song_data.get('audioKey')
        image_key = song_data.get('imageKey')
        # Zbog GSI ProjectionType.ALL, ovi atributi su dostupni
        genres = song_data.get('genres', [])
        artist_ids = song_data.get('artistIds', []) 

        if not artist_id:
             raise Exception("Item found but missing required artistId (Partition Key).")
             
    except Exception as e:
        print(f"Error finding item's artistId via GSI query: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal Server Error while finding content keys.'}),
            'headers': cors_headers()
        }

    # KORAK 4: Brisanje (Ostaje nepromenjeno - koristi artistId i singleId)
    try:
        # Brisanje iz DynamoDB Singles tabele - MORA da uključi oba ključa!
        singles_table.delete_item(
            Key={
                'artistId': artist_id, # <--- Partition Key (PK)
                'singleId': single_id # <--- Sort Key (SK)
            }
        )
        # Brisanje iz Index tabela
        content_key = f"single#{single_id}"
        # ... (ostala logika brisanja indexa i S3 fajlova) ...
        for genre_name in genres:
            delete_from_index(genre_index_table, genre_name, content_key, 'genreName', 'contentKey')
        for current_artist_id in artist_ids: # Promenjeno ime varijable zbog opsega
            delete_from_index(artist_index_table, current_artist_id, content_key, 'artistId', 'contentKey')

        # Brisanje fajlova iz S3 Bucketa
        if audio_key:
            s3.delete_object(Bucket=AUDIO_BUCKET_NAME, Key=audio_key)
        if image_key:
            s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=image_key)
            
    except Exception as e:
        print(f"Error during deletion process: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal Server Error during deletion process.'}),
            'headers': cors_headers()
        }
            
    # 7. Uspešan odgovor
    return {
        'statusCode': 204,
        'body': '',
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
        }
    }
# import json
# import os
# import boto3
# from boto3.dynamodb.conditions import Attr

# # Inicijalizacija AWS klijenata
# dynamodb = boto3.resource('dynamodb')
# s3 = boto3.client('s3')

# # Dobijanje imena resursa iz environment varijabli (postavljenih u CDK-u)
# SINGLES_TABLE_NAME = os.environ['SINGLES_TABLE']
# AUDIO_BUCKET_NAME = os.environ['AUDIO_BUCKET']
# IMAGES_BUCKET_NAME = os.environ['IMAGES_BUCKET']
# GENRE_INDEX_TABLE_NAME = os.environ['GENRE_INDEX_TABLE']
# ARTIST_INDEX_TABLE_NAME = os.environ['ARTIST_INDEX_TABLE']

# singles_table = dynamodb.Table(SINGLES_TABLE_NAME)
# genre_index_table = dynamodb.Table(GENRE_INDEX_TABLE_NAME)
# artist_index_table = dynamodb.Table(ARTIST_INDEX_TABLE_NAME)


# def cors_headers():
#     """Definiše kompletne CORS headere za sve odgovore."""
#     return {
#         "Access-Control-Allow-Origin": "*",
#         "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#         "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE", # Dodali smo DELETE ovde
#         # Neki brauzeri zahtevaju i Content-Type
#         "Content-Type": "application/json"
#     }
    
# def delete_from_index(table, partition_key_value, sort_key_value, partition_key_name, sort_key_name):
#     """Generička funkcija za brisanje iz DynamoDB index tabela."""
#     try:
#         table.delete_item(
#             Key={
#                 partition_key_name: partition_key_value,
#                 sort_key_name: sort_key_value
#             }
#         )
#         print(f"Successfully deleted item from {table.name} with {partition_key_name}={partition_key_value} and {sort_key_name}={sort_key_value}")
#     except Exception as e:
#         print(f"Error deleting from index {table.name}: {e}")
#         # Nastaviti izvršavanje čak i ako brisanje indexa ne uspe

# def handler(event, context):
#     print("Received event:", json.dumps(event))
    
#     # 1. Provera Admin Uloge (Najbolja praksa!)
#     try:
#         user_role = event['requestContext']['authorizer']['claims']['custom:role']
#         if user_role != 'Admin':
#             return {
#                 'statusCode': 403,
#                 'body': json.dumps({'message': 'Forbidden: Only administrators can delete content.'}),
#                 'headers': cors_headers() # Koristimo funkciju ovde
#             }
#     except KeyError:
#         return {
#             'statusCode': 403,
#             'body': json.dumps({'message': 'Forbidden: User role not found.'}),
#             'headers': cors_headers() # Koristimo funkciju ovde
#         }

#     # 2. Dobijanje singleId iz putanje
#     single_id = event.get('pathParameters', {}).get('singleId')

#     if not single_id:
#         return {
#             'statusCode': 400,
#             'body': json.dumps({'message': 'Missing singleId in path.'}),
#             'headers': cors_headers() # Koristimo funkciju ovde
#         }

#     # KORAK 3: PRONALAŽENJE Partition Key-a (artistId) pomoću Scan-a
#     # NAPOMENA: Scan je neefikasan! Preporučuje se GSI, ali ovo rešava problem odmah.
#     try:
#         # Koristimo Scan za pretragu cele tabele po SingleId (Sort Key-u)
#         response = singles_table.scan(
#             FilterExpression=Attr('singleId').eq(single_id),
#             Limit=1 # Očekujemo samo jedan rezultat
#         )
#         song_item = response.get('Items', [])
#         print(song_item)
#         if not song_item:
#             # Pesma nije pronađena
#             return {
#                 'statusCode': 404, 
#                 'body': json.dumps({'message': 'Song not found, potentially already deleted.'}),
#                 'headers': cors_headers()
#             }
        
#         # Ekstrakcija oba ključa i podataka
#         song_data = song_item[0]
#         artist_id = song_data.get('artistId') # <--- OBAVEZNI artistId (PK)
#         audio_key = song_data.get('audioKey')
#         image_key = song_data.get('imageKey')
#         genres = song_data.get('genres', [])
#         artist_ids = song_data.get('artistIds', []) # Ovo je lista svih artista

#         if not artist_id:
#              # Ako je pronađen zapis, ali mu fali artistId, to je greška u podacima
#              raise Exception("Item found but missing required artistId (Partition Key).")
             
#     except Exception as e:
#         print(f"Error finding item's artistId via scan: {e}")
#         return {
#             'statusCode': 500,
#             'body': json.dumps({'message': 'Internal Server Error while finding content keys.'}),
#             'headers': cors_headers()
#         }

#     # KORAK 4: Brisanje (Sada moramo da obezbedimo oba ključa)
#     try:
#         # Brisanje iz DynamoDB Singles tabele - MORA da uključi oba ključa!
#         singles_table.delete_item(
#             Key={
#                 'artistId': artist_id, # <--- Partition Key (PK)
#                 'singleId': single_id  # <--- Sort Key (SK)
#             }
#         )
#         # Brisanje iz Index tabela
#         content_key = f"single#{single_id}"
#         for genre_name in genres:
#             delete_from_index(genre_index_table, genre_name, content_key, 'genreName', 'contentKey')
#         for artist_id in artist_ids:
#             delete_from_index(artist_index_table, artist_id, content_key, 'artistId', 'contentKey')

#         # Brisanje fajlova iz S3 Bucketa
#         if audio_key:
#             s3.delete_object(Bucket=AUDIO_BUCKET_NAME, Key=audio_key)
#         if image_key:
#             s3.delete_object(Bucket=IMAGES_BUCKET_NAME, Key=image_key)
            
#     except Exception as e:
#         print(f"Error during deletion process: {e}")
#         return {
#             'statusCode': 500,
#             'body': json.dumps({'message': 'Internal Server Error during deletion process.'}),
#             'headers': cors_headers() # Koristimo funkciju ovde
#         }
            
#     # 7. Uspešan odgovor (204 No Content je standard za uspešan DELETE bez povratnog tela)
#     return {
#         'statusCode': 204,
#         'body': '',
#         'headers': {
#             "Access-Control-Allow-Origin": "*",
#             "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
#             "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE" # Samo ovi su potrebni za 204
#         }
#     }