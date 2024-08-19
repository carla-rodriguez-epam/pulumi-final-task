import json
import boto3
import os
import logging
import base64

# logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SQS Client
sqs = boto3.client('sqs')

# SQS URL Queue
QUEUE_URL = os.environ['QUEUE_URL']

def handler(event, context):
    try:
        # Check if the event comes from API Gateway and if the body is base64 encoded
        if 'body' in event:
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(event['body']).decode('utf-8')
                body = json.loads(body)
            else:
                body = json.loads(event['body'])
        else:
            # Process as SQS event
            record = event['Records'][0]
            body = json.loads(record['body'])

        logger.info(f"Processing message with body: {body}")

        # Send the payload to the SQS queue
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(body)
        )
        logger.info(f"Message sent to SQS: {response}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Payloads processed and sent to the SQS queue'})
        }

    except Exception as e:
        logger.error(f"Error processing messages: {str(e)}")
        logger.error(f"Complete event: {json.dumps(event)}")  # Log the full event for debugging
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error processing payloads'})
        }