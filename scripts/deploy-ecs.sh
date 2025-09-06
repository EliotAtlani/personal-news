#!/bin/bash

# Manual ECS Deployment Script for Personal News
# Usage: ./scripts/deploy-ecs.sh [IMAGE_TAG]
# If no IMAGE_TAG provided, will use 'latest'

set -e

# Configuration
AWS_REGION="us-east-1"
ECS_CLUSTER="personal-news-prod"
ECS_SERVICE="personal-news-prod" 
ECS_TASK_DEFINITION="personal-news-prod"
CONTAINER_NAME="personal-news-prod"
ECR_REPOSITORY="personal-news-prod"

# Get AWS Account ID dynamically
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not determine AWS Account ID. Make sure you're authenticated with AWS CLI."
    exit 1
fi

echo "🚀 Personal News ECS Deployment"
echo "================================"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Cluster: $ECS_CLUSTER"
echo "Service: $ECS_SERVICE"

# Determine image tag
IMAGE_TAG="${1:-latest}"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "Image: $ECR_URI"
echo ""

# Verify image exists in ECR
echo "🔍 Verifying image exists in ECR..."
if ! aws ecr describe-images \
    --repository-name "$ECR_REPOSITORY" \
    --image-ids imageTag="$IMAGE_TAG" \
    --region "$AWS_REGION" \
    --output text &>/dev/null; then
    echo "❌ Error: Image with tag '$IMAGE_TAG' not found in ECR repository '$ECR_REPOSITORY'"
    echo ""
    echo "Available images:"
    aws ecr list-images \
        --repository-name "$ECR_REPOSITORY" \
        --query 'imageIds[*].imageTag' \
        --output table
    exit 1
fi
echo "✅ Image found in ECR"

# Download current task definition
echo "📥 Downloading current task definition..."
aws ecs describe-task-definition \
    --task-definition "$ECS_TASK_DEFINITION" \
    --query taskDefinition \
    --output json > task-definition.json

# Clean task definition (remove read-only fields)
echo "🧹 Cleaning task definition..."
jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
    task-definition.json > task-definition-clean.json

# Update image in task definition
echo "🔄 Updating container image..."
jq --arg new_image "$ECR_URI" \
    '(.containerDefinitions[] | select(.name == "'$CONTAINER_NAME'") | .image) = $new_image' \
    task-definition-clean.json > task-definition-updated.json

# Register new task definition
echo "📝 Registering new task definition..."
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition-updated.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

echo "✅ New task definition registered: $NEW_TASK_DEF_ARN"

# Update ECS service
echo "🔄 Updating ECS service..."
aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --task-definition "$NEW_TASK_DEF_ARN" \
    --output text > /dev/null

echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE"

# Verify deployment
echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount,TaskDefinition:taskDefinition}' \
    --output table

# Show recent tasks
echo ""
echo "📋 Recent Tasks:"
aws ecs list-tasks \
    --cluster "$ECS_CLUSTER" \
    --service-name "$ECS_SERVICE" \
    --query 'taskArns[0:3]' \
    --output table

# Check logs
echo ""
echo "📝 Checking recent logs..."
sleep 10  # Wait for task to start

TASK_ARN=$(aws ecs list-tasks \
    --cluster "$ECS_CLUSTER" \
    --service-name "$ECS_SERVICE" \
    --query 'taskArns[0]' \
    --output text)

if [ "$TASK_ARN" != "None" ] && [ "$TASK_ARN" != "" ]; then
    TASK_ID=$(echo "$TASK_ARN" | cut -d'/' -f3)
    LOG_STREAM="ecs/$CONTAINER_NAME/$TASK_ID"
    
    echo "Log stream: /aws/ecs/$ECS_TASK_DEFINITION/$LOG_STREAM"
    
    # Try to get recent log events
    aws logs get-log-events \
        --log-group-name "/aws/ecs/$ECS_TASK_DEFINITION" \
        --log-stream-name "$LOG_STREAM" \
        --limit 10 \
        --query 'events[*].[timestamp,message]' \
        --output table 2>/dev/null || echo "📝 Logs not yet available - check CloudWatch in a few minutes"
else
    echo "📝 No running tasks found yet - check status in a few minutes"
fi

# Clean up temporary files
rm -f task-definition.json task-definition-clean.json task-definition-updated.json

echo ""
echo "🎉 Deployment complete!"
echo "💡 Monitor logs: aws logs tail /aws/ecs/$ECS_TASK_DEFINITION --follow"