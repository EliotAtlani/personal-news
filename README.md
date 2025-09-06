# Personal News Digest - Multi-Profile System

An AI-powered weekly news digest system that delivers specialized newsletters based on distinct topic profiles, with intelligent summaries and beautiful email templates.

## Newsletter Profiles

🚀 **Tech Weekly** - Mondays @ 12:00 UTC  
Software engineering, programming, DevOps, cloud computing, and developer tools

🌍 **Geopolitics Weekly** - Wednesdays @ 12:00 UTC  
International conflicts, foreign policy, defense, security, and diplomacy

🤖 **AI Weekly** - Fridays @ 12:00 UTC  
Artificial intelligence, GenAI, machine learning, and AI research

## Features

- **Multi-profile newsletters**: Three distinct weekly newsletters with specialized content
- **Multi-source news aggregation**: NewsAPI, The Guardian, specialized sources per profile
- **AI-powered summaries**: OpenAI GPT or Anthropic Claude with profile-specific prompting
- **Smart filtering**: Relevance scoring, duplicate removal, and article history tracking
- **Profile-specific templates**: Unique styling and branding for each newsletter
- **Weekly automation**: Scheduled delivery via AWS EventBridge
- **Cloud deployment**: AWS ECS Fargate with S3 configuration storage

## Quick Start

1. **Install with uv**:
   ```bash
   cd personal-news
   uv sync
   ```

2. **Interactive setup**:
   ```bash
   uv run python run.py setup
   ```

3. **Test configuration**:
   ```bash
   uv run python run.py test
   ```

4. **Run specific profile**:
   ```bash
   uv run python run.py run --profile tech        # Tech newsletter
   uv run python run.py run --profile geopolitics # Geopolitics newsletter
   uv run python run.py run --profile ai          # AI newsletter
   uv run python run.py run                       # Defaults to tech
   ```

5. **For cloud deployment**:
   ```bash
   # Deploy AWS infrastructure
   cd infrastructure/
   pulumi up
   
   # Deploy application to ECS
   ./scripts/deploy-ecs.sh latest all  # All profiles
   ./scripts/deploy-ecs.sh latest tech # Specific profile
   ```

## Configuration

### Required API Keys

1. **NewsAPI**: Get free API key from [newsapi.org](https://newsapi.org)
2. **AI Service** (choose one):
   - **OpenAI**: Get API key from [platform.openai.com](https://platform.openai.com)
   - **Anthropic**: Get API key from [console.anthropic.com](https://console.anthropic.com)

### Email Setup (Gmail recommended)

1. Enable 2-factor authentication on your Gmail account
2. Generate an app password: [Google Account Settings](https://myaccount.google.com/apppasswords)
3. Use the app password in your configuration

### Multi-Profile Configuration

The system uses a multi-profile configuration in `config/preferences.json`:

```json
{
  "user": {
    "email": "your-email@example.com",
    "name": "Your Name",
    "timezone": "UTC"
  },
  "profiles": {
    "tech": {
      "name": "Tech & Software Engineering Weekly",
      "subject_prefix": "Tech Weekly",
      "schedule": {
        "day_of_week": 1,
        "time": "12:00"
      },
      "topics": [
        "software engineering",
        "programming languages",
        "developer tools",
        "DevOps",
        "cloud computing"
      ],
      "sources": [
        "stackoverflow-blog",
        "hackernews",
        "freecodecamp",
        "aws-blog"
      ],
      "content": {
        "time_range": "last_week",
        "max_articles": 5,
        "min_articles": 2,
        "summary_length": "medium"
      }
    },
    "geopolitics": {
      "name": "Geopolitics & Conflicts Weekly",
      "subject_prefix": "Geo Weekly",
      "schedule": {
        "day_of_week": 3,
        "time": "12:00"
      },
      "topics": [
        "geopolitics",
        "international conflicts",
        "foreign policy",
        "defense"
      ],
      "sources": [
        "bbc-world",
        "reuters-world",
        "guardian-world"
      ]
    },
    "ai": {
      "name": "AI & GenAI Weekly",
      "subject_prefix": "AI Weekly",
      "schedule": {
        "day_of_week": 5,
        "time": "12:00"
      },
      "topics": [
        "artificial intelligence",
        "GenAI",
        "machine learning"
      ],
      "sources": [
        "mit-tech-review",
        "towards-data-science"
      ]
    }
  },
  "email": {
    "sender_email": "your-sender@gmail.com",
    "sender_password": "your-app-password"
  },
  "api_keys": {
    "newsapi": "your-newsapi-key",
    "openai": "your-openai-key"
  },
  "history": {
    "sent_articles": []
  }
}
```

### Environment Variables

You can also use environment variables:

```bash
export NEWSAPI_KEY="your-newsapi-key"
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export EMAIL_PASSWORD="your-app-password"
```

## Commands

- `setup`: Interactive configuration setup (creates multi-profile config)
- `test`: Test email configuration  
- `run --profile <name>`: Generate and send newsletter for specific profile
- `run`: Generate and send newsletter (defaults to tech profile)

### Profile Commands
```bash
uv run python run.py run --profile tech        # Monday tech newsletter
uv run python run.py run --profile geopolitics # Wednesday geopolitics newsletter  
uv run python run.py run --profile ai          # Friday AI newsletter
```

### Cloud Deployment Commands
```bash
./scripts/deploy-ecs.sh                    # Deploy all profiles with latest image
./scripts/deploy-ecs.sh abc123def         # Deploy all profiles with specific image
./scripts/deploy-ecs.sh latest tech       # Deploy tech profile only
./scripts/deploy-ecs.sh latest geopolitics # Deploy geopolitics profile only
./scripts/deploy-ecs.sh latest ai         # Deploy AI profile only
```

## Development

### Project Structure

```
personal-news/
├── src/
│   ├── config/         # Multi-profile configuration management
│   ├── news/           # News fetching and filtering
│   ├── ai/             # AI summarization
│   ├── email/          # Email templating and sending
│   └── main.py         # CLI interface
├── templates/          # Profile-specific email templates
│   ├── tech-newsletter.html
│   ├── geopolitics-newsletter.html  
│   ├── ai-newsletter.html
│   └── newsletter.html # Default template
├── infrastructure/     # AWS Pulumi infrastructure
├── scripts/           # Deployment and utility scripts
├── config/            # Configuration files
└── logs/              # Application logs
```

### Development Tools

The project uses **Ruff** for linting and **Black** for formatting:

```bash
# Check code with ruff
make lint
# or: uv run ruff check src/

# Format code with black
make format  
# or: uv run black src/

# Auto-fix linting issues
make fix
# or: uv run ruff check --fix src/

# Run all checks (lint + format check)
make check

# Complete development workflow (fix + format + check)
make dev-check
```

### Running Tests

```bash
make test
# or: uv run pytest
```

### Development Workflow

```bash
# Set up development environment
make dev-setup

# Before committing, run:
make dev-check

# Available make commands
make help
```

## Customization

### Adding New Profiles

1. Add profile configuration to `config/preferences.json`
2. Create new email template in `templates/`
3. Update infrastructure with new EventBridge schedule
4. Deploy with updated configuration

### Profile-Specific Templates

Each profile has its own template with unique styling:
- `tech-newsletter.html` - Blue theme, code-focused styling
- `geopolitics-newsletter.html` - Red theme, formal typography  
- `ai-newsletter.html` - Purple theme, futuristic gradients

### News Sources

Each profile has specialized news sources:
- **Tech**: Stack Overflow Blog, HackerNews, AWS Blog, Netflix Tech Blog
- **Geopolitics**: BBC World, Reuters, Guardian World, Foreign Affairs
- **AI**: MIT Tech Review, Towards Data Science, VentureBeat

### Article History & Deduplication

The system tracks sent articles in `history.sent_articles` to prevent duplicates across all profiles. Articles are filtered by:
- URL deduplication
- Time range (last week for each profile)
- Relevance scoring
- Profile-specific topics

## Troubleshooting

### Common Issues

1. **Email not sending**:
   - Check Gmail app password (not regular password)
   - Verify SMTP settings
   - Run `uv run python -m src.main test`

2. **No articles found**:
   - Broaden your topics
   - Check API key validity
   - Lower `min_relevance_score` in config

3. **AI summarization failing**:
   - Verify API keys
   - Check rate limits
   - Try different AI service

### Logs

Check logs in the `logs/` directory for detailed error information.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and feature requests, please create an issue on GitHub.