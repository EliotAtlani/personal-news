#!/bin/bash

# Sync Preferences Script
# Uploads local config/preferences.json to S3 bucket
# Usage: ./scripts/sync-preferences.sh [upload|download]

set -e

# Configuration
CONFIG_FILE="config/preferences.json"
S3_BUCKET_PREFIX="personal-news-preferences-prod"

# Get AWS Account ID dynamically
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not determine AWS Account ID. Make sure you're authenticated with AWS CLI."
    exit 1
fi

S3_BUCKET="${S3_BUCKET_PREFIX}-${AWS_ACCOUNT_ID}"
S3_KEY="preferences.json"
S3_URI="s3://${S3_BUCKET}/${S3_KEY}"

echo "🔄 Personal News Preferences Sync"
echo "================================"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "S3 Bucket: $S3_BUCKET"
echo "Local File: $CONFIG_FILE"
echo ""

# Determine action
ACTION="${1:-upload}"

if [[ "$ACTION" != "upload" && "$ACTION" != "download" ]]; then
    echo "❌ Error: Invalid action '$ACTION'. Use 'upload' or 'download'"
    echo ""
    echo "Usage:"
    echo "  ./scripts/sync-preferences.sh upload    # Upload local config to S3 (default)"
    echo "  ./scripts/sync-preferences.sh download  # Download S3 config to local"
    exit 1
fi

# Verify S3 bucket exists
echo "🔍 Checking S3 bucket..."
if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "❌ Error: S3 bucket '$S3_BUCKET' not found or not accessible"
    echo ""
    echo "Make sure:"
    echo "1. The bucket exists and is accessible"
    echo "2. You have proper AWS permissions"
    echo "3. Your infrastructure is deployed"
    exit 1
fi
echo "✅ S3 bucket accessible"

if [[ "$ACTION" == "upload" ]]; then
    echo ""
    echo "📤 Uploading preferences to S3..."
    
    # Check if local file exists
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "❌ Error: Local file '$CONFIG_FILE' not found"
        echo ""
        echo "Create the file first with your preferences, or download from S3:"
        echo "  ./scripts/sync-preferences.sh download"
        exit 1
    fi
    
    # Validate JSON format
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        echo "❌ Error: '$CONFIG_FILE' is not valid JSON"
        echo ""
        echo "Please fix the JSON format and try again"
        exit 1
    fi
    
    # Show current local config summary
    echo "📋 Local config summary:"
    echo "  User: $(jq -r '.user.name // "Not set"' "$CONFIG_FILE") ($(jq -r '.user.email // "Not set"' "$CONFIG_FILE"))"
    echo "  Topics: $(jq -r '.topics | length' "$CONFIG_FILE") topics"
    echo "  Sources: $(jq -r '.sources | length' "$CONFIG_FILE") sources"
    echo "  Max articles: $(jq -r '.content.max_articles // "Not set"' "$CONFIG_FILE")"
    echo ""
    
    # Check if S3 version exists
    if aws s3api head-object --bucket "$S3_BUCKET" --key "$S3_KEY" &>/dev/null; then
        echo "⚠️  S3 version already exists. This will overwrite it."
        echo ""
        read -p "Continue with upload? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Upload cancelled"
            exit 0
        fi
        echo ""
    fi
    
    # Upload with metadata
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    USER_NAME=$(whoami)
    
    aws s3 cp "$CONFIG_FILE" "$S3_URI" \
        --metadata "uploaded-by=$USER_NAME,uploaded-at=$TIMESTAMP" \
        --content-type "application/json"
    
    echo "✅ Preferences uploaded successfully!"
    echo ""
    echo "📊 S3 Object Info:"
    aws s3api head-object \
        --bucket "$S3_BUCKET" \
        --key "$S3_KEY" \
        --query '{Size:ContentLength,LastModified:LastModified,Metadata:Metadata}' \
        --output table
        
elif [[ "$ACTION" == "download" ]]; then
    echo ""
    echo "📥 Downloading preferences from S3..."
    
    # Check if S3 object exists
    if ! aws s3api head-object --bucket "$S3_BUCKET" --key "$S3_KEY" &>/dev/null; then
        echo "❌ Error: No preferences found in S3 bucket"
        echo ""
        echo "Upload your local preferences first:"
        echo "  ./scripts/sync-preferences.sh upload"
        exit 1
    fi
    
    # Check if local file exists
    if [[ -f "$CONFIG_FILE" ]]; then
        echo "⚠️  Local file '$CONFIG_FILE' already exists."
        echo ""
        echo "📋 Current local config summary:"
        if jq empty "$CONFIG_FILE" 2>/dev/null; then
            echo "  User: $(jq -r '.user.name // "Not set"' "$CONFIG_FILE") ($(jq -r '.user.email // "Not set"' "$CONFIG_FILE"))"
            echo "  Topics: $(jq -r '.topics | length' "$CONFIG_FILE") topics"
            echo "  Sources: $(jq -r '.sources | length' "$CONFIG_FILE") sources"
        else
            echo "  ⚠️  Current local file has invalid JSON"
        fi
        echo ""
        read -p "Overwrite local file with S3 version? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Download cancelled"
            exit 0
        fi
        echo ""
    fi
    
    # Ensure config directory exists
    mkdir -p "$(dirname "$CONFIG_FILE")"
    
    # Download from S3
    aws s3 cp "$S3_URI" "$CONFIG_FILE"
    
    echo "✅ Preferences downloaded successfully!"
    echo ""
    echo "📋 Downloaded config summary:"
    echo "  User: $(jq -r '.user.name // "Not set"' "$CONFIG_FILE") ($(jq -r '.user.email // "Not set"' "$CONFIG_FILE"))"
    echo "  Topics: $(jq -r '.topics | length' "$CONFIG_FILE") topics"
    echo "  Sources: $(jq -r '.sources | length' "$CONFIG_FILE") sources"
    echo "  Max articles: $(jq -r '.content.max_articles // "Not set"' "$CONFIG_FILE")"
fi

echo ""
echo "🎉 Sync complete!"
echo ""
echo "💡 Tips:"
echo "  - Use 'upload' to push local changes to production"
echo "  - Use 'download' to sync production settings locally"
echo "  - Always backup important configurations"