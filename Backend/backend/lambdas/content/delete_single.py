import os
import json
import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

SINGLES_TABLE_NAME = os.environ["SINGLES_TABLE"]
GENRE_INDEX_TABLE_NAME = os.environ["GENRE_INDEX_TABLE"]
ARTIST_INDEX_TABLE_NAME = os.environ["ARTIST_INDEX_TABLE"]
AUDIO_BUCKET = os.environ["AUDIO_BUCKET"]
IMAGES_BUCKET = os.environ["IMAGES_BUCKET"]
SINGLES_GSI_BY_SINGLE_ID = "SingleIdIndexV2"
FEED_CACHE_TABLE_NAME = os.environ["FEED_CACHE_TABLE"]
FEED_CACHE_GSI = "by-content-id"

feed_cache_table = dynamodb.Table(FEED_CACHE_TABLE_NAME)

singles_table = dynamodb.Table(SINGLES_TABLE_NAME)
genre_index_table = dynamodb.Table(GENRE_INDEX_TABLE_NAME)
artist_index_table = dynamodb.Table(ARTIST_INDEX_TABLE_NAME)

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
        if bucket_name != AUDIO_BUCKET and bucket_name != IMAGES_BUCKET: return None
        print(f"Deleting s3://{bucket_name}/{object_key}")
        s3.delete_object(Bucket=bucket_name, Key=object_key)
        return object_key
    except Exception as e:
        print(f"Failed to delete S3 object {key_url}: {str(e)}")
        return None

def delete_index_entries(content_key, genres, artist_ids):
    try:
        with genre_index_table.batch_writer() as batch:
            for genre_name in genres: batch.delete_item(Key={'genreName': genre_name, 'contentKey': content_key})
        print(f"Deleted entries for {content_key} from GenreIndex.")
    except Exception as e: print(f"Error deleting from GenreIndex for {content_key}: {e}")
    try:
        with artist_index_table.batch_writer() as batch:
            for artist_id in artist_ids: batch.delete_item(Key={'artistId': artist_id, 'contentKey': content_key})
        print(f"Deleted entries for {content_key} from ArtistIndex.")
    except Exception as e: print(f"Error deleting from ArtistIndex for {content_key}: {e}")

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
            if 'LastEvaluatedKey' not in response: break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        if not items_to_delete:
            print(f"No items found in FeedCache for contentId {content_id}")
            return

        print(f"Found {len(items_to_delete)} items in FeedCache to delete for contentId {content_id}")
        with feed_cache_table.batch_writer() as batch:
            for item in items_to_delete:
                batch.delete_item(Key={'username': item['username'], 'contentId': item['contentId']})
                deleted_count += 1
        print(f"Deleted {deleted_count} items from FeedCache")
    except Exception as e:
        print(f"Error deleting items from FeedCache for {content_id}: {str(e)}")

def handler(event, context):
    try:
        claims = (event.get("requestContext", {}) or {}).get("authorizer", {}).get("claims", {}) or {}
        if claims.get("custom:role") != "Admin":
            return {"statusCode": 403, "headers": cors(), "body": json.dumps({"error": "forbidden"})}

        path_params = event.get("pathParameters", {})
        single_id_to_delete = path_params.get("singleId")

        if not single_id_to_delete:
            return {"statusCode": 400, "headers": cors(), "body": json.dumps({"error": "singleId is required in path"})}

        print(f"Attempting to delete single: singleId={single_id_to_delete}")

        single_item = None
        artist_id_pk = None
        try:
            response = singles_table.query(
                IndexName=SINGLES_GSI_BY_SINGLE_ID,
                KeyConditionExpression=Key('singleId').eq(single_id_to_delete)
            )
            items = response.get('Items', [])
            if not items:
                 print("Single not found via GSI.")
                 return {"statusCode": 404, "headers": cors(), "body": json.dumps({"error": "Single not found"})}
            single_item = items[0]
            artist_id_pk = single_item.get('artistId')
            if not artist_id_pk:
                 return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Internal error: Missing primary key data"})}

            print(f"Single details fetched via GSI. artistId={artist_id_pk}")
            audio_key_url = single_item.get('audioKey')
            image_key_url = single_item.get('imageKey')
            single_genres = list(single_item.get('genres', set()))
            single_artist_ids = list(single_item.get('artistIds', set()))

        except Exception as e:
            print(f"Error finding single via GSI: {str(e)}")
            return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to find single details"})}

        deleted_s3_keys = []
        deleted_s3_keys.append(delete_s3_object_from_url(audio_key_url))
        if image_key_url:
            deleted_s3_keys.append(delete_s3_object_from_url(image_key_url))

        content_key = f"single-{single_id_to_delete}"
        delete_index_entries(content_key, single_genres, single_artist_ids)

        delete_from_feed_cache(single_id_to_delete)
        
        try:
            singles_table.delete_item(
                Key={'artistId': artist_id_pk, 'singleId': single_id_to_delete}
            )
            print("Deleted item from Singles table.")
        except Exception as e:
             print(f"Error deleting from Singles table: {str(e)}")
             return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": "Failed to delete single from main table"})}

        final_deleted_keys = [key for key in deleted_s3_keys if key]
        return {"statusCode": 200, "headers": cors(), "body": json.dumps({
            "message": "Single deleted successfully",
            "deletedS3Keys": final_deleted_keys
            })}

    except Exception as e:
        print(f"Unhandled error: {str(e)}")
        return {"statusCode": 500, "headers": cors(), "body": json.dumps({"error": str(e)})}