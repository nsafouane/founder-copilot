# Skill: Founder Co-Pilot

A discovery and validation engine for founders, allowing the agent to find "pain points" on social media (Reddit) and analyze them using LLMs.

## Commands

The skill provides a local CLI `copilot` located at `/root/.openclaw/workspace/founder-copilot/bin/copilot`.

### Discovering Pain Points
Find high-signal opportunities in specific subreddits.
```bash
/root/.openclaw/workspace/founder-copilot/bin/copilot discover --sub saas --limit 5 --min-score 0.5
```

### Configuration
Manage API keys and default settings.
```bash
# View config
/root/.openclaw/workspace/founder-copilot/bin/copilot config

# Set Groq API Key
/root/.openclaw/workspace/founder-copilot/bin/copilot config groq_api_key "YOUR_KEY"

# Set Subreddits
/root/.openclaw/workspace/founder-copilot/bin/copilot config subreddits '["saas", "solopreneur"]'
```

### Leads & Validation (Phase 4 WIP)
Manage captured leads and validate ideas.
```bash
/root/.openclaw/workspace/founder-copilot/bin/copilot leads
/root/.openclaw/workspace/founder-copilot/bin/copilot validate <post_id>
```

## Data Storage
Signals and posts are stored in a local SQLite database, typically at `~/.founder_copilot/founder_copilot.db`.

## Orchestration Guide
1. **Setup:** Ensure `GROQ_API_KEY`, `REDDIT_CLIENT_ID`, and `REDDIT_CLIENT_SECRET` are configured.
2. **Discovery:** Use `discover` to scan for problems founders can solve.
3. **Filtering:** The CLI filters for "composite value" which balances pain intensity, engagement, and recency.
4. **Action:** Once a high-value signal is found, the agent can use the post URL to investigate further or draft a solution proposal.
