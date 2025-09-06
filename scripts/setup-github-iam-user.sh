#!/bin/bash

# Setup GitHub Actions IAM User (Alternative to OIDC)
# This creates an IAM user with programmatic access for GitHub Actions

set -e

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO_NAME="eliotatlani/personal-news"
IAM_USER_NAME="github-actions-user"
POLICY_NAME="github-actions-ecr-policy"

echo "🔧 Setting up GitHub Actions IAM User"
echo "===================================="
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Repository: $REPO_NAME"
echo "IAM User: $IAM_USER_NAME"
echo ""

# Create IAM user
echo "👤 Creating IAM user..."
if aws iam get-user --user-name "$IAM_USER_NAME" &>/dev/null; then
    echo "⚠️  IAM user '$IAM_USER_NAME' already exists"
else
    aws iam create-user --user-name "$IAM_USER_NAME" --tags Key=Purpose,Value=GitHubActions Key=Repository,Value="$REPO_NAME"
    echo "✅ IAM user created"
fi

# Create policy for ECR access
echo "📋 Creating IAM policy..."
cat > /tmp/github-ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        }
    ]
}
EOF

if aws iam get-policy --policy-arn "arn:aws:iam::$AWS_ACCOUNT_ID:policy/$POLICY_NAME" &>/dev/null; then
    echo "⚠️  Policy '$POLICY_NAME' already exists, updating..."
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::$AWS_ACCOUNT_ID:policy/$POLICY_NAME" \
        --policy-document file:///tmp/github-ecr-policy.json \
        --set-as-default
else
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/github-ecr-policy.json
fi

# Attach policy to user
echo "🔗 Attaching policy to user..."
aws iam attach-user-policy \
    --user-name "$IAM_USER_NAME" \
    --policy-arn "arn:aws:iam::$AWS_ACCOUNT_ID:policy/$POLICY_NAME"

# Create access key
echo "🔑 Creating access key..."
ACCESS_KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER_NAME" --output json)

ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')

# Clean up temp file
rm /tmp/github-ecr-policy.json

echo ""
echo "✅ Setup complete!"
echo ""
echo "🔐 GitHub Secrets to add:"
echo "========================"
echo "Name: AWS_ACCESS_KEY_ID"
echo "Value: $ACCESS_KEY_ID"
echo ""
echo "Name: AWS_SECRET_ACCESS_KEY"  
echo "Value: $SECRET_ACCESS_KEY"
echo ""
echo "Name: AWS_REGION"
echo "Value: us-east-1"
echo ""
echo "⚠️  IMPORTANT: Store these credentials securely!"
echo "   - Add them to your GitHub repository secrets"
echo "   - Never commit them to your code"
echo "   - Consider rotating them periodically"
echo ""
echo "📝 Next steps:"
echo "1. Go to GitHub → Settings → Secrets and variables → Actions"
echo "2. Add the three secrets above"
echo "3. Update your GitHub Actions workflow to use standard AWS credentials"