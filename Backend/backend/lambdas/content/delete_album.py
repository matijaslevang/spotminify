import os
import json
import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

ALBUM_TABLE_NAME = os.environ["ALBUM_TABLE"]
SINGLES_TABLE_NAME = os.environ["SINGLES_TABLE"]
GENRE_INDEX_TABLE_NAME = os.environ["GENRE_INDEX_TABLE"]
ARTIST_INDEX_TABLE_NAME = os.environ["ARTIST_INDEX_TABLE"]
FEED_CACHE_TABLE_NAME = os.environ["FEED_CACHE_TABLE"]

AUDIO_BUCKET = os.environ["AUDIO_BUCKET"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]

ALBUM_GSI_NAME = "AlbumIdIndexV2"
SINGLES_GSI_NAME = os.environ["SINGLES_GSI"] 
FEED_CACHE_GSI = os.environ.get("FEED_CACHE_GSI", "by-content-id")

albums_table = dynamodb.Table(ALBUM_TABLE_NAME)
singles_table = dynamodb.Table(SINGLES_TABLE_NAME)
genre_index_table = dynamodb.Table(GENRE_INDEX_TABLE_NAME)
artist_index_table = dynamodb.Table(ARTIST_INDEX_TABLE_NAME)
feed_cache_table = dynamodb.Table(FEED_CACHE_TABLE_NAME)


def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE"
    }

def delete_s3_object_from_url(key_url):
    if not key_url or not key_url.startswith("https://"): return None
    try:
        parts = key_url.replace("https://", "").split(".s3.amazonaws.com/")
        if len(parts) != 2: return None
        bucket_name, object_key = parts[0], parts[1]
        
        if bucket_name != AUDIO_BUCKET and bucket_name != IMAGES_BUCKET:
            print(f"Skipping deletion, bucket {bucket_name} not recognized.")
            return None
            
        print(f"Deleting s3://{bucket_name}/{object_key}")
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        return object_key
    except Exception as e:
        print(f"Failed to delete S3 object {key_url}: {str(e)}")
        return None

def delete_index_entries(content_key, genres, artist_ids):
    try:
        with genre_index_table.batch_writer() as batch:
            for genre_name in genres:
                batch.delete_item(Key={'genreName': genre_name, 'contentKey': content_key})
        print(f"Deleted entries for {content_key} from GenreIndex.")
    except Exception as e:
        print(f"Error deleting from GenreIndex for {content_key}: {e}")

    try:
        with artist_index_table.batch_writer() as batch:
            for artist_id in artist_ids:
                batch.delete_item(Key={'artistId': artist_id, 'contentKey': content_key})
        print(f"Deleted entries for {content_key} from ArtistIndex.")
    except Exception as e:
        print(f"Error deleting from ArtistIndex for {content_key}: {e}")

def delete_from_feed_cache(content_id):
    deleted_count = 0
    try:
        query_kwargs = {
            'IndexName': FEED_CACHE_GSI,
            'KeyConditionExpression': Key('contentId').eq(content_id),
            'ProjectionExpression': 'username, contentId' 
        }
        items_to_delete = []
        
        while True:
            response = feed_cache_table.query(**query_kwargs)
            items_to_delete.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        if not items_to_delete:
            print(f"No items found in FeedCache for contentId {content_id}")
            return

        print(f"Found {len(items_to_delete)} items in FeedCache to delete for contentId {content_id}")
        
        with feed_cache_table.batch_writer() as batch:
            for item in items_to_delete:
                batch.delete_item(Key={'username': item['username'], 'contentId': item['contentId']})
                deleted_count += 1
        print(f"Deleted {deleted_count} items from FeedCache for {content_id}")
        
    except Exception as e:
        print(f"Error deleting items from FeedCache for {content_id}: {str(e)}")

def handler(event, context):
    try:
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode": 403, "headers": cors(), "body": json.dumps({"error": "forbidden"})}

        path_params = event.get("pathParameters", {})
        album_id_to_delete = path_params.get("albumId")

        if not album_id_to_delete:
            return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "albumId is required in path"})}

        print(f"--- START: Deleting album {album_id_to_delete} (without touching ratings) ---")

        album_item = None
        artist_id_pk = None
        try:
            response = albums_table.query(
                IndexName=ALBUM_GSI_NAME,
                KeyConditionExpression=Key('albumId').eq(album_id_to_delete)
            )
            items = response.get('Items', [])
            if not items:
                print("Album not found via GSI.")
                return {"statusCode": 404, "headers": cors(), "body": json.dumps({"error": "Album not found"})}
            
            album_item = items[0]
            artist_id_pk = album_item.get('artistId') 
            if not artist_id_pk:
                return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Internal error: Missing primary key data for album"})}
            
            print(f"Album details fetched via GSI. artistId={artist_id_pk}")

        except Exception as e:
            print(f"Error finding album via GSI: {str(e)}")
            return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to find album details"})}

        deleted_s3_keys = []

        print(f"Finding associated songs for album {album_id_to_delete}...")
        songs_to_delete = []
        try:
            query_kwargs = {
                'IndexName': SINGLES_GSI_NAME,
                'KeyConditionExpression': Key('albumId').eq(album_id_to_delete)
            }
            while True:
                response = singles_table.query(**query_kwargs)
                songs_to_delete.extend(response.get('Items', []))
                if 'LastEvaluatedKey' not in response:
                    break
                query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            
            print(f"Found {len(songs_to_delete)} songs to delete.")

        except Exception as e:
            print(f"Error finding associated songs: {str(e)}")
            
        for song in songs_to_delete:
            try:
                song_id = song.get('singleId')
                song_artist_pk = song.get('artistId')
                
                if not song_id or not song_artist_pk:
                    print(f"Skipping song, missing keys: {song}")
                    continue

                print(f"Deleting song: {song_id} (artist: {song_artist_pk})")
                
                deleted_s3_keys.append(delete_s3_object_from_url(song.get('audioKey')))
                deleted_s3_keys.append(delete_s3_object_from_url(song.get('imageKey')))

                song_content_key = f"single-{song_id}"
                song_genres = list(song.get('genres', set()))
                song_artist_ids = list(song.get('artistIds', set()))
                delete_index_entries(song_content_key, song_genres, song_artist_ids)

                delete_from_feed_cache(song_id)
                
                singles_table.delete_item(
                    Key={'artistId': song_artist_pk, 'singleId': song_id}
                )
                print(f"Successfully deleted song {song_id} from Singles table.")

            except Exception as e:
                print(f"Error during deletion of song {song.get('singleId')}: {str(e)}")
        
        print(f"--- Finished deleting songs. Now deleting album {album_id_to_delete} ---")

        album_image_key_url = album_item.get('imageKey')
        deleted_s3_keys.append(delete_s3_object_from_url(album_image_key_url))

        album_content_key = f"album-{album_id_to_delete}" 
        album_genres = list(album_item.get('genres', set()))
        album_artist_ids = list(album_item.get('artistIds', set()))
        delete_index_entries(album_content_key, album_genres, album_artist_ids)

        delete_from_feed_cache(album_id_to_delete)

        try:
            albums_table.delete_item(
                Key={'artistId': artist_id_pk, 'albumId': album_id_to_delete}
            )
            print("Deleted item from Albums table.")
        except Exception as e:
             print(f"Error deleting from Albums table: {str(e)}")
             return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to delete album from main table"})}

        final_deleted_keys = [key for key in deleted_s3_keys if key]
        return {"statusCode": 200, "headers": cors(), "body": json.dumps({
            "message": f"Album {album_id_to_delete} and its {len(songs_to_delete)} songs deleted successfully",
            "deletedS3Keys": final_deleted_keys
            })}

    except Exception as e:
        print(f"Unhandled error: {str(e)}")
        return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": str(e)})}