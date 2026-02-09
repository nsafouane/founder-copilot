# Founder Co-Pilot V1.1 Release Notes

## 🚀 Overview
Founder Co-Pilot V1.1 is a major intelligence expansion of our standalone CLI tool for SaaS founders. We've moved beyond simple Reddit scraping into a multi-platform discovery engine with unified opportunity scoring.

## ✨ New Features

### 1. Multi-Platform Discovery
- **Hacker News:** Scrape "Ask HN", "Show HN", and search queries for technical pain points.
- **Review Sites (G2/Capterra):** Direct integration via Apify to pull competitor reviews and star ratings.
- **Unified Interface:** New `--source` and `--target` flags allow targeting specific platforms or "all" at once.

### 2. Unified Opportunity Scoring (The 7D Engine)
A new weighted algorithm that ranks signals based on:
1. **Pain Intensity:** LLM-analyzed frustration levels.
2. **Engagement:** Normalized upvotes/comments across platforms.
3. **Validation Evidence:** Presence of "me too" or solution requests.
4. **Sentiment Intensity:** Depth of emotional expression.
5. **Recency:** Time-decayed relevance.
6. **Trend Momentum:** Growth in discussion volume.
7. **Market Signal:** Cross-platform corroboration bonus.

### 3. CRM & Lead Intelligence
- **Multi-channel Verification:** Automatic lookup of LinkedIn/Twitter profiles for high-intent leads.
- **CRM Export:** Native export formats for **HubSpot** and **Salesforce** lead/contact imports.
- **Persona Generation:** Auto-generate detailed target customer profiles (Name, Role, Industry, Budget) for top opportunities.

### 4. Web Dashboard (Prototype)
- A local FastAPI + Vue 3 dashboard to visualize discovery stats, top opportunities, and qualified leads without touching the terminal.

## 🔧 Improvements & Fixes
- **Foundation Refactor:** Switched to generic `channel` fields in Pydantic models to support non-Reddit sources.
- **Storage Evolution:** Additive SQLite migrations to track `opportunity_scores` and `verified_profiles`.
- **Test Coverage:** Maintained 85%+ coverage across the new modular provider architecture.

## 📖 Getting Started
```bash
# Discover everything about 'notion' across all sources
copilot scan --query "notion" --min-score 0.7

# Export leads for HubSpot
copilot export --type leads --format hubspot --output leads_import.csv
```

---
*Tanit | Co-founder & Technical Architect | February 2026*
