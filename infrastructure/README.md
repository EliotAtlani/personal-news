# Personal News Digest

AI-powered daily news digest that fetches, summarizes, and emails personalized news.

## Features

- Fetches news from multiple sources
- AI-powered summarization using OpenAI, Anthropic, or Google AI
- Personalized preferences stored in S3
- Automated daily email delivery
- Runs on AWS Fargate with EventBridge scheduling

## Deployment

Deploy to AWS using Pulumi:

```bash
../scripts/deploy.sh
```

## Configuration

Update your API keys in AWS Secrets Manager:

```bash
../scripts/deploy.sh secrets
```

## Monitoring

View logs:

```bash
../scripts/deploy.sh logs
```
