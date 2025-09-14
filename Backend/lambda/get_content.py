import json
import boto3

dynamodb = boto3.client('dynamodb')
s3_client = boto3.client('s3')

def get_content(event, context):

    table_name = 'content'
    content_name = event.get('contentName')
    content_type = event.get('contentType')

    if not content_type and not content_name:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Bad request'})
        }

    try:
        response = dynamodb.get_item(
            TableName=table_name,
            Key={
                'contentType': {'S': content_type},
                'contentName': {'S': content_name}
            }
        )

        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Item not found'})
            }
        
        dynamo_data = {k: list(v.values())[0] for k, v in item.items()}
    
        return {
            'statusCode': 200,
            'body': json.dumps({'data': dynamo_data})
        }
            
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }