# Personal News Setup Guide

## 🎯 What You've Built

A complete AI-powered daily news digest system that:
- Fetches news from multiple sources (NewsAPI, Guardian, RSS)
- Uses AI (OpenAI/Anthropic) to generate intelligent summaries
- Sends beautiful HTML newsletters to your email
- Automatically categorizes content by topic

## 📋 Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
cd personal-news
uv sync
```

### 2. Get API Keys

#### NewsAPI (Required)
- Go to [newsapi.org](https://newsapi.org)
- Sign up for free account
- Copy your API key

#### AI Service (Required - choose one)
- **OpenAI**: [platform.openai.com](https://platform.openai.com) → API Keys
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com) → API Keys

#### Gmail Setup (Required)
- Enable 2FA on your Gmail account
- Generate App Password: [Google Account Settings](https://myaccount.google.com/apppasswords)
- Use the 16-character app password (not your regular password)

### 3. Configure System
```bash
uv run python run.py setup
```

Follow the prompts to enter:
- Your email address
- Topics you're interested in (e.g., "AI, climate change, technology")
- Gmail credentials
- API keys
- Preferred send time

### 4. Test Configuration
```bash
uv run python run.py test
```

You should receive a test email.

### 5. Generate Your First Newsletter
```bash
uv run python run.py run
```

This will:
- Fetch latest news on your topics
- Generate AI summaries
- Send you a beautiful newsletter

## 🔄 Daily Automation

### Option 1: Cron Job (Recommended)
```bash
./scripts/setup_cron.sh
```

This sets up automatic daily delivery.

### Option 2: Manual Cron Setup
```bash
crontab -e
```

Add this line (adjust path and time):
```
0 8 * * * cd /path/to/personal-news && /usr/local/bin/uv run python run.py run
```

## 🎨 Customization

### Topics
Edit `config/preferences.json` and modify the `topics` array:
```json
{
  "topics": [
    "artificial intelligence",
    "renewable energy", 
    "space exploration",
    "biotechnology"
  ]
}
```

### Newsletter Appearance
Edit `templates/newsletter.html` to customize:
- Colors and styling
- Layout structure
- Logo/branding

### Content Settings
In `config/preferences.json`:
```json
{
  "content": {
    "max_articles": 15,          // More articles
    "summary_length": "long",    // Longer summaries
    "min_relevance_score": 0.4   // Include more articles
  }
}
```

## 🛠 Troubleshooting

### Common Issues

1. **No articles found**
   - Broaden your topics
   - Lower `min_relevance_score`
   - Check API key validity

2. **Email not sending**
   - Use Gmail App Password (not regular password)
   - Check SMTP settings
   - Run test: `uv run python run.py test`

3. **AI summarization failing**
   - Verify API keys have credits
   - System falls back to basic summaries
   - Check rate limits

### Logs
Check `logs/cron.log` for automated run results.

## 📊 Example Output

Your newsletter will include:
- **Today's Highlights**: Overall summary
- **Categorized Articles**: Technology, Science, Business, etc.
- **AI Summaries**: 2-3 sentence summaries
- **Key Points**: Bullet point highlights
- **Source Links**: Click to read full articles

## 🔐 Security Notes

- API keys are stored in `config/preferences.json`
- Use environment variables for production:
  ```bash
  export NEWSAPI_KEY="your-key"
  export OPENAI_API_KEY="your-key"
  export EMAIL_PASSWORD="your-app-password"
  ```
- Never commit `config/preferences.json` to version control

## 📈 Next Steps

1. **Monitor**: Check your newsletter daily and adjust topics
2. **Optimize**: Tune relevance scores and summary length  
3. **Expand**: Add more news sources in `src/news/fetchers.py`
4. **Share**: The system works for multiple users with different configs

Your TLDR-style newsletter is ready! 🎉