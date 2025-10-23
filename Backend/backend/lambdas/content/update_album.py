import os, json, uuid, boto3, datetime
from botocore.exceptions import ClientError
from decimal import Decimal

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
ddb_client = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
sns = boto3.client("sns")
sqs_client = boto3.client('sqs')

IMAGE_BUCKET = os.environ["IMAGE_BUCKET"]
ALBUMS_TABLE = os.environ["ALBUMS_TABLE"] 
ALBUM_ID_INDEX = os.environ["ALBUM_ID_INDEX"] 
UPDATE_FILTER_LAMBDA = os.environ["UPDATE_FILTER_LAMBDA"]
FEED_UPDATE_QUEUE_URL = os.environ["FEED_UPDATE_QUEUE_URL"]
NEW_CONTENT_TOPIC_ARN = os.environ["NEW_CONTENT_TOPIC_ARN"]
albums_table = ddb.Table(ALBUMS_TABLE)

# DecimalEncoder i cors funkcije ostaju ISTE
class DecimalEncoder(json.JSONEncoder):
    # ... (kod DecimalEncoder-a je isti)
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)
def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

# Funkcija za konstruisanje URL-a za sliku ostaje ista
def _construct_image_url(image_key):
    """Konstruiše puni javni URL za sliku (cover)."""
    if not image_key:
        return None
    return f"https://{IMAGE_BUCKET}.s3.amazonaws.com/{image_key}"


# FUNKCIJA ZA DOBIJANJE ALBUMA (analogno _get_single_by_id)
def _get_album_by_id(albumId):
    """Dobavlja album iz DynamoDB koristeći GSI"""
    response = ddb_client.query(
        TableName=ALBUMS_TABLE,
        IndexName=ALBUM_ID_INDEX,
        KeyConditionExpression='albumId = :id',
        ExpressionAttributeValues={':id': {'S': albumId}}
    )
    if response['Items']:
        return boto3.dynamodb.types.TypeDeserializer().deserialize({'M': response['Items'][0]})
    return None

def handler(event, _):
    try:
        # Autorizacija: Proveravamo da li je Admin
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode":403,"headers":cors(),"body":json.dumps({"error": "Admin access required"})}
        
        albumId = event['pathParameters']['albumId'] # <-- albumId umesto singleId
        body = json.loads(event['body'])
        
        # Ažurirani podaci iz tela zahteva
        new_title = body.get('title')
        new_genres = body.get('genres')
        new_artist_ids = body.get('artistIds')
        new_artist_names = body.get('artistNames')
        new_image_key = body.get('coverKey') # Novi S3 ključ ako je slika zamenjena

        # Konverzija (isto kao za single)
        if isinstance(new_genres, (set, tuple)): new_genres = list(new_genres)
        if isinstance(new_artist_ids, (set, tuple)): new_artist_ids = list(new_artist_ids)
        
        # 1. DOBIJANJE POSTOJEĆEG ALBUMA
        old_item = _get_album_by_id(albumId)
        if not old_item:
            return {"statusCode":404,"headers":cors(),"body":json.dumps({"error": "Album not found"})}

        # Važni ključevi iz starog albuma
        old_artist_id = old_item['artistId']
        old_image_key = old_item.get('coverKey')
        
        # 2. VALIDACIJA PK (Isto kao za single)
        if old_artist_id not in new_artist_ids:
             return {"statusCode":400,"headers":cors(),"body":json.dumps({"error": "Original artistId must be present in new artistIds list."})}

        # 3. RUKOVANJE S3 FAJLOVIMA (Samo Image)
        current_image_key = old_image_key # Podrazumevano, zadržavamo stari ključ
        remove_expression = ""

        if new_image_key is not None and new_image_key != old_image_key:
            # Zamena slike: Koristimo novi ključ i brišemo stari
            if old_image_key:
                try:
                    s3.delete_object(Bucket=IMAGE_BUCKET, Key=old_image_key)
                    print(f"Obrisana stara cover slika: {old_image_key}")
                except ClientError as e:
                    print(f"Upozorenje: Nije moguće obrisati staru cover sliku {old_image_key}. Greška: {e}")
            current_image_key = new_image_key
        
        elif new_image_key is None and old_image_key:
             # Brisane slike: Klijent je poslao new_image_key = None, a stara je postojala.
             try:
                 s3.delete_object(Bucket=IMAGE_BUCKET, Key=old_image_key)
                 print(f"Obrisana stara cover slika jer je uklonjena: {old_image_key}")
             except ClientError as e:
                 print(f"Upozorenje: Nije moguće obrisati staru cover sliku (uklonjena) {old_image_key}. Greška: {e}")
             current_image_key = None
             remove_expression = " REMOVE coverKey" # <-- DODATO

        # 4. AŽURIRANJE DynamoDB-a
        update_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        if new_title is not None:
            update_parts.append("#title = :t")
            expression_attribute_names['#title'] = 'title'
            expression_attribute_values[':t'] = new_title
        
        if new_genres is not None:
            update_parts.append("genres = :g")
            expression_attribute_values[':g'] = new_genres
        
        if new_artist_ids is not None:
            update_parts.append("artistIds = :aId")
            expression_attribute_values[':aId'] = new_artist_ids
        
        if new_artist_names is not None:
            update_parts.append("artistNames = :aN")
            expression_attribute_values[':aN'] = new_artist_names

        # Rukovanje slikom u DynamoDB Update izrazu
        full_image_url = _construct_image_url(current_image_key) # Može biti None
        
        if current_image_key is not None and current_image_key != old_image_key:
            # Slika je zamenjena/dodata (SET)
            #update_parts.append("imageKey = :ik")
            update_parts.append("coverKey = :ik")
            expression_attribute_values[':ik'] = full_image_url
            
        # Ako je slika obrisana (remove_expression je već postavljen)
        
        update_parts.append("updatedAt = :u")
        expression_attribute_values[':u'] = datetime.datetime.now().isoformat()
        
        if not update_parts and not remove_expression:
            if not update_parts:
                update_parts.append("updatedAt = :u")

        update_expression = "SET " + ", ".join(update_parts)
        if remove_expression:
             update_expression += remove_expression

        # Izvršavanje DynamoDB ažuriranja
        albums_table.update_item( # <-- albums_table umesto singles_table
            Key={'artistId': old_artist_id, 'albumId': albumId}, # <-- albumId umesto singleId
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names if expression_attribute_names else None,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )
        
        # 5. POZIVANJE DRUGIH SERVISA (Filter i Feed)
        final_new_content = old_item.copy()
        if new_title is not None: final_new_content['title'] = new_title
        if new_genres is not None: final_new_content['genres'] = new_genres
        if new_artist_ids is not None: final_new_content['artistIds'] = new_artist_ids
        if new_artist_names is not None: final_new_content['artistNames'] = new_artist_names
        
        # Postavljanje URL-a slike u finalni objekat
        if full_image_url:
            final_new_content['coverKey'] = full_image_url
        elif 'coverKey' in final_new_content: # Ako je slika uklonjena
             del final_new_content['coverKey']

        final_new_content['updatedAt'] = expression_attribute_values[':u']
        
        # A. Ažuriranje Filter/Index tabele (Genre Index, Artist Index)
        payload_filter = {
            "contentId": albumId,
            "contentType": "album", # <-- album umesto single
            "oldContent": old_item,
            "newContent": final_new_content
        }
        
        lambda_client.invoke(
            FunctionName=UPDATE_FILTER_LAMBDA,
            InvocationType="Event", 
            Payload=json.dumps(payload_filter, cls=DecimalEncoder))
        
        print("Pozvana UPDATE_FILTER_LAMBDA za album")

        # B. Ažuriranje Feed-a (šaljemo poruku u SQS red)
        payload_feed = {
            "content": final_new_content,
            "contentId": albumId,
            "contentType": "album", # <-- album umesto single
            "genres": json.dumps(list(final_new_content.get('genres', []))),
        }
        sqs_client.send_message(
            QueueUrl=FEED_UPDATE_QUEUE_URL,
            MessageBody=json.dumps(payload_feed, cls=DecimalEncoder)
        )
        print("Poslata poruka u SQS za ažuriranje Feed-a za album")

        # C. SNS notifikacija
        try:
            sns_message = {
                'contentType': 'album', # <-- album umesto single
                'contentId': albumId,
                'title': final_new_content.get('title'),
                'artistIds': final_new_content.get('artistIds'),
                'artistNames': final_new_content.get('artistNames'),
                'genres': final_new_content.get('genres'),
                'action': 'UPDATE'
            }
            sns.publish(
                TopicArn=NEW_CONTENT_TOPIC_ARN,
                Message=json.dumps({'default': json.dumps(sns_message, cls=DecimalEncoder)}),
                MessageStructure='json'
            )
            print(f"Published SNS message for album update {albumId}")
        except Exception as sns_error:
            print(f"Error publishing SNS update message: {str(sns_error)}")


        return {"statusCode":200,"headers":cors(),"body":json.dumps({"message": f"Album {albumId} updated successfully"})}
        
    except Exception as e:
        print(f"Greška pri ažuriranju albuma: {str(e)}")
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error": str(e)})}