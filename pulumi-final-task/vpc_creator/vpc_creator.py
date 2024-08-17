import json
import boto3

def create_vpc(project_name, cidr_block, num_public_subnets, num_private_subnets, region):
    ec2 = boto3.resource('ec2', region_name=region)

    # Create a new VPC
    vpc = ec2.create_vpc(CidrBlock=cidr_block)
    vpc.create_tags(Tags=[{"Key": "Name", "Value": f"{project_name}-vpc"}])
    vpc.wait_until_available()

    # Create an internet gateway
    igw = ec2.create_internet_gateway()
    vpc.attach_internet_gateway(InternetGatewayId=igw.id)
    igw.create_tags(Tags=[{"Key": "Name", "Value": f"{project_name}-igw"}])

    # Create subnets
    base_cidr = cidr_block.split('/')[0]  # Esto da '10.0.0.0'
    base_parts = base_cidr.split('.')  # Esto da ['10', '0', '0', '0']
    public_subnets = []
    private_subnets = []

    for i in range(num_public_subnets):
        # Genera un nuevo bloque CIDR para cada subred pública incrementando el tercer octeto
        subnet_cidr = f"{base_parts[0]}.{base_parts[1]}.{int(base_parts[2]) + i}.0/24"
        subnet = vpc.create_subnet(CidrBlock=subnet_cidr)
        subnet.create_tags(Tags=[{"Key": "Name", "Value": f"{project_name}-public-subnet-{i}"}])
        public_subnets.append(subnet.id)

    for i in range(num_private_subnets):
        # Genera un nuevo bloque CIDR para cada subred privada incrementando el tercer octeto
        subnet_cidr = f"{base_parts[0]}.{base_parts[1]}.{int(base_parts[2]) + num_public_subnets + i}.0/24"
        subnet = vpc.create_subnet(CidrBlock=subnet_cidr)
        subnet.create_tags(Tags=[{"Key": "Name", "Value": f"{project_name}-private-subnet-{i}"}])
        private_subnets.append(subnet.id)

    # Create route tables and associate with subnets
    route_table = vpc.create_route_table()
    route_table.create_tags(Tags=[{"Key": "Name", "Value": f"{project_name}-route-table"}])
    route_table.create_route(DestinationCidrBlock='0.0.0.0/0', GatewayId=igw.id)

    for subnet_id in public_subnets:
        route_table.associate_with_subnet(SubnetId=subnet_id)

    return {
        "vpc_id": vpc.id,
        "public_subnet_ids": public_subnets,
        "private_subnet_ids": private_subnets
    }

def lambda_handler(event, context):
    # Verificar si 'Records' está en el evento
    if 'Records' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'No Records key found in event'})
        }

    for record in event['Records']:
        payload = json.loads(record['body'])

        project_name = payload.get("ProjectName")
        cidr_block = payload.get("CIDR")
        num_public_subnets = payload.get("NumPublicSubnets", 1)
        num_private_subnets = payload.get("NumPrivateSubnets", 1)
        region = payload.get("awsRegion", "us-east-1")

        # Call the function to create the VPC
        vpc_info = create_vpc(project_name, cidr_block, num_public_subnets, num_private_subnets, region)

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'VPC creation triggered successfully', 'vpc_info': vpc_info})
    }