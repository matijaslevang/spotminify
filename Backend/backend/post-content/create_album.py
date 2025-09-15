# import os
# import json
# import uuid
# import datetime
# import boto3

# ddb=boto3.client("dynamodb"); T=os.environ["TABLE"]

# def handler(event,_):
#     b=json.loads(event.get("body") or "{}")
#     now=datetime.datetime.utcnow().isoformat()
#     album_id=b.get("albumId") or f"alb-{uuid.uuid4()}" # --- slika u s3 baket i onda dobavi link za ovde

#     title   = b.get("ContentName","")
#     artists = b.get("AlbumArtists",[])
#     genres  = b.get("AlbumGenres",[])
#     img     = b.get("AlbumImage","") or ""

#     item = {
#       "contentType": {"S": "ALBUM"},
#       "contentName": {"S": title},

#       "albumId":     {"S": album_id},
#       "AlbumImage":  {"S": img},
#       "AlbumArtists":{"SS": artists} if artists else {"SS": []},
#       "AlbumGenres": {"SS": genres}  if genres  else {"SS": []},
#       "AlbumRating": {"N": "0"},
#       "createdAt":   {"S": now},
#       "updatedAt":   {"S": now}
#     }
#     if b.get("releaseYear"):
#         item["releaseYear"] = {"N": str(b["releaseYear"])}

#     ddb.put_item(TableName=T, Item=item)

#     if genres:
#         req={"RequestItems":{T:[]}}
#         for g in genres:
#             req["RequestItems"][T].append({
#               "PutRequest":{"Item":{
#                 "contentType":{"S": f"GENRE#{g}"},
#                 "contentName":{"S": f"CONTENT#{album_id}"},
#                 "linkType":   {"S":"BY_GENRE"},
#                 "targetType": {"S":"ALBUM"},
#                 "targetName": {"S": title},
#                 "createdAt":  {"S": now}
#             }}})
#         ddb.batch_write_item(**req)

#     return _ok(201, {"albumId": album_id})

# def _ok(code, body):
#     return {
#       "statusCode": code,
#       "headers": {
#         "Access-Control-Allow-Origin": "*",
#         "Access-Control-Allow-Headers": "*",
#         "Access-Control-Allow-Methods": "OPTIONS,POST"
#       },
#       "body": json.dumps(body)
#     }
# backend/post-content/create_album.py
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
    # REST API authorizer
    claims = (rc.get("authorizer", {}) or {}).get("claims")
    if isinstance(claims, dict):
        return claims
    # HTTP API JWT authorizer
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
        album_id = b.get("albumId") or f"alb-{uuid.uuid4()}"

        title   = b.get("ContentName", "")
        artists = b.get("AlbumArtists", []) or []
        genres  = b.get("AlbumGenres", []) or []
        img     = b.get("AlbumImage", "") or ""

        item = {
            "contentType": {"S": "ALBUM"},
            "contentName": {"S": title},
            "albumId":     {"S": album_id},
            "AlbumImage":  {"S": img},
            "AlbumArtists":{"SS": artists} if artists else {"SS": []},
            "AlbumGenres": {"SS": genres}  if genres  else {"SS": []},
            "AlbumRating": {"N": "0"},
            "createdAt":   {"S": now},
            "updatedAt":   {"S": now},
        }
        if b.get("releaseYear"):
            item["releaseYear"] = {"N": str(b["releaseYear"])}

        ddb.put_item(TableName=T, Item=item)

        if genres:
            req = {"RequestItems": {T: []}}
            for g in genres:
                req["RequestItems"][T].append({
                    "PutRequest": {"Item": {
                        "contentType":{"S": f"GENRE#{g}"},
                        "contentName":{"S": f"CONTENT#{album_id}"},
                        "linkType":   {"S":"BY_GENRE"},
                        "targetType": {"S":"ALBUM"},
                        "targetName": {"S": title},
                        "createdAt":  {"S": now},
                    }}
                })
            ddb.batch_write_item(**req)

        return {"statusCode": 201, "headers": cors_headers(),
                "body": json.dumps({"albumId": album_id})}

    except Exception as e:
        return {"statusCode": 500, "headers": cors_headers(),
                "body": json.dumps({"error": str(e)})}
