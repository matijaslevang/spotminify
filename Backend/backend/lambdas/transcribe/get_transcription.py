import os
import boto3
import json

dynamodb = boto3.resource("dynamodb")
table_name = os.environ["TRANSCRIPTION_TABLE"]
table = dynamodb.Table(table_name)

def handler(event, context):
    single_id = event['queryStringParameters']['singleId']
    
    response = table.query(
        KeyConditionExpression='singleId = :singleId',
        ExpressionAttributeValues={
            ':singleId': single_id
        }
    )

    for item in response['Items']:
        transcript = item.get('transcription', '')
    
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': json.dumps({
            'transcription': transcript,
        })
    }

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,GET", 
        "Content-Type": "application/json" 
    }