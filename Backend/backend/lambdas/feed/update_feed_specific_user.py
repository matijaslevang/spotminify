import os
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table_score_cache = dynamodb.Table(os.environ["SCORE_TABLE_NAME"])
table_feed_cache = dynamodb.Table(os.environ["FEED_TABLE_NAME"])
table_artists = dynamodb.Table(os.environ["ARTIST_TABLE_NAME"])
table_singles = dynamodb.Table(os.environ["SINGLE_TABLE_NAME"])
table_albums = dynamodb.Table(os.environ["ALBUM_TABLE_NAME"])

def handler(event, context):
    for record in event['Records']:
        body = record['body']

        try:
            message = json.loads(body)

            # UPDATE A USERNAME'S FEED FROM SCRATCH

            # 1. get username
            username = message["username"]

            # 2. get user's score
            try:
                response = table_score_cache.get_item(
                    Key={"username": username}
                )
                score_entry = response.get("Item")

                user_scores: dict = score_entry.get("scores", {})

            except Exception as e:
                print(f"Failed to fetch score for {username}: {e}")
            
            # 3. get all content
            # get all artists
            response_artists = table_artists.scan()
            all_artists = response_artists['Items']
            print(all_artists)
            # get all songs
            response_songs = table_singles.scan()
            all_songs = response_songs['Items']
            print(all_songs)
            # get all albums
            response_album = table_albums.scan()
            all_albums = response_album['Items']
            print(all_albums)

            artists_scored = []
            songs_scored = []
            albums_scored = []
            # 4. assign scores to everything
            for artist in all_artists:
                score = 0
                for genre in artist['genres']:
                    score += user_scores.get(genre, 0)
                songs_scored.append([artist, score])

            for song in all_songs:
                score = 0
                for genre in song['genres']:
                    score += user_scores.get(genre, 0)
                artists_scored.append([song, score])

            for album in all_albums:
                score = 0
                for genre in album['genres']:
                    score += user_scores.get(genre, 0)
                albums_scored.append([album, score])

            # 5. save only the top X artists, top X songs, top X albums
            
            # sort the scored lists by score

            artists_scored.sort(key=lambda x: x[1], reverse=True)
            songs_scored.sort(key=lambda x: x[1], reverse=True)
            albums_scored.sort(key=lambda x: x[1], reverse=True)

            element_number = 5
            artists_scored = artists_scored[:element_number]
            songs_scored = songs_scored[:element_number]
            albums_scored = albums_scored[:element_number]

            combined_list = artists_scored + songs_scored + albums_scored

            # delete existing items from feed cache
            response = table_feed_cache.query(
                KeyConditionExpression="username = :username",
                ExpressionAttributeValues={":username": username}
            )

            print(response['Items'])
            with table_feed_cache.batch_writer() as batch:
                for item in response['Items']:
                    batch.delete_item(
                        Key={"username": item["username"], "contentId": item["contentId"]}
                    )

            # add new items to feed cache
            print(combined_list)
            with table_feed_cache.batch_writer() as batch:
                for element in combined_list:
                    print(element)
                    pk = username
                    if 'biography' in element[0]:
                        sk = element[0]['artistId']
                        content_type = "artist"
                    elif 'coverKey' in element[0]:
                        sk = element[0]['albumId']
                        content_type = "album"
                    elif 'singleId' in element[0]:
                        sk = element[0]['singleId']
                        content_type = "single"
                    else:
                        raise ValueError("Element does not contain valid id (artistId, albumId, or singleId)")
                    
                    print(sk)
                    batch.put_item(
                        Item={
                            "username": pk,
                            "contentId": sk,
                            "contentType": content_type,
                            "content": element[0],
                            "score": element[1],
                        }
                    )
                
        except Exception as e:
            print(f"Error: {e}")