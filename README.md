# Personal News Digest

An AI-powered daily news digest that fetches the latest news based on your interests, generates intelligent summaries, and sends you a personalized newsletter via email.

## Features

- **Multi-source news aggregation**: NewsAPI, The Guardian, RSS feeds
- **AI-powered summaries**: OpenAI GPT or Anthropic Claude
- **Smart filtering**: Relevance scoring and duplicate removal
- **Personalized content**: Based on your topics and preferences
- **Beautiful newsletters**: HTML email templates with mobile support
- **Daily automation**: Scheduled delivery at your preferred time
- **Easy configuration**: JSON-based settings with environment variable support

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

4. **Run once**:
   ```bash
   uv run python run.py run
   ```

5. **For daily automation**, set up a cron job:
   ```bash
   # Edit your crontab
   crontab -e
   
   # Add this line for daily 8:00 AM execution
   0 8 * * * cd /path/to/personal-news && /usr/local/bin/uv run python run.py run
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

### Configuration File

Edit `config/preferences.json`:

```json
{
    "user": {
        "email": "your-email@example.com",
        "name": "Your Name",
        "timezone": "UTC"
    },
    "topics": [
        "artificial intelligence",
        "climate change",
        "technology",
        "space exploration"
    ],
    "schedule": {
        "time": "08:00",
        "enabled": true
    },
    "content": {
        "max_articles": 10,
        "summary_length": "medium"
    },
    "email": {
        "sender_email": "your-sender@gmail.com",
        "sender_password": "your-app-password"
    },
    "api_keys": {
        "newsapi": "your-newsapi-key",
        "openai": "your-openai-key"
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

- `setup`: Interactive configuration setup
- `test`: Test email configuration  
- `run`: Generate and send newsletter once

For daily automation, use cron instead of the built-in scheduler to avoid potential conflicts.

## Development

### Project Structure

```
personal-news/
├── src/
│   ├── config/         # Configuration management
│   ├── news/           # News fetching and filtering
│   ├── ai/             # AI summarization
│   ├── email/          # Email templating and sending
│   ├── scheduler.py    # Daily scheduling
│   └── main.py         # CLI interface
├── templates/          # Email templates
├── config/             # Configuration files
└── logs/               # Application logs
```

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black src/
uv run isort src/
```

## Customization

### Topics and Keywords

The system automatically expands your topics with related keywords. For example:
- "artificial intelligence" → AI, machine learning, neural networks, GPT
- "climate change" → global warming, carbon emissions, renewable energy

### Email Template

Customize the newsletter appearance by editing `templates/newsletter.html`.

### News Sources

Add RSS feeds or modify API sources in `src/news/fetchers.py`.

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