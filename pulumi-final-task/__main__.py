import json
import pulumi
import pulumi_aws as aws
import pulumi_aws_apigateway as apigateway

# IAM role for Lambda
role = aws.iam.Role(
    "role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com",
                    },
                }
            ],
        }
    ),
    managed_policy_arns=[
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
    ],
)

# SQS Queue
queue = aws.sqs.Queue("queue")

# Define an inline policy to allow access to SQS
role_policy_sqs = aws.iam.RolePolicy(
    "lambdaSQSSendPolicy",
    role=role.id,
    policy=pulumi.Output.all(queue.arn).apply(lambda queue_arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sqs:SendMessage"
                ],
                "Resource": queue_arn
            }
        ]
    }))
)

# Define an inline policy for VPC creation
role_policy_vpc = aws.iam.RolePolicy(
    "lambdaVPCPolicy",
    role=role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:CreateVpc",
                    "ec2:CreateSubnet",
                    "ec2:CreateRouteTable",
                    "ec2:CreateInternetGateway",
                    "ec2:AttachInternetGateway",
                    "ec2:AssociateRouteTable",
                    "ec2:CreateRoute",
                    "ec2:ModifyVpcAttribute",
                    "ec2:DeleteVpc",
                    "ec2:DeleteSubnet",
                    "ec2:DeleteRouteTable",
                    "ec2:DetachInternetGateway",
                    "ec2:DeleteInternetGateway",
                    "ec2:DisassociateRouteTable",
                    "ec2:CreateTags",
                    "ec2:DescribeVpcs"
                ],
                "Resource": "*"
            }
        ]
    })
)

# First Lambda function to handle the payload and send it to SQS
handler = aws.lambda_.Function(
    "handler",
    runtime="python3.9",
    handler="handler.handler",
    role=role.arn,
    code=pulumi.AssetArchive({
        '.': pulumi.FileArchive('./function'),  # Your Lambda function code
    }),
    environment={
        'variables': {
            'QUEUE_URL': queue.url,
        },
    },
)

# Lambda function to process the SQS messages and create a VPC
vpc_creator = aws.lambda_.Function(
    "vpcCreator",
    runtime="python3.9",
    handler="vpc_creator.lambda_handler",
    role=role.arn,
    code=pulumi.AssetArchive({
        '.': pulumi.FileArchive('./vpc_creator'),  # Lambda for VPC creation
    }),
    environment={
        'variables': {
            'QUEUE_URL': queue.url,
        },
    },
    timeout=30  # Set timeout to 30 seconds
)

# Grant the SQS queue permission to trigger the Lambda function
event_source_mapping = aws.lambda_.EventSourceMapping(
    "eventSourceMapping",
    event_source_arn=queue.arn,
    function_name=vpc_creator.arn,
    batch_size=1,  # Process one message at a time
)

# API Gateway to handle HTTP requests and send payloads to Lambda
api = apigateway.RestAPI(
    "api",
    routes=[
        apigateway.RouteArgs(
            path="/",
            method=apigateway.Method.POST,
            event_handler=handler,
        )
    ],
    # cors=True,  # Habilitar CORS
)

# Obtener la identidad del usuario
identity = aws.get_caller_identity()
account_id = identity.account_id

# Construir el ARN de la API Gateway
api_arn = pulumi.Output.concat(
    "arn:aws:execute-api:",
    aws.config.region,
    ":",
    account_id,
    ":",
    api.api.id,
    "/*/*"
)

# Definir los permisos para la Lambda
aws.lambda_.Permission("api-permission",
    action="lambda:InvokeFunction",
    function=handler.arn,
    principal="apigateway.amazonaws.com",
    source_arn=api_arn)

# Export the API URL
pulumi.export("url", api.url)