# Founder Co-Pilot Documentation

## 🏗 Architecture
Founder Co-Pilot is built as a modular Python CLI.

### Core Components
- **Providers:** Scrapers (Reddit, HN, Apify) and LLM (Groq, Ollama).
- **Modules:** Business logic for Discovery, Scoring, Validation, Leads, and Export.
- **CLI:** Click-based command interface.
- **Storage:** SQLite backend for persistence.

## 🚀 Usage Guide

### Discovery
Use `discover` for targeted scraping or `scan` for cross-platform search.
```bash
copilot scan -q "crm for small business" --min-score 0.6
```

### Validation
Deep-dive into a specific post to map competitors and market size.
```bash
copilot validate <post_id> --deep
```

### Lead Management
Identify high-intent leads and verify their social profiles.
```bash
copilot leads --verify
```

### Exporting
```bash
copilot export --type leads --format hubspot
```

## ⚙️ Configuration
Configure your API keys in `config.json` or via environment variables.
- `GROQ_API_KEY`: For LLM analysis.
- `REDDIT_CLIENT_ID/SECRET`: For Reddit access.
- `APIFY_API_TOKEN`: For G2/Capterra scraping.
