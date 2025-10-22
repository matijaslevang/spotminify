import json
import os
import boto3
from datetime import datetime

# Inicijalizacija AWS klijenata
dynamodb = boto3.resource('dynamodb')

# Dobijanje imena resursa iz environment varijabli
RATINGS_TABLE_NAME = os.environ['RATINGS_TABLE']
SINGLES_TABLE_NAME = os.environ['SINGLES_TABLE']
ALBUMS_TABLE_NAME = os.environ['ALBUMS_TABLE']

ratings_table = dynamodb.Table(RATINGS_TABLE_NAME)
singles_table = dynamodb.Table(SINGLES_TABLE_NAME)
albums_table = dynamodb.Table(ALBUMS_TABLE_NAME)


def cors_headers():
    """Definiše kompletne CORS headere za sve odgovore."""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
        "Content-Type": "application/json"
    }

def get_content_details(content_id, content_type):
    """Dohvata žanrove na osnovu contentId i targetType."""
    if content_type == 'SONG':
        # Za SINGL nam treba i artistId, ali ako ne znate artistId, 
        # morate uraditi SCAN ili QUERY na GSI 'by-single-id' ako postoji
        # ili se osloniti na SingleID ako je to SK. 
        # Ako je tabela singlova PK: artistId, SK: singleId, NE MOŽETE SAMO SA singleId!
        
        # PRETPOSLOŽENO REŠENJE: Dohvatate iz tabele gde znate PK/SK. 
        # Ako je tabela singlova artistId(PK)/singleId(SK), moraćete da je prilagodite.
        # Za sada, pretpostavimo da imate sve informacije za QUERY/GET, ili radite SCAN.
        # Ako je singleId JEDINSTVEN, možemo koristiti GSI, ali ovde je sigurnije i lakše.
        # Trenutno ne znamo PK/SK singla da bismo koristili GET.
        
        # OVO JE KRITIČNA TAČKA, TREBA NAM GSI ZA singleId
        # Privremeno rešenje, zahteva da u CDK-u dodate GSI na SinglesTable: 
        # IndexName='SingleIdIndex', PK='singleId'
        try:
            # Koristimo SingleIdIndex na SinglesTable
            response = singles_table.query(
                IndexName='SingleIdIndexV2', # MORATE DODATI OVAJ GSI U CDK!
                KeyConditionExpression=boto3.dynamodb.conditions.Key('singleId').eq(content_id)
            )
            item = response.get('Items', [None])[0]
            if item:
                return item.get('genres', [])
        except Exception as e:
            print(f"Error querying singles table: {e}")
            return []
            
    elif content_type == 'ALBUM':
        # Slično, zahteva dobar pristup (PK: artistId, SK: albumId)
        # Ako nemate artistId, opet vam treba GSI na AlbumsTable: 
        # IndexName='AlbumIdIndex', PK='albumId'
        try:
            # Koristimo AlbumIdIndex na AlbumsTable
            response = albums_table.query(
                IndexName='AlbumIdIndexV2', # MORATE DODATI OVAJ GSI U CDK!
                KeyConditionExpression=boto3.dynamodb.conditions.Key('albumId').eq(content_id)
            )
            item = response.get('Items', [None])[0]
            if item:
                return item.get('genres', [])
        except Exception as e:
            print(f"Error querying albums table: {e}")
            return []

    # Za ARTIST se žanrovi obično ne upisuju u ocenu, ali možete ih uzeti sa artist_table
    return []


def handler(event, context):
    try:
        # 1. AUTORIZACIJA: Provera korisnika i uloge (samo redovni korisnik)
        # Dohvatanje username-a iz Cognito Claimsa
        username = event['requestContext']['authorizer']['claims']['cognito:username']
        user_role = event['requestContext']['authorizer']['claims']['custom:role']
        
        #if user_role != 'User': # Proverite tačan naziv uloge
        #     return {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden: Only regular users can rate.'}), 'headers': cors_headers()}

        # 2. PARSIRANJE TELA ZAHTEVA
        body = json.loads(event['body'])
        target_id = body.get('targetId')
        target_type = body.get('targetType') # 'SONG', 'ALBUM', 'ARTIST'
        rating_value = body.get('value')     # 1 do 5

        if not all([target_id, target_type, rating_value]):
            return {'statusCode': 400, 'body': json.dumps({'message': 'Missing targetId, targetType, or value.'}), 'headers': cors_headers()}

        if not (1 <= rating_value <= 5):
            return {'statusCode': 400, 'body': json.dumps({'message': 'Rating value must be between 1 and 5.'}), 'headers': cors_headers()}
        
        # 3. DOHVATANJE DETALJA SADRŽAJA (Genres)
        # **PAŽNJA: Pročitajte komentar iznad funkcije get_content_details**
        genres = get_content_details(target_id, target_type)
        if not genres and (target_type == 'SONG' or target_type == 'ALBUM'):
             print(f"Warning: Could not fetch genres for {target_type} ID: {target_id}. Item might not exist.")

        # 4. KREIRANJE I UPIS STAVKE
        current_time_iso = datetime.utcnow().isoformat() + 'Z' 
        
        item_to_put = {
            'contentId': target_id,
            'username': username,
            'rating': rating_value,
            'targetType': target_type,
            'genres': genres, 
            'timestamp': current_time_iso
        }
        
        # Koristimo put_item za upis/ažuriranje. Ako korisnik ponovo oceni, 
        # ključ (contentId+username) će zameniti staru ocenu (overwrite).
        ratings_table.put_item(Item=item_to_put)
        
        # Opciono: Mogli biste ovde poslati poruku na SQS za asinhrono ažuriranje prosečne ocene

        # 5. USPEŠAN ODGOVOR
        return {
            'statusCode': 200, # Vraćamo 200 OK
            'body': json.dumps({'message': 'Content rated successfully.', 'rating': rating_value}),
            'headers': cors_headers()
        }

    except Exception as e:
        print(f"Fatal error in rate_content handler: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal Server Error.'}), 'headers': cors_headers()}