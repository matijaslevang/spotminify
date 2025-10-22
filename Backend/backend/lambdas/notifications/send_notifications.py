import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

ses_client = boto3.client('ses', region_name='eu-central-1')
cognito_client = boto3.client('cognito-idp', region_name='eu-central-1')
dynamodb = boto3.resource("dynamodb")

SUBSCRIPTIONS_TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE_NAME"]
SUBSCRIPTIONS_GSI_NAME = os.environ["GSI_NAME"]
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)

USER_POOL_ID = os.environ["USER_POOL_ID"]
SENDER_EMAIL = "diirrektorr@gmail.com"

ARTISTS_TABLE_NAME = os.environ["ARTISTS_TABLE_NAME"]
artists_table = dynamodb.Table(ARTISTS_TABLE_NAME)

def handler(event, context):
    print(f"Received event: {json.dumps(event)}")
    
    all_usernames_to_notify = set()
    processed_content_details = {}

    for record in event.get("Records", []):
        try:
            message_body_str = record.get("body", "{}")
            message_body = json.loads(message_body_str)
            content_data_str = message_body.get("Message", "{}")
            content_data = json.loads(content_data_str)
            
            print(f"Processing content data: {content_data}")

            artist_ids = content_data.get("artistIds", [])
            genre_names = content_data.get("genres", []) 
            content_title = content_data.get("title", "Unknown Title")
            content_type = content_data.get("contentType", "content")
            content_id = content_data.get("contentId")

            if content_id not in processed_content_details:
                artist_names = get_artist_names_from_ids(artist_ids)
                processed_content_details[content_id] = {
                    "title": content_title,
                    "type": content_type,
                    "artist_names": artist_names,
                    "genre_names": genre_names
                }

            for artist_id in artist_ids:
                subscribers = find_subscribers(artist_id, "ARTIST")
                for user in subscribers:
                    all_usernames_to_notify.add(user["username"])

            for genre_name in genre_names:
                subscribers = find_subscribers(genre_name, "GENRE")
                for user in subscribers:
                    all_usernames_to_notify.add(user["username"])

        except Exception as e:
            print(f"Error processing a record: {e}\nRecord body: {message_body_str}")
            continue

    if not all_usernames_to_notify:
        print("No users to notify for this event.")
        return

    print(f"Sending notifications to {len(all_usernames_to_notify)} users...")
    
    details = list(processed_content_details.values())[0] if processed_content_details else {}
    email_subject = f"New {details.get('type', 'content').capitalize()} Alert: {details.get('title', 'New Content')}"
    body_lines = [
        f"Check out the new {details.get('type', 'content')}: '{details.get('title', 'New Content')}'!"
    ]
    if details.get('artist_names'):
        body_lines.append(f"Artist(s): {', '.join(details['artist_names'])}")
    if details.get('genre_names'):
        body_lines.append(f"Genre(s): {', '.join(details['genre_names'])}")
    email_body = "\n".join(body_lines)
    for username in all_usernames_to_notify:
        try:
            user_email = get_user_email(username)
            if user_email:
                send_email_notification(user_email, username, email_subject, email_body)
            else:
                print(f"Could not find email for user {username}")
        except Exception as e:
            print(f"Failed processing notification for {username}: {e}")

    print("Finished processing event.")
    return


def find_subscribers(target_id, subscription_type):
    try:
        response = subscriptions_table.query(
            IndexName=SUBSCRIPTIONS_GSI_NAME,
            KeyConditionExpression=Key('targetId').eq(target_id),
            FilterExpression=Attr('subscriptionType').eq(subscription_type)
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error querying Subscriptions GSI for target {target_id} ({subscription_type}): {e}")
        return []

def get_user_email(username):
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                return attr['Value']
        return None
    except cognito_client.exceptions.UserNotFoundException:
         print(f"User {username} not found in Cognito.")
         return None
    except Exception as e:
        print(f"Error getting email for {username}: {e}")
        return None

def send_email_notification(recipient_email, username, subject, body_text):
    try:
        full_body = f"Hi {username},\n\n{body_text}\n\nEnjoy!"
        ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': full_body, 'Charset': 'UTF-8'}}
            }
        )
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")

def get_artist_names_from_ids(artist_ids):
    if not artist_ids:
        return []

    keys_to_get = [{'artistId': artist_id} for artist_id in artist_ids]
    artist_names = []

    try:
        response = dynamodb.batch_get_item(
            RequestItems={
                ARTISTS_TABLE_NAME: {
                    'Keys': keys_to_get,
                    'ProjectionExpression': 'artistId, #nm',
                    'ExpressionAttributeNames': {'#nm': 'name'}
                }
            }
        )
        
        items = response.get('Responses', {}).get(ARTISTS_TABLE_NAME, [])
        name_map = {item['artistId']: item.get('name', 'Unknown') for item in items}
        
        artist_names = [name_map.get(artist_id, 'Unknown') for artist_id in artist_ids]

    except Exception as e:
        print(f"Error getting artist names for IDs {artist_ids}: {e}")
        artist_names = ['Error fetching names'] * len(artist_ids)

    return artist_names