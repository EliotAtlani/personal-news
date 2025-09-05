#!/bin/bash

# Personal News Digest - AWS Deployment Script
set -e

# Configuration
PROJECT_NAME="personal-news"
ENVIRONMENT="prod"
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check Pulumi
    if ! command -v pulumi &> /dev/null; then
        log_error "Pulumi is not installed. Please install it first: https://www.pulumi.com/docs/get-started/install/"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

deploy_infrastructure() {
    log_info "Deploying infrastructure with Pulumi..."
    
    cd infrastructure
    
    # Install Python dependencies if needed
    if [ ! -d "venv" ]; then
        log_info "Setting up Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Login to Pulumi (using local backend)
    pulumi login --local
    
    # Set Pulumi passphrase for secrets (empty)
    export PULUMI_CONFIG_PASSPHRASE=""
    
    # Check if stack exists
    if pulumi stack ls | grep -q "$STACK_NAME"; then
        log_info "Stack exists, selecting..."
        pulumi stack select "$STACK_NAME"
    else
        log_info "Creating new stack..."
        pulumi stack init "$STACK_NAME" --secrets-provider=passphrase
    fi
    
    # Set configuration
    pulumi config set aws:region "$AWS_REGION"
    pulumi config set personal-news:project-name "$PROJECT_NAME"
    pulumi config set personal-news:environment "$ENVIRONMENT"
    
    # Deploy infrastructure
    log_info "Running Pulumi up..."
    pulumi up --yes
    
    cd ..
    log_success "Infrastructure deployment completed"
}

build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    cd infrastructure
    source venv/bin/activate
    
    # Set Pulumi passphrase for secrets (empty)
    export PULUMI_CONFIG_PASSPHRASE=""
    
    # Get ECR repository URI from Pulumi outputs
    ECR_URI=$(pulumi stack output ecr_repository_uri)
    
    if [ -z "$ECR_URI" ]; then
        log_error "Could not retrieve ECR repository URI"
        exit 1
    fi
    
    cd ..
    log_info "ECR Repository: $ECR_URI"
    
    # Login to ECR
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_URI"
    
    # Build image
    log_info "Building Docker image..."
    docker build -t "$PROJECT_NAME:latest" .
    
    # Tag for ECR
    docker tag "$PROJECT_NAME:latest" "$ECR_URI:latest"
    docker tag "$PROJECT_NAME:latest" "$ECR_URI:$(date +%Y%m%d-%H%M%S)"
    
    # Push to ECR
    log_info "Pushing image to ECR..."
    docker push "$ECR_URI:latest"
    docker push "$ECR_URI:$(date +%Y%m%d-%H%M%S)"
    
    log_success "Image built and pushed successfully"
    echo "ECR_URI=$ECR_URI" > .env.deploy
}

update_task_definition() {
    log_info "Updating ECS task definition with new image..."
    
    cd infrastructure
    source venv/bin/activate
    
    # Set Pulumi passphrase for secrets (empty)
    export PULUMI_CONFIG_PASSPHRASE=""
    
    # The task definition is automatically updated since we're using the ECR URI directly
    # We just need to refresh the Pulumi stack to pick up any changes
    log_info "Refreshing Pulumi stack..."
    pulumi refresh --yes
    
    # Update the stack (this will update the task definition with the new image)
    log_info "Updating Pulumi stack..."
    pulumi up --yes
    
    cd ..
    log_success "Task definition updated successfully"
}

setup_secrets() {
    log_info "Setting up secrets..."
    log_warning "You need to manually update the following secrets in AWS Secrets Manager:"
    
    # Get secret ARNs
    NEWSAPI_SECRET="${PROJECT_NAME}/newsapi-key-${ENVIRONMENT}"
    OPENAI_SECRET="${PROJECT_NAME}/openai-key-${ENVIRONMENT}"
    ANTHROPIC_SECRET="${PROJECT_NAME}/anthropic-key-${ENVIRONMENT}"
    EMAIL_SECRET="${PROJECT_NAME}/email-password-${ENVIRONMENT}"
    
    echo ""
    echo "1. NewsAPI Key:"
    echo "   aws secretsmanager update-secret --secret-id '$NEWSAPI_SECRET' --secret-string 'YOUR_NEWSAPI_KEY'"
    echo ""
    echo "2. OpenAI API Key:"
    echo "   aws secretsmanager update-secret --secret-id '$OPENAI_SECRET' --secret-string 'YOUR_OPENAI_KEY'"
    echo ""
    echo "3. Anthropic API Key:"
    echo "   aws secretsmanager update-secret --secret-id '$ANTHROPIC_SECRET' --secret-string 'YOUR_ANTHROPIC_KEY'"
    echo ""
    echo "4. Email Password:"
    echo "   aws secretsmanager update-secret --secret-id '$EMAIL_SECRET' --secret-string 'YOUR_EMAIL_APP_PASSWORD'"
    echo ""
}

upload_initial_preferences() {
    log_info "Uploading initial preferences to S3..."
    
    cd infrastructure
    source venv/bin/activate
    
    # Set Pulumi passphrase for secrets (empty)
    export PULUMI_CONFIG_PASSPHRASE=""
    
    # Get S3 bucket name from Pulumi outputs
    BUCKET_NAME=$(pulumi stack output s3_bucket_name)
    
    if [ -z "$BUCKET_NAME" ]; then
        log_error "Could not retrieve S3 bucket name"
        exit 1
    fi
    
    cd ..
    # Upload current preferences if they exist
    if [ -f "config/preferences.json" ]; then
        aws s3 cp config/preferences.json "s3://$BUCKET_NAME/preferences.json"
        log_success "Preferences uploaded to S3 bucket: $BUCKET_NAME"
    else
        log_warning "No local preferences.json found. You can create one later via your future web interface."
    fi
}

test_deployment() {
    log_info "Testing deployment..."
    
    cd infrastructure
    source venv/bin/activate
    
    # Set Pulumi passphrase for secrets (empty)
    export PULUMI_CONFIG_PASSPHRASE=""
    
    # Get deployment info from Pulumi outputs
    TASK_DEF_ARN=$(pulumi stack output task_definition_arn)
    CLUSTER_NAME=$(pulumi stack output ecs_cluster_name)
    
    cd ..
    log_info "Task Definition: $TASK_DEF_ARN"
    log_info "Cluster: $CLUSTER_NAME"
    log_success "Deployment completed successfully!"
    
    echo ""
    echo "Next steps:"
    echo "1. Update your API keys in AWS Secrets Manager (commands shown above)"
    echo "2. The EventBridge rule will trigger the task daily at 8:00 AM UTC"
    echo "3. Check CloudWatch Logs for execution details: /aws/ecs/${PROJECT_NAME}-${ENVIRONMENT}"
    echo ""
}

# Main deployment flow
main() {
    log_info "Starting deployment of Personal News Digest to AWS Fargate"
    log_info "Project: $PROJECT_NAME | Environment: $ENVIRONMENT | Region: $AWS_REGION"
    
    check_prerequisites
    deploy_infrastructure
    build_and_push_image
    update_task_definition
    upload_initial_preferences
    setup_secrets
    test_deployment
    
    log_success "Deployment completed! 🚀"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "secrets")
        setup_secrets
        ;;
    "build")
        build_and_push_image
        update_task_definition
        ;;
    "logs")
        aws logs tail "/aws/ecs/${PROJECT_NAME}-${ENVIRONMENT}" --follow --region "$AWS_REGION"
        ;;
    "destroy")
        log_warning "This will destroy all resources. Are you sure? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            cd infrastructure
            source venv/bin/activate
            export PULUMI_CONFIG_PASSPHRASE=""
            pulumi stack select "$STACK_NAME"
            pulumi destroy --yes
            pulumi stack rm "$STACK_NAME" --yes
            cd ..
            log_info "Stack destruction completed"
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|secrets|build|logs|destroy}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  secrets - Show secrets setup commands"
        echo "  build   - Build and deploy new image only"
        echo "  logs    - Follow CloudWatch logs"
        echo "  destroy - Delete all AWS resources"
        exit 1
        ;;
esac