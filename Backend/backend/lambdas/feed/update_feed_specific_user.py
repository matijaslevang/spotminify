import os
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table_score_cache = dynamodb.Table(os.environ["SCORE_TABLE_NAME"])
table_feed_cache = dynamodb.Table(os.environ["FEED_TABLE_NAME"])

def handler(event, context):
    for record in event['Records']:
        body = record['body']

        try:
            message = json.loads(body)

            # UPDATE A USERNAME'S FEED FROM SCRATCH

            # 1. get user's scores
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
            
            # 2. get all content
            # TODO
            # get all artists
            # get all songs
            # get all albums

            # 3. assign scores to everything

            # 4. save only the top X artists, top X songs, top X albums

        except Exception as e:
            print(f"Error: {e}")