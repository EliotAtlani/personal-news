# AWS Fargate Deployment Guide

This guide will help you deploy your Personal News Digest application to AWS using Fargate.

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Docker** installed and running

3. **AWS Account** with appropriate permissions for:
   - CloudFormation
   - ECS/Fargate
   - S3
   - ECR
   - Secrets Manager
   - EventBridge
   - VPC/Networking

## Quick Deployment

### 1. Deploy Everything
```bash
./scripts/deploy.sh
```

This command will:
- Create all AWS infrastructure
- Build and push Docker image to ECR
- Deploy the ECS task definition
- Upload preferences to S3
- Show you how to set up API keys

### 2. Configure API Keys
After deployment, update your secrets in AWS Secrets Manager:

```bash
# Replace with your actual keys
aws secretsmanager update-secret --secret-id 'personal-news/newsapi-key-prod' --secret-string 'YOUR_NEWSAPI_KEY'
aws secretsmanager update-secret --secret-id 'personal-news/openai-key-prod' --secret-string 'YOUR_OPENAI_KEY'
aws secretsmanager update-secret --secret-id 'personal-news/anthropic-key-prod' --secret-string 'YOUR_ANTHROPIC_KEY'
aws secretsmanager update-secret --secret-id 'personal-news/email-password-prod' --secret-string 'YOUR_EMAIL_APP_PASSWORD'
```

### 3. Verify Deployment
```bash
# Check logs
./scripts/deploy.sh logs

# Manual test run (optional)
aws ecs run-task \
  --cluster personal-news-prod \
  --task-definition personal-news-prod \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

## Architecture Overview

```
EventBridge (8:00 AM UTC) → ECS Fargate Task → S3 (preferences) → Gmail SMTP
```

### Components Created:

1. **S3 Bucket**: Stores preferences with versioning enabled
2. **ECS Cluster**: Fargate cluster for running containers
3. **Task Definition**: Container specs with 256 CPU / 512 MB RAM
4. **EventBridge Rule**: Daily trigger at 8:00 AM UTC
5. **ECR Repository**: Private Docker registry
6. **Secrets Manager**: Secure storage for API keys
7. **VPC & Networking**: Private subnets with NAT gateway
8. **IAM Roles**: Least-privilege permissions

## Environment Variables

The application uses these environment variables in Fargate:

- `AWS_USE_S3=true` - Enables S3 preferences storage
- `S3_BUCKET_NAME` - Auto-set to created bucket
- `AWS_DEFAULT_REGION` - Auto-set to deployment region

API keys are loaded from Secrets Manager as environment variables.

## Cost Estimation

**Monthly costs (US East 1):**
- Fargate task (5 min/day): ~$0.50
- S3 storage (small JSON): ~$0.01
- NAT Gateway: ~$32
- **Total: ~$33/month**

**Cost optimization options:**
- Use existing VPC/NAT Gateway to reduce costs
- Run in public subnet (less secure but cheaper)
- Reduce task frequency

## Management Commands

```bash
# View deployment status
aws cloudformation describe-stacks --stack-name personal-news-prod

# Update only the container image
./scripts/deploy.sh build

# View logs
./scripts/deploy.sh logs

# Show secrets setup commands
./scripts/deploy.sh secrets

# Destroy all resources
./scripts/deploy.sh destroy
```

## Customization

### Change Schedule
Edit the `ScheduleTime` parameter in `infrastructure/cloudformation.yaml`:
```yaml
Parameters:
  ScheduleTime:
    Default: "cron(0 8 * * ? *)"  # 8:00 AM UTC daily
```

Common schedules:
- `cron(0 8 * * ? *)` - 8:00 AM UTC daily
- `cron(0 6 * * MON-FRI *)` - 6:00 AM UTC weekdays only
- `cron(0 */12 * * ? *)` - Every 12 hours

### Modify Resources
Edit `infrastructure/cloudformation.yaml` to adjust:
- CPU/Memory allocation
- Retention policies
- Security settings
- Environment variables

### Update Application
1. Make code changes
2. Run `./scripts/deploy.sh build` to rebuild and deploy
3. Check logs with `./scripts/deploy.sh logs`

## Troubleshooting

### Common Issues:

1. **Task fails to start**
   - Check CloudWatch logs: `/aws/ecs/personal-news-prod`
   - Verify secrets are properly set
   - Check task definition environment variables

2. **S3 permissions errors**
   - Ensure task role has S3 permissions
   - Verify bucket exists and is accessible

3. **Network connectivity issues**
   - Check security group allows outbound HTTPS (443)
   - Verify NAT Gateway is working
   - Consider using public subnet for testing

4. **Email delivery fails**
   - Verify Gmail app password is correct
   - Check firewall allows SMTP (587)
   - Test email credentials locally first

### Debug Commands:
```bash
# Check task execution
aws ecs describe-tasks --cluster personal-news-prod --tasks [task-arn]

# View task logs
aws logs get-log-events --log-group-name "/aws/ecs/personal-news-prod" --log-stream-name [stream-name]

# List secrets
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `personal-news`)]'
```

## Security Notes

- All resources use least-privilege IAM policies
- S3 bucket blocks public access
- Secrets stored in AWS Secrets Manager
- Tasks run in private subnets
- All communications encrypted in transit

## Next Steps

1. **Set up monitoring**: Add CloudWatch alarms for task failures
2. **Create web interface**: Build frontend to edit preferences
3. **Add notifications**: SNS alerts for execution status
4. **Multi-environment**: Deploy dev/staging environments