import json
import boto3
import os
import logging
import base64

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cliente de SQS
sqs = boto3.client('sqs')

# URL de la cola SQS
QUEUE_URL = os.environ['QUEUE_URL']

def handler(event, context):
    try:
        # Verificar si el evento proviene de API Gateway y si el cuerpo está codificado en base64
        if 'body' in event:
            if event.get('isBase64Encoded', False):
                body = base64.b64decode(event['body']).decode('utf-8')
                body = json.loads(body)
            else:
                body = json.loads(event['body'])
        else:
            # Procesar como evento de SQS
            record = event['Records'][0]
            body = json.loads(record['body'])

        logger.info(f"Procesando mensaje con body: {body}")

        # Enviar el payload a la cola SQS
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(body)
        )
        logger.info(f"Mensaje enviado a SQS: {response}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Payloads procesados y enviados a la cola SQS'})
        }

    except Exception as e:
        logger.error(f"Error procesando mensajes: {str(e)}")
        logger.error(f"Evento completo: {json.dumps(event)}")  # Log the full event for debugging
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error procesando payloads'})
        }