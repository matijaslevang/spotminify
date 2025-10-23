import os, json, uuid, boto3, datetime
from botocore.exceptions import ClientError
from decimal import Decimal

s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb")
ddb_client = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")
sns = boto3.client("sns")
sqs_client = boto3.client('sqs')

# Env varijable
SINGLES_TABLE = os.environ["SINGLES_TABLE"]
SINGLE_ID_INDEX = os.environ["SINGLE_ID_INDEX"]
AUDIO_BUCKET = os.environ["AUDIO_BUCKET"]
IMAGE_BUCKET = os.environ["IMAGE_BUCKET"]
UPDATE_FILTER_LAMBDA = os.environ["UPDATE_FILTER_LAMBDA"]
FEED_UPDATE_QUEUE_URL = os.environ["FEED_UPDATE_QUEUE_URL"]
NEW_CONTENT_TOPIC_ARN = os.environ["NEW_CONTENT_TOPIC_ARN"]

singles_table = ddb.Table(SINGLES_TABLE)

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }
def _construct_audio_url(audio_key):
    """Konstruiše puni javni URL za audio fajl."""
    if not audio_key:
        return None
    return f"https://{AUDIO_BUCKET}.s3.amazonaws.com/{audio_key}"

def _construct_image_url(image_key):
    """Konstruiše puni javni URL za sliku."""
    if not image_key:
        return None
    return f"https://{IMAGE_BUCKET}.s3.amazonaws.com/{image_key}"

def _get_single_by_id(singleId):
    """Dobavlja single iz DynamoDB koristeći GSI"""
    response = ddb_client.query(
        TableName=SINGLES_TABLE,
        IndexName=SINGLE_ID_INDEX,
        KeyConditionExpression='singleId = :id',
        ExpressionAttributeValues={':id': {'S': singleId}}
    )
    # GSI na singleId bi trebalo da vrati samo jedan rezultat
    if response['Items']:
        # Konvertuje DynamoDB format u standardni Python dict
        return boto3.dynamodb.types.TypeDeserializer().deserialize({'M': response['Items'][0]})
    return None

def handler(event, _):
    try:
        # Autorizacija: Proveravamo da li je Admin
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode":403,"headers":cors(),"body":json.dumps({"error": "Admin access required"})}
        
        singleId = event['pathParameters']['singleId']
        body = json.loads(event['body'])
        
        # Ažurirani podaci iz tela zahteva
        new_title = body.get('title')
        new_genres = body.get('genres')
        new_artist_ids = body.get('artistIds')
        new_artist_names = body.get('artistNames')
        new_explicit = body.get('explicit')
        new_audio_key = body.get('audioKey') # Novi S3 ključ ako je fajl zamenjen
        new_image_key = body.get('imageKey') # Novi S3 ključ ako je slika zamenjena

        if isinstance(new_genres, (set, tuple)):
             new_genres = list(new_genres)
        
        if isinstance(new_artist_ids, (set, tuple)):
             new_artist_ids = list(new_artist_ids)
        
        # 1. DOBIJANJE POSTOJEĆEG SINGLA
        old_item = _get_single_by_id(singleId)
        if not old_item:
            return {"statusCode":404,"headers":cors(),"body":json.dumps({"error": "Single not found"})}

        # Važni ključevi iz starog singla
        old_artist_id = old_item['artistId']
        old_audio_key = old_item['audioKey']
        old_image_key = old_item.get('imageKey')
        
        # Ažurirani podaci iz tela zahteva
        new_title = body.get('title')
        new_genres = body.get('genres')
        new_artist_ids = body.get('artistIds')
        new_artist_names = body.get('artistNames')
        new_explicit = body.get('explicit')
        new_audio_key = body.get('audioKey') # Novi S3 ključ ako je fajl zamenjen
        new_image_key = body.get('imageKey') # Novi S3 ključ ako je slika zamenjena

        if isinstance(new_genres, (set, tuple)):
             new_genres = list(new_genres)
        
        if isinstance(new_artist_ids, (set, tuple)):
             new_artist_ids = list(new_artist_ids)
             
        # 2. VALIDACIJA (Proveravamo da li se primarni ključ menja)
        # Ako se ArtistId promenio, moramo obrisati stari i kreirati novi unos.
        # Ako je stari ArtistId različit od bilo kog u novoj listi, to je kritičan problem.
        # U ovom sistemu, single uvek pripada jednom glavnom artistu (artistId je PK). 
        # Ako se stari artistId ne nalazi u novoj listi, to je greška.

        if old_artist_id not in new_artist_ids:
            return {"statusCode":400,"headers":cors(),"body":json.dumps({"error": "Original artistId must be present in new artistIds list."})}


        # 3. RUKOVANJE S3 FAJLOVIMA (Audio i Image)
    
        # 3a. AUDIO ZAMENA
        current_audio_key = old_audio_key # Podrazumevano, zadržavamo stari ključ
        if new_audio_key and new_audio_key != old_audio_key:
            # Novi fajl je uploadovan, brišemo stari
            try:
                s3.delete_object(Bucket=AUDIO_BUCKET, Key=old_audio_key)
                print(f"Obrisan stari audio fajl: {old_audio_key}")
            except ClientError as e:
                # Brišemo samo ako fajl postoji; u produkciji je ovo često samo upozorenje
                print(f"Upozorenje: Nije moguće obrisati stari audio fajl {old_audio_key}. Greška: {e}")
            current_audio_key = new_audio_key # Nastavljamo sa novim ključem  # BITNOO
            
        # ----- image -------
        current_image_key = old_image_key # Podrazumevano, zadržavamo stari ključ
        print('New image key')
        print(new_image_key)
        if new_image_key is not None and new_image_key != old_image_key:
            # Zamena slike: Koristimo novi ključ i brišemo stari
            if old_image_key:
                try:
                    s3.delete_object(Bucket=IMAGE_BUCKET, Key=old_image_key)
                    print(f"Obrisana stara slika: {old_image_key}")
                except ClientError as e:
                    print(f"Upozorenje: Nije moguće obrisati staru sliku {old_image_key}. Greška: {e}")
            current_image_key = new_image_key
            
        # elif new_image_key is None and old_image_key:
        #     # Brisane slike: Klijent je poslao new_image_key = None, a stara je postojala.
        #     try:
        #         s3.delete_object(Bucket=IMAGE_BUCKET, Key=old_image_key)
        #         print(f"Obrisana stara slika jer je uklonjena: {old_image_key}")
        #     except ClientError as e:
        #         print(f"Upozorenje: Nije moguće obrisati staru sliku (uklonjena) {old_image_key}. Greška: {e}")
        #     current_image_key = None
        # 4. AŽURIRANJE DynamoDB-a
        
        # Dinamičko kreiranje UpdateExpression-a
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
        
        if new_explicit is not None:
            update_parts.append("explicit = :e")
            expression_attribute_values[':e'] = new_explicit
        
        full_audio_url = old_audio_key
        if current_audio_key != old_audio_key:
            full_audio_url = _construct_audio_url(current_audio_key) # kriticnoo
            update_parts.append("audioKey = :ak")
            expression_attribute_values[':ak'] = current_audio_key
            # expression_attribute_values[':ak'] = full_audio_url PRE RADILO OVO
        
        update_parts.append("updatedAt = :u")
        expression_attribute_values[':u'] = datetime.datetime.now().isoformat()       
        
        remove_expression = ""
        #PROBLEM
        full_image_url = old_image_key
        
        if current_image_key!=old_image_key:
            # Slika postoji (bilo stara, bilo nova)
            full_image_url = _construct_image_url(current_image_key)
            update_parts.append("imageKey = :ik")
            expression_attribute_values[':ik'] = current_image_key
            # expression_attribute_values[':ik'] = full_image_url RADILO
            
        # elif old_image_key and current_image_key is None:
        #     remove_expression = " REMOVE imageKey"
     
        if not update_parts and not remove_expression:
            # Dodajemo barem updatedAt da bi izraz bio validan
            if not update_parts:
                update_parts.append("updatedAt = :u")

        update_expression = "SET " + ", ".join(update_parts) + remove_expression

        # Izvršavanje DynamoDB ažuriranja
        singles_table.update_item(
            Key={'artistId': old_artist_id, 'singleId': singleId},
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
        if new_explicit is not None: final_new_content['explicit'] = new_explicit
        
        #final_new_content['audioKey'] = current_audio_key
        final_new_content['audioKey'] = full_audio_url
        print('Full audio')
        print(full_audio_url)
       
        print('Full image')
        print(full_image_url)
        
        if full_image_url:
            final_new_content['imageKey'] = full_image_url
        elif 'imageKey' in final_new_content:
            del final_new_content['imageKey']
            
        final_new_content['updatedAt'] = expression_attribute_values[':u']
        
        # A. Ažuriranje Filter/Index tabele (Genre Index, Artist Index)
        payload_filter = {
            "contentId": singleId,
            "contentType": "single",
            "oldContent": old_item,
            "newContent": final_new_content
        }
        
        lambda_client.invoke(
            FunctionName=UPDATE_FILTER_LAMBDA,
            InvocationType="Event", # Asinhroni poziv
            Payload=json.dumps(payload_filter)
        )
        print("Pozvana UPDATE_FILTER_LAMBDA")

        # B. Ažuriranje Feed-a (šaljemo poruku u SQS red)
        # Feed se ažurira na isti način kao kod kreiranja
        payload_feed = {
            "content": final_new_content,
            "contentId": singleId,
            "contentType": "single",
            "genres": json.dumps(list(final_new_content.get('genres', []))),
        }
        sqs_client.send_message(
            QueueUrl=FEED_UPDATE_QUEUE_URL,
            MessageBody=json.dumps(payload_feed)
        )
        print("Poslata poruka u SQS za ažuriranje Feed-a")

        # C. SNS notifikacija (opciono, ako se želi obavestiti korisnik o ažuriranju)
        # Neki sistemi preskaču SNS za ažuriranja, ali ćemo ga ovde uključiti:
        try:
            sns_message = {
                'contentType': 'single',
                'contentId': singleId,
                'title': final_new_content.get('title'),
                'artistIds': final_new_content.get('artistIds'),
                'artistNames': final_new_content.get('artistNames'),
                'genres': final_new_content.get('genres'),
                'action': 'UPDATE'
            }
            sns.publish(
                TopicArn=NEW_CONTENT_TOPIC_ARN,
                Message=json.dumps({'default': json.dumps(sns_message)}),
                MessageStructure='json'
            )
            print(f"Published SNS message for single update {singleId}")
        except Exception as sns_error:
            print(f"Error publishing SNS update message: {str(sns_error)}")


        return {"statusCode":200,"headers":cors(),"body":json.dumps({"message": f"Single {singleId} updated successfully"})}
        
    except Exception as e:
        print(f"Greška pri ažuriranju singla: {str(e)}")
        return {"statusCode":500,"headers":cors(),"body":json.dumps({"error": str(e)})}
