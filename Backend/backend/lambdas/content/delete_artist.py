import os
import json
import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

ARTISTS_TABLE_NAME = os.environ["ARTISTS_TABLE"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"] 
GENRE_INDEX_TABLE_NAME = os.environ["GENRE_INDEX_TABLE"]
ARTIST_INDEX_TABLE_NAME = os.environ["ARTIST_INDEX_TABLE"]
FEED_CACHE_TABLE_NAME = os.environ["FEED_CACHE_TABLE"]
SUBSCRIPTIONS_TABLE_NAME = os.environ["SUBSCRIPTIONS_TABLE"]
FEED_CACHE_GSI = os.environ.get("FEED_CACHE_GSI", "by-content-id")
SUBSCRIPTIONS_GSI_NAME = os.environ.get("SUBSCRIPTIONS_GSI_NAME", "by-target-id")

artists_table = dynamodb.Table(ARTISTS_TABLE_NAME)
genre_index_table = dynamodb.Table(GENRE_INDEX_TABLE_NAME)
artist_index_table = dynamodb.Table(ARTIST_INDEX_TABLE_NAME)
feed_cache_table = dynamodb.Table(FEED_CACHE_TABLE_NAME)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)

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
        
        if bucket_name != IMAGES_BUCKET:
            print(f"Skipping deletion, bucket {bucket_name} not recognized as {IMAGES_BUCKET}.")
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

def delete_subscriptions(target_id):
    """Pronalazi i briše sve pretplate za dati targetId (artistId)."""
    deleted_count = 0
    try:
        query_kwargs = {
            'IndexName': SUBSCRIPTIONS_GSI_NAME,
            'KeyConditionExpression': Key('targetId').eq(target_id),
            'ProjectionExpression': 'username, targetId'
        }
        items_to_delete = []
        
        while True:
            response = subscriptions_table.query(**query_kwargs)
            items_to_delete.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        if not items_to_delete:
            print(f"No subscriptions found for targetId {target_id}")
            return

        print(f"Found {len(items_to_delete)} subscriptions to delete for targetId {target_id}")
        
        with subscriptions_table.batch_writer() as batch:
            for item in items_to_delete:
                batch.delete_item(Key={'username': item['username'], 'targetId': item['targetId']})
                deleted_count += 1
        print(f"Deleted {deleted_count} subscriptions for {target_id}")
        
    except Exception as e:
        print(f"Error deleting subscriptions for {target_id}: {str(e)}")


def handler(event, context):
    try:
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode": 403, "headers": cors(), "body": json.dumps({"error": "forbidden"})}

        path_params = event.get("pathParameters", {})
        artist_id_to_delete = path_params.get("artistId")

        if not artist_id_to_delete:
            return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "artistId is required in path"})}

        print(f"--- START: Deleting artist {artist_id_to_delete} (no cascade) ---")

        artist_item = None
        try:
            response = artists_table.get_item(
                Key={'artistId': artist_id_to_delete}
            )
            artist_item = response.get('Item')
            if not artist_item:
                print("Artist not found.")
                return {"statusCode": 404, "headers": cors(), "body": json.dumps({"error": "Artist not found"})}
            
            print(f"Artist details fetched: {artist_id_to_delete}")

        except Exception as e:
            print(f"Error finding artist: {str(e)}")
            return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to find artist details"})}

        deleted_s3_keys = []

        image_key_url = artist_item.get('imageKey')
        deleted_s3_keys.append(delete_s3_object_from_url(image_key_url))

        content_key = f"artist-{artist_id_to_delete}" 
        genres = list(artist_item.get('genres', set()))
        artist_ids = [artist_id_to_delete] 
        delete_index_entries(content_key, genres, artist_ids)

        delete_from_feed_cache(artist_id_to_delete)
        
        print(f"Deleting subscriptions for artist {artist_id_to_delete}")
        delete_subscriptions(artist_id_to_delete)
        
        try:
            artists_table.delete_item(
                Key={'artistId': artist_id_to_delete}
            )
            print("Deleted item from Artists table.")
        except Exception as e:
             print(f"Error deleting from Artists table: {str(e)}")
             return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to delete artist from main table"})}

        # 9. Gotovo
        final_deleted_keys = [key for key in deleted_s3_keys if key]
        return {"statusCode": 200, "headers": cors(), "body": json.dumps({
            "message": f"Artist {artist_id_to_delete} deleted successfully (songs/albums retained).",
            "deletedS3Keys": final_deleted_keys
            })}

    except Exception as e:
        print(f"Unhandled error: {str(e)}")
        return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": str(e)})}