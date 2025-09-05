import pulumi
import pulumi_aws as aws
import json

# Configuration
config = pulumi.Config()
project_name = config.get("project-name") or "personal-news"
environment = config.get("environment") or "prod"
schedule_time = config.get("schedule-time") or "cron(0 8 * * ? *)"

# Get current AWS account info
current = aws.get_caller_identity()
account_id = current.account_id
region = aws.get_region().name

# S3 Bucket for preferences storage
preferences_bucket = aws.s3.Bucket(
    "preferences-bucket",
    bucket=f"{project_name}-preferences-{environment}-{account_id}"
)

# S3 Bucket Versioning
bucket_versioning = aws.s3.BucketVersioningV2(
    "preferences-bucket-versioning",
    bucket=preferences_bucket.id,
    versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(
        status="Enabled"
    )
)

# S3 Bucket Encryption
bucket_encryption = aws.s3.BucketServerSideEncryptionConfigurationV2(
    "preferences-bucket-encryption",
    bucket=preferences_bucket.id,
    rules=[aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
        apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
            sse_algorithm="AES256"
        )
    )]
)

# S3 Bucket Public Access Block
bucket_pab = aws.s3.BucketPublicAccessBlock(
    "preferences-bucket-pab",
    bucket=preferences_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True
)

# S3 Bucket Lifecycle Configuration
bucket_lifecycle = aws.s3.BucketLifecycleConfigurationV2(
    "preferences-bucket-lifecycle",
    bucket=preferences_bucket.id,
    rules=[aws.s3.BucketLifecycleConfigurationV2RuleArgs(
        id="backup-retention",
        status="Enabled",
        filter=aws.s3.BucketLifecycleConfigurationV2RuleFilterArgs(
            prefix="backups/"
        ),
        expiration=aws.s3.BucketLifecycleConfigurationV2RuleExpirationArgs(
            days=90
        )
    )]
)

# VPC and Networking
vpc = aws.ec2.Vpc(
    "vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={"Name": f"{project_name}-vpc-{environment}"}
)

# Internet Gateway
igw = aws.ec2.InternetGateway(
    "igw",
    vpc_id=vpc.id,
    tags={"Name": f"{project_name}-igw-{environment}"}
)

# Public Subnets
public_subnet_1 = aws.ec2.Subnet(
    "public-subnet-1",
    vpc_id=vpc.id,
    availability_zone=aws.get_availability_zones().names[0],
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    tags={"Name": f"{project_name}-public-subnet-1-{environment}"}
)

public_subnet_2 = aws.ec2.Subnet(
    "public-subnet-2",
    vpc_id=vpc.id,
    availability_zone=aws.get_availability_zones().names[1],
    cidr_block="10.0.2.0/24",
    map_public_ip_on_launch=True,
    tags={"Name": f"{project_name}-public-subnet-2-{environment}"}
)

# Private subnets removed for cost optimization

# NAT Gateway removed for cost optimization

# Route Tables
public_route_table = aws.ec2.RouteTable(
    "public-route-table",
    vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(
        cidr_block="0.0.0.0/0",
        gateway_id=igw.id
    )],
    tags={"Name": f"{project_name}-public-rt-{environment}"}
)

# Private route table removed for cost optimization

# Route Table Associations
public_rta_1 = aws.ec2.RouteTableAssociation(
    "public-rta-1",
    route_table_id=public_route_table.id,
    subnet_id=public_subnet_1.id
)

public_rta_2 = aws.ec2.RouteTableAssociation(
    "public-rta-2",
    route_table_id=public_route_table.id,
    subnet_id=public_subnet_2.id
)

# Private route table associations removed for cost optimization

# Security Group
security_group = aws.ec2.SecurityGroup(
    "security-group",
    name=f"{project_name}-sg-{environment}",
    description="Security group for Personal News Digest",
    vpc_id=vpc.id,
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"]
    )]
)

# Secrets Manager for API keys
newsapi_secret = aws.secretsmanager.Secret(
    "newsapi-secret",
    name=f"{project_name}/newsapi-key-{environment}",
    description="NewsAPI key for Personal News Digest"
)

aws.secretsmanager.SecretVersion(
    "newsapi-secret-version",
    secret_id=newsapi_secret.id,
    secret_string="PLACEHOLDER_NEWSAPI_KEY"
)

openai_secret = aws.secretsmanager.Secret(
    "openai-secret",
    name=f"{project_name}/openai-key-{environment}",
    description="OpenAI API key for Personal News Digest"
)

aws.secretsmanager.SecretVersion(
    "openai-secret-version",
    secret_id=openai_secret.id,
    secret_string="PLACEHOLDER_OPENAI_KEY"
)

anthropic_secret = aws.secretsmanager.Secret(
    "anthropic-secret",
    name=f"{project_name}/anthropic-key-{environment}",
    description="Anthropic API key for Personal News Digest"
)

aws.secretsmanager.SecretVersion(
    "anthropic-secret-version",
    secret_id=anthropic_secret.id,
    secret_string="PLACEHOLDER_ANTHROPIC_KEY"
)

email_password_secret = aws.secretsmanager.Secret(
    "email-password-secret",
    name=f"{project_name}/email-password-{environment}",
    description="Email password for Personal News Digest"
)

aws.secretsmanager.SecretVersion(
    "email-password-secret-version",
    secret_id=email_password_secret.id,
    secret_string="PLACEHOLDER_EMAIL_PASSWORD"
)

# CloudWatch Log Group
log_group = aws.cloudwatch.LogGroup(
    "log-group",
    name=f"/aws/ecs/{project_name}-{environment}",
    retention_in_days=30
)

# IAM Role for Task Execution
task_execution_role = aws.iam.Role(
    "task-execution-role",
    name=f"{project_name}-task-execution-{environment}",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    })
)

# Attach AWS managed policy
aws.iam.RolePolicyAttachment(
    "task-execution-role-policy",
    role=task_execution_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
)

# Custom policy for Secrets Manager access
secrets_policy = aws.iam.RolePolicy(
    "secrets-policy",
    role=task_execution_role.id,
    policy=pulumi.Output.all(
        newsapi_secret.arn,
        openai_secret.arn,
        anthropic_secret.arn,
        email_password_secret.arn
    ).apply(lambda arns: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": arns
        }]
    }))
)

# IAM Role for Task (application permissions)
task_role = aws.iam.Role(
    "task-role",
    name=f"{project_name}-task-{environment}",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    })
)

# S3 policy for task role
s3_policy = aws.iam.RolePolicy(
    "s3-policy",
    role=task_role.id,
    policy=preferences_bucket.bucket.apply(lambda bucket_name: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{bucket_name}"
            }
        ]
    }))
)

# ECR Repository
ecr_repository = aws.ecr.Repository(
    "ecr-repository",
    name=f"{project_name}-{environment}",
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push=True
    )
)

# ECR Lifecycle Policy (separate resource)
ecr_lifecycle_policy = aws.ecr.LifecyclePolicy(
    "ecr-lifecycle-policy",
    repository=ecr_repository.name,
    policy=json.dumps({
        "rules": [{
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 10
            },
            "action": {
                "type": "expire"
            }
        }]
    })
)

# ECS Cluster
ecs_cluster = aws.ecs.Cluster(
    "ecs-cluster",
    name=f"{project_name}-{environment}"
)

# ECS Cluster Capacity Providers
cluster_capacity_providers = aws.ecs.ClusterCapacityProviders(
    "cluster-capacity-providers",
    cluster_name=ecs_cluster.name,
    capacity_providers=["FARGATE"],
    default_capacity_provider_strategies=[aws.ecs.ClusterCapacityProvidersDefaultCapacityProviderStrategyArgs(
        capacity_provider="FARGATE",
        weight=1
    )]
)

# ECS Task Definition (will be updated with actual image later)
task_definition = aws.ecs.TaskDefinition(
    "task-definition",
    family=f"{project_name}-{environment}",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    cpu="256",
    memory="512",
    execution_role_arn=task_execution_role.arn,
    task_role_arn=task_role.arn,
    container_definitions=pulumi.Output.all(
        ecr_repository.repository_url,
        log_group.name,
        preferences_bucket.bucket,
        newsapi_secret.arn,
        openai_secret.arn,
        anthropic_secret.arn,
        email_password_secret.arn
    ).apply(lambda args: json.dumps([{
        "name": f"{project_name}-container",
        "image": f"{args[0]}:latest",
        "essential": True,
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": args[1],
                "awslogs-region": region,
                "awslogs-stream-prefix": "ecs"
            }
        },
        "environment": [
            {"name": "AWS_USE_S3", "value": "true"},
            {"name": "S3_BUCKET_NAME", "value": args[2]},
            {"name": "AWS_DEFAULT_REGION", "value": region}
        ],
        "secrets": [
            {"name": "NEWSAPI_KEY", "valueFrom": args[3]},
            {"name": "OPENAI_API_KEY", "valueFrom": args[4]},
            {"name": "ANTHROPIC_API_KEY", "valueFrom": args[5]},
            {"name": "EMAIL_PASSWORD", "valueFrom": args[6]}
        ]
    }]))
)

# IAM Role for EventBridge
eventbridge_role = aws.iam.Role(
    "eventbridge-role",
    name=f"{project_name}-eventbridge-{environment}",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "events.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    })
)

# EventBridge policy
eventbridge_policy = aws.iam.RolePolicy(
    "eventbridge-policy",
    role=eventbridge_role.id,
    policy=pulumi.Output.all(
        task_definition.arn,
        task_execution_role.arn,
        task_role.arn
    ).apply(lambda arns: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["ecs:RunTask"],
                "Resource": arns[0]
            },
            {
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": [arns[1], arns[2]]
            }
        ]
    }))
)

# EventBridge Rule for Scheduling
schedule_rule = aws.cloudwatch.EventRule(
    "schedule-rule",
    name=f"{project_name}-schedule-{environment}",
    description="Daily trigger for Personal News Digest",
    schedule_expression=schedule_time,
    state="ENABLED"
)

# EventBridge Target
schedule_target = aws.cloudwatch.EventTarget(
    "schedule-target",
    rule=schedule_rule.name,
    arn=ecs_cluster.arn,
    role_arn=eventbridge_role.arn,
    ecs_target=aws.cloudwatch.EventTargetEcsTargetArgs(
        task_definition_arn=task_definition.arn,
        launch_type="FARGATE",
        network_configuration=aws.cloudwatch.EventTargetEcsTargetNetworkConfigurationArgs(
            security_groups=[security_group.id],
            subnets=[public_subnet_1.id, public_subnet_2.id],
            assign_public_ip=True
        )
    )
)

# Exports
pulumi.export("s3_bucket_name", preferences_bucket.bucket)
pulumi.export("ecr_repository_uri", ecr_repository.repository_url)
pulumi.export("ecs_cluster_name", ecs_cluster.name)
pulumi.export("task_definition_arn", task_definition.arn)
pulumi.export("vpc_id", vpc.id)
pulumi.export("security_group_id", security_group.id)