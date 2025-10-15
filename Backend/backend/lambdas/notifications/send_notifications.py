import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Inicijalizacija AWS klijenata
dynamodb = boto3.resource("dynamodb")
# AWS SES (Simple Email Service) klijent za slanje email-ova
# ses_client = boto3.client("ses") 

# Učitavanje imena resursa iz environment varijabli
TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
GSI_NAME = os.environ["GSI_NAME"]
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    """
    Ova funkcija se pokreće kada stigne poruka u SQS red.
    Poruka sadrži informacije o novom sadržaju (npr. pesmi).
    """
    print(f"Received event: {json.dumps(event)}")
    
    all_usernames_to_notify = set()

    # SQS može poslati više poruka odjednom (batch)
    for record in event.get("Records", []):
        try:
            # Poruka sa SNS-a je u 'body' polju SQS record-a
            message_body = json.loads(record.get("body", "{}"))
            # SNS poruka je omotana, stvarni podaci su u 'Message' ključu
            content_data = json.loads(message_body.get("Message", "{}"))
            
            print(f"Processing new content: {content_data}")

            artist_id = content_data.get("artistId")
            genre_ids = content_data.get("genreIds", [])

            # 1. Pronađi sve korisnike pretplaćene na umetnika
            if artist_id:
                subscribers = find_subscribers(artist_id, "ARTIST")
                for user in subscribers:
                    all_usernames_to_notify.add(user["username"])

            # 2. Pronađi sve korisnike pretplaćene na žanrove
            for genre_id in genre_ids:
                subscribers = find_subscribers(genre_id, "GENRE")
                for user in subscribers:
                    all_usernames_to_notify.add(user["username"])

        except Exception as e:
            print(f"Error processing a record: {e}")
            # Nastavljamo sa sledećom porukom u batch-u
            continue

    # 3. Pošalji notifikacije svim jedinstvenim korisnicima
    if not all_usernames_to_notify:
        print("No users to notify for this event.")
        return

    print(f"Sending notifications to {len(all_usernames_to_notify)} users: {list(all_usernames_to_notify)}")
    
    for username in all_usernames_to_notify:
        try:
            # === PLACEHOLDER ZA SLANJE NOTIFIKACIJE ===
            # Ovde dolazi tvoja logika za slanje email-a, SMS-a ili WebSocket poruke.
            # Na primer, slanje email-a preko AWS SES servisa:
            
            # user_email = get_user_email(username) # Funkcija koja dobavlja email iz Cognita
            # if user_email:
            #     ses_client.send_email(
            #         Source='tvoj.verifikovani.email@domen.com',
            #         Destination={'ToAddresses': [user_email]},
            #         Message={
            #             'Subject': {'Data': 'Novi sadržaj je stigao!'},
            #             'Body': {'Text': {'Data': f'Zdravo {username}, poslušaj novu pesmu!'}}
            #         }
            #     )
            print(f"--> PLACEHOLDER: Sending notification to user '{username}'...")
            
        except Exception as e:
            print(f"Failed to send notification to {username}: {e}")

    print("Finished processing event.")
    # Nije potreban return jer je SQS trigger asinhron
    return


def find_subscribers(target_id, subscription_type):
    """
    Pomoćna funkcija koja koristi GSI za pronalaženje svih pretplatnika
    za dati targetId i tip pretplate.
    """
    try:
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('targetId').eq(target_id),
            FilterExpression=Attr('subscriptionType').eq(subscription_type)
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error querying GSI for target {target_id}: {e}")
        return []