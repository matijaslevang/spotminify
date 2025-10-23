import os
import json
import boto3

client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
table_score_cache = dynamodb.Table(os.environ["SCORE_TABLE_NAME"])
table_feed_cache = dynamodb.Table(os.environ["FEED_TABLE_NAME"])
user_pool_id = os.environ["USER_POOL_ID"]

def handler(event, context):
    for record in event['Records']:
        body = record['body']

        try:
            message = json.loads(body)

            # 1. get all users
            pagination_token = None
            usernames = []

            while True:
                params = {
                    "UserPoolId": user_pool_id,
                    "Limit": 60,
                }
                if pagination_token:
                    params["PaginationToken"] = pagination_token

                try:
                    response = client.list_users(**params)
                except client.exceptions.InvalidParameterException as e:
                    print(f"Invalid Parameter: {e}")
                    break
                except Exception as e:
                    print(f"Error during list_users: {e}")
                    break

                print(response)
                for user in response["Users"]:
                    usernames.append(user["Username"])

                pagination_token = response.get("PaginationToken")
                if not pagination_token:
                    break

            # LOOP:
            print(usernames)
            
            for username in usernames:
                # 2. get user's scores
                song_score = 0
                try:
                    response = table_score_cache.get_item(
                        Key={"username": username}
                    )
                    score_entry = response.get("Item", {})

                    scores: dict = score_entry.get("scores", {})

                except Exception as e:
                    print(f"Failed to fetch score for {username}: {e}")

                # 3. calculate new content's score
                genres = json.loads(message["genres"])
                for genre in genres:
                    song_score += scores.get(genre, 0)

                # a small boost because it is new content
                song_score *= 10
                # 4. get user's cached feed
                response = table_feed_cache.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('username').eq(username)
                )
                user_feed = response.get("Items", [])
                filtered_feed = [item for item in user_feed if item["contentType"] == message["contentType"]]
                element_number = 10

                if filtered_feed:
                # 5. add to feed if it has enough score
                    lowest = min(filtered_feed, key=lambda x: x["score"])
                
                    if lowest["score"] < song_score and len(filtered_feed) == element_number:
                        
                        # delete lowest score song from user's feed
                        table_feed_cache.delete_item(
                            Key={
                                "username": username,
                                "contentId": lowest["contentId"]
                            }
                        )
                    
                    # add current song to user's feed
                table_feed_cache.put_item(
                    Item={
                        "username": username,
                        "contentId": message["contentId"],
                        "score": song_score,
                        "contentType": message["contentType"],
                        "content": message["content"]
                    }
                )
        except Exception as e:
            print(f"Error: {e}")