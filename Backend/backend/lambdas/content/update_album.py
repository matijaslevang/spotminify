import os
import json
import uuid
import boto3
from urllib.parse import urlparse, parse_qs
from requests_toolbelt.multipart import decoder
from decimal import Decimal

# Inicijalizacija AWS klijenata
s3 = boto3.client("s3")
ddb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

# Varijable okruženja
ALBUMS_TABLE = os.environ["ALBUMS_TABLE"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]
FILTER_UPDATE_LAMBDA = os.environ.get("FILTER_UPDATE_LAMBDA", "filter-update-album-placeholder") # Predpostavka: treba nam i filter update
NEW_CONTENT_TOPIC_ARN = os.environ.get("NEW_CONTENT_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:new-content-topic")

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def get_current_album(album_id: str, artist_id: str):
    """Pronađi trenutne podatke o albumu koristeći njegov ID i ArtistId (PK)."""
    try:
        response = ddb.get_item(
            TableName=ALBUMS_TABLE,
            Key={
                'artistId': {'S': artist_id},
                'albumId': {'S': album_id}
            }
        )
        # Boto3 vraća Dict sa tipovima podataka (npr. {'S': 'value'}). Ovo je jednostavan način za dekodiranje.
        return response.get('Item')
    except Exception as e:
        print(f"Error fetching album {album_id}: {str(e)}")
        return None

def ddb_item_to_dict(ddb_item):
    """
    Pomoćna funkcija za pretvaranje DynamoDB stavke u običan Python rječnik.
    Pojednostavljeno: obrađuje samo tipove String (S) i String Set (SS).
    """
    if not ddb_item:
        return {}
    
    result = {}
    for key, value in ddb_item.items():
        if 'S' in value:
            result[key] = value['S']
        elif 'SS' in value:
            result[key] = value['SS']
    return result

def get_s3_key_from_url(url):
    """Ekstrahuje S3 ključ iz punog S3 URL-a."""
    try:
        if not url:
            return None
        # Prvo parsujemo URL
        parsed_url = urlparse(url)
        # path je obično ključ (bez vodeće kose crte)
        # Trimujemo prvu '/' ako postoji
        key = parsed_url.path.lstrip('/')
        return key if key else None
    except:
        return None

def handler(event, _):
    try:
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode": 403, "headers": cors(), "body": json.dumps({"error": "forbidden"})}

        # RUKOVANJE MULTIPART/FORM-DATA
        content_type_header = event["headers"].get("content-type") or event["headers"].get("Content-Type")
        
        # Ako nema Content-Type, pretpostavljamo da je FormData ili JSON (mada bi trebalo biti FormData)
        if not content_type_header:
             return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "Missing Content-Type header"})}
        
        # Dekodovanje FormData (binarni dio)
        body = event["body"]
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body)

        data = {}
        file_to_upload = None
        
        # Toolbelt dekoder za multipart/form-data
        for part in decoder.MultipartDecoder(body, content_type_header).parts:
            headers = part.headers
            content_disp = headers.get(b'Content-Disposition', b'').decode('utf-8')
            
            # Ekstrahuj ime polja
            name_match = next((p.split('=')[1].strip('"') for p in content_disp.split(';') if p.strip().startswith('name=')), None)
            
            if name_match:
                # Polje je fajl (cover)
                if name_match == "cover" and part.content:
                    # Kreiramo S3 ključ za novu sliku
                    new_image_key = f"album-covers/{uuid.uuid4()}"
                    file_to_upload = {
                        "key": new_image_key,
                        "content": part.content,
                        "content_type": part.headers.get(b'Content-Type', b'image/jpeg').decode('utf-8')
                    }
                    data["coverKey"] = new_image_key
                # Polje je regularna forma
                elif name_match in ["title", "albumId", "artistIds", "genres", "currentArtistId"]:
                    value = part.content.decode('utf-8')
                    if name_match in ["artistIds", "genres"]:
                        # Rukovanje nizovima koji dolaze kao ponovljena polja u FormData
                        if name_match not in data:
                            data[name_match] = []
                        data[name_match].append(value)
                    else:
                        data[name_match] = value
                
        # Validacija potrebnih polja
        album_id = data.get("albumId")
        # Primarni ključ (artistId) mora biti dostavljen da bi se pronašao album u DynamoDB-u
        # Trenutni PK je neophodan da bismo pronašli stavku u DDB (jer je PK composite key)
        current_artist_id = data.get("currentArtistId") 
        title = data.get("title", "").strip()
        artistIds = data.get("artistIds")
        genres = data.get("genres")
        
        if not album_id: return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "albumId required"})}
        if not current_artist_id: return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "currentArtistId (PK) required"})}
        if not title: return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "title required"})}
        if not artistIds: return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "artistIds required"})}
        
        # DOHVAT TRENUTNIH PODATAKA ALBUMA
        current_album_item = get_current_album(album_id, current_artist_id)
        if not current_album_item:
             return {"statusCode": 404, "headers": cors(), "body": json.dumps({"error": f"Album with ID {album_id} not found."})}
        
        current_album_dict = ddb_item_to_dict(current_album_item)
        
        # PROVJERA PROMJENE PK
        # Ako je ArtistId (PK) promijenjen, morate obrisati stari i kreirati novi unos.
        # U ovom scenariju, ArtistId je prvi element liste artistIds.
        new_pk_artist_id = artistIds[0]
        pk_changed = new_pk_artist_id != current_artist_id
        
        # 1. PRIPREMA AŽURIRANJA I MIGRACIJA SLIKE
        
        # Inicijalizacija ključeva za DynamoDB UpdateExpression
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}
        remove_expression_parts = []
        
        # Definisanje novog S3 ključa i URL-a
        new_image_key = None
        
        # Da li je korisnik uploadovao novu sliku?
        if file_to_upload:
            # Upload nove slike na S3
            s3.put_object(
                Bucket=IMAGES_BUCKET,
                Key=file_to_upload["key"],
                Body=file_to_upload["content"],
                ContentType=file_to_upload["content_type"]
            )
            new_image_key = file_to_upload["key"]
            
            # Brišemo staru sliku (ako je postojala)
            old_image_url = current_album_dict.get("coverKey")
            old_image_key = get_s3_key_from_url(old_image_url)
            
            # Samo brišemo ako je ključ zaista bio u našem album-covers folderu
            if old_image_key and old_image_key.startswith("album-covers/"):
                s3.delete_object(Bucket=IMAGES_BUCKET, Key=old_image_key)
                print(f"Deleted old image: {old_image_key}")

        # Ako nije uploadovana nova slika, ali je polje coverKey postojalo, zadržavamo staru
        # Ako coverKey nije bio prisutan u FormData (što je default ponašanje kod nas), koristi se stara vrednost.
        # Ako je coverKey eksplicitno null/prazno (što je teško iz FormDatea), onda ga brišemo.
        
        # UPDATE ATRIBUTA
        
        # Ažuriranje Naslova
        update_expression_parts.append("#t = :t")
        expression_attribute_names["#t"] = "title"
        expression_attribute_values[":t"] = {"S": title}

        # Ažuriranje Žanrova
        update_expression_parts.append("genres = :g")
        expression_attribute_values[":g"] = {"SS": genres}

        # Ažuriranje Artist ID-eva
        update_expression_parts.append("artistIds = :a")
        expression_attribute_values[":a"] = {"SS": artistIds}
        
        # Ažuriranje Slike
        if new_image_key:
            # Postavili smo novu sliku
            full_image_url = f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{new_image_key}"
            update_expression_parts.append("coverKey = :ck")
            expression_attribute_values[":ck"] = {"S": full_image_url}
        else:
            # Koristimo staru sliku. Ovdje je ključno: ako nije poslan novi fajl, 
            # DDB operacija ne treba da dira stari coverKey polje. 
            # U ovom kodu, polje se diralo samo ako je poslan novi fajl (kao gore). 
            # Dakle, ako new_image_key nije setovan, stari coverKey ostaje u item-u.
            pass

        # 2. IZVRŠAVANJE DYNAMODB OPERACIJE
        
        # Ako se Partition Key (artistId) mijenja, moramo obrisati stari item i kreirati novi.
        # Ako artistIds polje postoji i prvi ID se promijenio, to je promena PK.
        if pk_changed:
            
            # 2a. Brisanje starog item-a
            ddb.delete_item(
                TableName=ALBUMS_TABLE,
                Key={
                    'artistId': {'S': current_artist_id},
                    'albumId': {'S': album_id}
                }
            )
            
            # 2b. Kreiranje novog item-a (sa novim PK)
            # Kopiramo stare podatke i prebrisujemo nove
            new_item = current_album_item.copy()
            # Ažuriranje PK/SK
            new_item['artistId'] = {'S': new_pk_artist_id}
            # Ažuriranje polja
            new_item['title'] = {'S': title}
            new_item['genres'] = {'SS': genres}
            new_item['artistIds'] = {'SS': artistIds}
            
            if new_image_key:
                 new_item['coverKey'] = {'S': f"https://{IMAGES_BUCKET}.s3.amazonaws.com/{new_image_key}"}
            elif "coverKey" in new_item:
                 # Ako coverKey nije promijenjen, DDB ga vraća u starom formatu.
                 pass
            
            ddb.put_item(TableName=ALBUMS_TABLE, Item=new_item)
            
            print(f"Album {album_id}: PK changed from {current_artist_id} to {new_pk_artist_id}. Item migrated.")

        else:
            # Ako je Partition Key isti, radimo standardni UpdateItem
            update_expression = "SET " + ", ".join(update_expression_parts)
            
            # Ako ima polja za brisanje (u ovom scenariju nema, ali za budućnost)
            if remove_expression_parts:
                update_expression += " REMOVE " + ", ".join(remove_expression_parts)
            
            ddb.update_item(
                TableName=ALBUMS_TABLE,
                Key={
                    'artistId': {'S': current_artist_id}, # PK je star/trenutni
                    'albumId': {'S': album_id} # SK
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="UPDATED_NEW"
            )
            print(f"Album {album_id} updated.")

        # 3. POZIV FILTER LAMBDA FUNKCIJE ZA AŽURIRANJE INDEKSA
        # Učitavamo ažuriranu stavku da bismo je poslali filter funkciji
        updated_album = get_current_album(album_id, new_pk_artist_id if pk_changed else current_artist_id)
        updated_album_content = ddb_item_to_dict(updated_album)

        payload_filter = {
            "contentId": album_id,
            "contentType": "album",
            "content": updated_album_content,
        }
        lambda_client.invoke(
            FunctionName=FILTER_UPDATE_LAMBDA,
            InvocationType="Event",
            Payload=json.dumps(payload_filter)
        )
        print(f"Invoked Filter Update for album {album_id}")

        # 4. PUBLIKOVANJE SNS PORUKE (Opcionalno - za notifikaciju)
        # Ovu sekciju možete koristiti za obavještavanje drugih servisa o promjeni.
        # Možda želite da obavijestite sistem za feed o ažuriranju.
        # try:
        #     sns_message = {
        #         'contentType': 'album_updated',
        #         'contentId': album_id,
        #         'title': title,
        #         'artistIds': artistIds,
        #         'genres': genres
        #     }
        #     # sns.publish(...
        # except Exception as sns_error:
        #     print(f"Error publishing SNS message for album {album_id}: {str(sns_error)}")

        return {"statusCode": 200, "headers": cors(), "body": json.dumps({"albumId": album_id, "message": "Album successfully updated"})}

    except Exception as e:
        print(f"Global error: {str(e)}")
        # Vratićemo HTTP 500 sa greškom.
        return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": str(e)})}
