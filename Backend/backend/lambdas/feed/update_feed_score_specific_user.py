import os
import json
import boto3

sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
table_score_cache = dynamodb.Table(os.environ["SCORE_TABLE_NAME"])
queue_url = os.environ["QUEUE_URL"]

def handler(event, context):
    for record in event['Records']:
        body = record['body']

        try:
            message = json.loads(body)

            # UPDATE A USERNAME'S SCORE:
            username = message["username"]

            # 1. get user's score
            try:
                response = table_score_cache.get_item(
                    Key={"username": username}
                )
                score_entry = response.get("Item", {})

                scores: dict = score_entry.get("scores", {})

            except Exception as e:
                print(f"Failed to fetch score for {username}: {e}")

            # 2. update score based on type of message
            # activity, rating, artist subscription, genre subscription
            update_type = message["type"]
            incoming_score = message["incomingScore"]
            
            if update_type == "activity":
                incoming_score *= 1
            elif update_type == "rating": 
                incoming_score *= 10
            elif update_type == "artsub":
                incoming_score *= 1000
            elif update_type == "gensub":
                incoming_score *= 500
            else:
                raise Exception("Invalid type")
            
            genres = json.loads(message["genres"])
            print(genres)
            for genre in genres:
                scores[genre] = scores.get(genre, 0) + incoming_score

            # 3. write final score in table
            table_score_cache.put_item(
                Item={
                    "username": username,
                    "scores": scores
                }
            )

            # 4. update feed for specific user
            print("send message")
            payload = {
                "username": username
            }
            response = sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(payload)
            )

        except Exception as e:
            print(f"Error: {e}")