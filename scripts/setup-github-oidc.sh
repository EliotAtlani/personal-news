#!/bin/bash

# Setup GitHub OIDC IAM Role for CI/CD
# Run this once to set up the IAM role for GitHub Actions

set -e

# Get AWS Account ID dynamically
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Could not determine AWS Account ID. Make sure you're authenticated with AWS CLI."
    exit 1
fi
GITHUB_REPO="eliotatlani/personal-news"  # Update this to match your GitHub repo
ROLE_NAME="github-actions-role"
POLICY_NAME="github-actions-policy"

echo "Setting up GitHub OIDC IAM Role for $GITHUB_REPO"

# Create OIDC Identity Provider (if it doesn't exist)
echo "Creating OIDC Identity Provider..."
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com \
  --tags Key=Name,Value=github-actions-oidc 2>/dev/null || echo "OIDC Provider already exists"

# Create trust policy
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": [
            "repo:${GITHUB_REPO}:ref:refs/heads/main",
            "repo:${GITHUB_REPO}:pull_request"
          ]
        }
      }
    }
  ]
}
EOF

# Create permissions policy
cat > permissions-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeImages",
        "ecr:DescribeImageScanFindings",
        "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks",
        "ecs:ListTasks",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/personal-news-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:${AWS_ACCOUNT_ID}:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::personal-news-preferences-prod-${AWS_ACCOUNT_ID}/*"
    }
  ]
}
EOF

# Create the IAM role
echo "Creating IAM role: $ROLE_NAME"
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for GitHub Actions to deploy personal-news" || echo "Role already exists"

# Create and attach the policy
echo "Creating and attaching IAM policy: $POLICY_NAME"
aws iam create-policy \
  --policy-name "$POLICY_NAME" \
  --policy-document file://permissions-policy.json \
  --description "Permissions for GitHub Actions personal-news deployment" 2>/dev/null || echo "Policy already exists"

aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/$POLICY_NAME"

# Clean up temporary files
rm trust-policy.json permissions-policy.json

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/$ROLE_NAME"

echo "✅ Setup complete!"
echo ""
echo "Role ARN: $ROLE_ARN"
echo ""
echo "Next steps:"
echo "1. Add this GitHub repository secret:"
echo "   Name: AWS_ROLE_ARN"  
echo "   Value: $ROLE_ARN"
echo ""
echo "2. Update the GitHub repo path in this script if needed: $GITHUB_REPO"
echo "3. Push your code to trigger the CI/CD pipeline"
echo "4. Use ./scripts/deploy-ecs.sh to manually deploy to ECS"