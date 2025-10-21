import json
import os
import boto3
from decimal import Decimal

# Pomoćna klasa za konverziju Decimal tipova u JSON format (i dalje je dobra praksa)
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

# NOVO: Pomoćna funkcija za rekurzivnu konverziju nestandardnih tipova
def convert_to_serializable(obj):
    if isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    # KRITIČNA KONVERZIJA: set -> list
    if isinstance(obj, set):
        return list(obj) 
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def cors_headers():
    # Vraćanje svih potrebnih zaglavlja za omogućavanje CORS-a
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET" 
    }
    
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """
    Vraća sve stavke (artiste) iz DynamoDB tabele, konvertujući setove u liste.
    """
    
    table_name = os.environ.get("ARTISTS_TABLE_NAME")
    if not table_name:
        return {
            'statusCode': 500,
            'headers': cors_headers(), 
            'body': json.dumps({'message': 'Ime tabele nije definisano.'})
        }

    table = dynamodb.Table(table_name)

    try:
        projection = "artistId, biography, genres, imageUrl, #artistName"
        attribute_names = {"#artistName": "name"}
        
        response = table.scan(
            ProjectionExpression=projection,
            ExpressionAttributeNames=attribute_names
        )
        artists = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                ProjectionExpression=projection, 
                ExpressionAttributeNames=attribute_names
            )
            artists.extend(response['Items'])

        # KRITIČNA IZMENA: Konvertovanje setova (npr. za 'genres') pre slanja
        serializable_artists = [convert_to_serializable(artist) for artist in artists]

        headers = cors_headers()
        headers['Content-Type'] = 'application/json'

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(serializable_artists, cls=JSONEncoder)
        }

    except Exception as e:
        print(f"Greška prilikom čitanja artista: {e}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'message': f'Došlo je do greške: {str(e)}'})
        }