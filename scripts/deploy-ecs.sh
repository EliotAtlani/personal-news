#!/bin/bash

# Manual ECS Task Runner Script for Personal News Multi-Profile System
# Usage: ./scripts/deploy-ecs.sh [IMAGE_TAG] [PROFILE]
# 
# Arguments:
#   IMAGE_TAG - Docker image tag to deploy (default: latest)
#   PROFILE   - Newsletter profile to deploy: tech, geopolitics, ai, or all (default: all)

set -e

# Usage function
usage() {
    echo "Usage: $0 [IMAGE_TAG] [PROFILE]"
    echo ""
    echo "Arguments:"
    echo "  IMAGE_TAG  Docker image tag to deploy (default: latest)"
    echo "  PROFILE    Newsletter profile to deploy (tech|geopolitics|ai|all, default: all)"
    echo ""
    echo "Examples:"
    echo "  $0                          # Deploy latest image for all profiles"
    echo "  $0 abc123def               # Deploy specific image for all profiles"
    echo "  $0 latest tech             # Deploy latest image for tech profile only"
    echo "  $0 abc123def geopolitics   # Deploy specific image for geopolitics profile"
    exit 1
}

# Parse arguments
IMAGE_TAG="${1:-latest}"
PROFILE="${2:-all}"

# Validate profile argument
case "$PROFILE" in
    tech|geopolitics|ai|all)
        ;;
    -h|--help)
        usage
        ;;
    *)
        echo "❌ Error: Invalid profile '$PROFILE'. Must be one of: tech, geopolitics, ai, all"
        echo ""
        usage
        ;;
esac

# Configuration
AWS_REGION="us-east-1"
ECS_CLUSTER="personal-news-prod"
ECR_REPOSITORY="personal-news-prod"
SUBNET_ID="subnet-0a40525b6500443fa"
SECURITY_GROUP_ID="sg-0c627ed0a75a442ba"

# Get AWS Account ID dynamically
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not determine AWS Account ID. Make sure you're authenticated with AWS CLI."
    exit 1
fi

echo "🚀 Personal News Multi-Profile ECS Deployment"
echo "============================================="
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Cluster: $ECS_CLUSTER"
echo "Profile(s): $PROFILE"
echo "Image Tag: $IMAGE_TAG"

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
echo "Image: $ECR_URI"
echo ""

# Determine which profiles to deploy
if [ "$PROFILE" = "all" ]; then
    PROFILES=("tech" "geopolitics" "ai")
else
    PROFILES=("$PROFILE")
fi

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

# Function to update task definition for a profile
update_task_definition() {
    local profile=$1
    # Map full profile names to shortened task definition names
    case "$profile" in
        "geopolitics") task_def_name="personal-news-geo-prod" ;;
        *) task_def_name="personal-news-${profile}-prod" ;;
    esac
    local container_name="personal-news-${profile}-container"
    
    echo ""
    echo "📝 Updating task definition for $profile profile..."
    
    # Download current task definition
    aws ecs describe-task-definition \
        --task-definition "$task_def_name" \
        --query taskDefinition \
        --output json > task-definition-${profile}.json
    
    # Clean task definition (remove read-only fields)
    jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' \
        task-definition-${profile}.json > task-definition-clean-${profile}.json
    
    # Update image in task definition
    jq --arg new_image "$ECR_URI" \
        '(.containerDefinitions[] | select(.name == "'$container_name'") | .image) = $new_image' \
        task-definition-clean-${profile}.json > task-definition-updated-${profile}.json
    
    # Register new task definition
    NEW_TASK_DEF_ARN=$(aws ecs register-task-definition \
        --cli-input-json file://task-definition-updated-${profile}.json \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    echo "✅ New task definition registered for $profile: $NEW_TASK_DEF_ARN"
    
    # Clean up temporary files for this profile
    rm -f task-definition-${profile}.json task-definition-clean-${profile}.json task-definition-updated-${profile}.json
    
    return 0
}

# Function to run task for a profile
run_task_for_profile() {
    local profile=$1
    # Map full profile names to shortened task definition names
    case "$profile" in
        "geopolitics") task_def_name="personal-news-geo-prod" ;;
        *) task_def_name="personal-news-${profile}-prod" ;;
    esac
    
    echo ""
    echo "🚀 Running ECS task for $profile profile..."
    
    TASK_ARN=$(aws ecs run-task \
        --cluster "$ECS_CLUSTER" \
        --task-definition "$task_def_name" \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
        --query 'tasks[0].taskArn' \
        --output text)
    
    if [ "$TASK_ARN" = "None" ] || [ -z "$TASK_ARN" ]; then
        echo "❌ Error: Failed to start task for $profile"
        return 1
    fi
    
    echo "✅ Task started for $profile: $TASK_ARN"
    
    # Wait a moment and check task status
    sleep 3
    
    TASK_STATUS=$(aws ecs describe-tasks \
        --cluster "$ECS_CLUSTER" \
        --tasks "$TASK_ARN" \
        --query 'tasks[0].lastStatus' \
        --output text)
    
    echo "📊 $profile Task Status: $TASK_STATUS"
    
    # Store task ARN for later reference
    profile_upper=$(echo "$profile" | tr '[:lower:]' '[:upper:]')
    eval "${profile_upper}_TASK_ARN=$TASK_ARN"
}

# Update task definitions for all selected profiles
echo ""
echo "🔄 Updating task definitions..."
for profile in "${PROFILES[@]}"; do
    update_task_definition "$profile"
done

# Ask user if they want to run tasks immediately
echo ""
echo "📋 Task definitions updated for: ${PROFILES[*]}"
echo ""
read -p "Do you want to run the newsletter tasks now? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Running tasks for selected profiles..."
    
    # Run tasks for all selected profiles
    for profile in "${PROFILES[@]}"; do
        run_task_for_profile "$profile"
    done
    
    echo ""
    echo "📝 Checking logs in 10 seconds..."
    sleep 10
    
    # Show logs for each profile
    for profile in "${PROFILES[@]}"; do
        profile_upper=$(echo "$profile" | tr '[:lower:]' '[:upper:]')
        task_var="${profile_upper}_TASK_ARN"
        task_arn=${!task_var}
        
        if [ -n "$task_arn" ]; then
            echo ""
            echo "📄 Logs for $profile profile:"
            echo "Task: $task_arn"
            
            TASK_ID=$(echo "$task_arn" | cut -d'/' -f3)
            LOG_STREAM="ecs-${profile}/${TASK_ID}"
            
            # Try to get recent log events
            aws logs get-log-events \
                --log-group-name "/aws/ecs/personal-news-prod" \
                --log-stream-name "$LOG_STREAM" \
                --limit 10 \
                --query 'events[*].message' \
                --output text 2>/dev/null || echo "📝 Logs not yet available for $profile"
        fi
    done
    
else
    echo "📋 Task definitions updated but not executed."
    echo ""
    echo "To run tasks manually:"
    for profile in "${PROFILES[@]}"; do
        case "$profile" in
            "geopolitics") task_def="personal-news-geo-prod" ;;
            *) task_def="personal-news-${profile}-prod" ;;
        esac
        echo "  $profile: aws ecs run-task --cluster $ECS_CLUSTER --task-definition $task_def --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}'"
    done
fi

echo ""
echo "🎉 Deployment completed!"
echo ""
echo "📅 Newsletter Schedules:"
echo "  Tech:        Mondays at 12:00 UTC"
echo "  Geopolitics: Wednesdays at 12:00 UTC" 
echo "  AI:          Fridays at 12:00 UTC"
echo ""
echo "💡 Monitor all logs: aws logs tail /aws/ecs/personal-news-prod --follow"
echo "💡 Check cluster status: aws ecs describe-clusters --clusters $ECS_CLUSTER"