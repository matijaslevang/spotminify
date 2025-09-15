# # backend/post-content/create_single.py
import os
import json
import uuid
import datetime
import boto3

ddb = boto3.client("dynamodb")
T = os.environ["TABLE"]

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET,PUT,POST,DELETE",
    }

def _claims(event):
    rc = event.get("requestContext", {}) or {}
    claims = (rc.get("authorizer", {}) or {}).get("claims")
    if isinstance(claims, dict):
        return claims
    jwt = (rc.get("authorizer", {}) or {}).get("jwt", {})
    claims = jwt.get("claims")
    return claims if isinstance(claims, dict) else {}

def handler(event, _):
    try:
        # Admin guard
        role = _claims(event).get("custom:role", "")
        if role != "Admin":
            return {"statusCode": 403, "headers": cors_headers(),
                    "body": json.dumps({"error": "User does not have permission"})}

        b = json.loads(event.get("body") or "{}")
        now = datetime.datetime.utcnow().isoformat()
        cid = str(uuid.uuid4())

        title    = b.get("ContentName", "")
        artists  = b.get("SongArtists", []) or []
        genres   = b.get("SongGenres", []) or []
        # S3 reference polja se po potrebi vrate kad uključiš upload
        # song_ref = b.get("SongRef", "") or ""
        # song_img = b.get("SongImage", "") or ""
        album_id = b.get("albumId", "") or ""

        item = {
            "contentType": {"S": "SINGLE"},
            "contentName": {"S": title},
            "contentId":   {"S": cid},
            # "SongRef":     {"S": song_ref},
            # "SongImage":   {"S": song_img},
            "SongArtists": {"SS": artists} if artists else {"SS": []},
            "SongGenres":  {"SS": genres}  if genres  else {"SS": []},
            "SongRating":  {"N": "0"},
            "albumId":     {"S": album_id},
            "trackNo":     {"N": str(b.get("trackNo", 1))},
            "explicit":    {"BOOL": bool(b.get("explicit", False))},
            "createdAt":   {"S": now},
            "updatedAt":   {"S": now},
        }

        ddb.put_item(TableName=T, Item=item)

        if genres:
            req = {"RequestItems": {T: []}}
            for g in genres:
                req["RequestItems"][T].append({
                    "PutRequest": {"Item": {
                        "contentType": {"S": f"GENRE#{g}"},
                        "contentName": {"S": f"CONTENT#{cid}"},
                        "linkType":    {"S": "BY_GENRE"},
                        "targetType":  {"S": "SINGLE"},
                        "targetName":  {"S": title},
                        "createdAt":   {"S": now},
                    }}
                })
            ddb.batch_write_item(**req)

        return {"statusCode": 201, "headers": cors_headers(),
                "body": json.dumps({"contentId": cid})}

    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers(),
                "body": json.dumps({"error": str(e)})}
