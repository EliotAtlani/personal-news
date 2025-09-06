#!/bin/bash

# Build and Push Docker Image Script for Personal News
# Usage: ./scripts/build-and-push.sh [IMAGE_TAG]
# 
# Arguments:
#   IMAGE_TAG - Docker image tag (default: latest)

set -e

# Usage function
usage() {
    echo "Usage: $0 [IMAGE_TAG]"
    echo ""
    echo "Arguments:"
    echo "  IMAGE_TAG  Docker image tag (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Build and push with 'latest' tag"
    echo "  $0 v1.2.3            # Build and push with 'v1.2.3' tag"
    echo "  $0 \$(git rev-parse --short HEAD)  # Build and push with git commit hash"
    exit 1
}

# Parse arguments
IMAGE_TAG="${1:-latest}"

# Validate arguments
case "$1" in
    -h|--help)
        usage
        ;;
esac

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="personal-news-prod"
LOCAL_IMAGE_NAME="personal-news"

# Get AWS Account ID dynamically
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not determine AWS Account ID. Make sure you're authenticated with AWS CLI."
    exit 1
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

echo "🐳 Personal News Docker Build & Push"
echo "===================================="
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Repository: $ECR_REPOSITORY"
echo "Image Tag: $IMAGE_TAG"
echo "Full Image URI: ${ECR_URI}:${IMAGE_TAG}"
echo ""

# Step 1: Clean up any existing images
echo "🧹 Cleaning up existing local images..."
docker rmi "$LOCAL_IMAGE_NAME" 2>/dev/null || echo "No existing local image to remove"
docker rmi "${ECR_URI}:${IMAGE_TAG}" 2>/dev/null || echo "No existing tagged image to remove"

# Step 2: Build Docker image
echo "🔨 Building Docker image..."
echo "Command: docker build --platform linux/amd64 -t $LOCAL_IMAGE_NAME ."
docker build --platform linux/amd64 -t "$LOCAL_IMAGE_NAME" .

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"

# Step 3: Tag image for ECR
echo ""
echo "🏷️  Tagging image for ECR..."
docker tag "$LOCAL_IMAGE_NAME" "${ECR_URI}:${IMAGE_TAG}"

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker tag failed"
    exit 1
fi

echo "✅ Image tagged successfully"

# Step 4: Login to ECR
echo ""
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

if [ $? -ne 0 ]; then
    echo "❌ Error: ECR login failed"
    exit 1
fi

echo "✅ ECR login successful"

# Step 5: Push image to ECR
echo ""
echo "📤 Pushing image to ECR..."
echo "Command: docker push ${ECR_URI}:${IMAGE_TAG}"
docker push "${ECR_URI}:${IMAGE_TAG}"

if [ $? -ne 0 ]; then
    echo "❌ Error: Docker push failed"
    exit 1
fi

echo "✅ Image pushed successfully"

# Step 6: Verify image in ECR
echo ""
echo "🔍 Verifying image in ECR..."
aws ecr describe-images \
    --repository-name "$ECR_REPOSITORY" \
    --image-ids imageTag="$IMAGE_TAG" \
    --region "$AWS_REGION" \
    --query 'imageDetails[0].{Size:imageSizeInBytes,PushedAt:imagePushedAt}' \
    --output table

if [ $? -ne 0 ]; then
    echo "❌ Warning: Could not verify image in ECR, but push may have succeeded"
else
    echo "✅ Image verified in ECR"
fi

# Step 7: Clean up local images (optional)
echo ""
read -p "🗑️  Clean up local images? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 Cleaning up local images..."
    docker rmi "$LOCAL_IMAGE_NAME" 2>/dev/null || echo "Local image already removed"
    docker rmi "${ECR_URI}:${IMAGE_TAG}" 2>/dev/null || echo "Tagged image already removed"
    echo "✅ Local images cleaned up"
else
    echo "📝 Local images kept for debugging"
fi

echo ""
echo "🎉 Build and push completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "  • Deploy with: ./scripts/deploy-ecs.sh $IMAGE_TAG [PROFILE]"
echo "  • Update all profiles: ./scripts/deploy-ecs.sh $IMAGE_TAG all"
echo "  • Check ECR: aws ecr list-images --repository-name $ECR_REPOSITORY"
echo ""
echo "💡 Image URI: ${ECR_URI}:${IMAGE_TAG}"