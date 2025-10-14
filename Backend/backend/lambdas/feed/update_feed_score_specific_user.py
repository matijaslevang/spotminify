import os
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table_score_cache = dynamodb.Table(os.environ["SCORE_TABLE_NAME"])

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
                score_entry = response.get("Item")

                scores: dict = score_entry.get("scores", {})

            except Exception as e:
                print(f"Failed to fetch score for {username}: {e}")

            # 2. update score based on type of message
            # activity, rating, artist subscription, genre subscription
            update_type = message["type"]
            incoming_score = message["incomingScore"]
            update_feed = False # TODO: think if we should update feed like this, when should feed EXACTLY be updated?

            if update_type == "activity":
                incoming_score *= 1
            elif update_type == "rating": 
                incoming_score *= 10
                update_feed = True
            elif update_type == "artsub":
                incoming_score *= 1000
                update_feed = True
            elif update_type == "gensub":
                incoming_score *= 500
                update_feed = True
            else:
                raise Exception("Invalid type")
            
            genres = message["genres"]
            for genre in genres:
                scores[genre] = scores.get(genre, 0) + incoming_score

            # 3. write final score in table
            table_score_cache.put_item(
                Item={
                    "username": username,
                    "scores": scores
                }
            )

        except Exception as e:
            print(f"Error: {e}")