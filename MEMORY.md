# Founder Co-Pilot Project Memory

**Purpose:** Standalone CLI tool for the full founder journey — Discovery → Validation → Lead Gen → Outreach → CRM Sync.

---

## 📊 Project Status

| Aspect | Status |
|--------|--------|
| **Version** | V1.2.0 |
| **Branch** | `master` |
| **Latest Commit** | `54db497` (Multi-platform SaaS Growth Engine) |
| **Test Coverage** | 80%+ |
| **Strategic Review** | PENDING |

---

## 🎯 Vision

A local-first, open-source toolkit for SaaS founders:
- **Discovery:** Find real pain points from Reddit, HN, ProductHunt, G2
- **Validation:** Score and verify market demand
- **Lead Generation:** Extract and qualify potential customers
- **Outreach:** Generate and track engagement with leads
- **CRM Sync:** Push to HubSpot, Salesforce, or webhooks

---

## 🏗️ Architecture Overview

### Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Local-First** | SQLite storage, zero external dependencies required |
| **Privacy-Centric** | Credentials in `.env`, no data leaves machine |
| **Zero-Cost Default** | Works with local LLMs (Ollama); cloud APIs optional |
| **Decoupled Providers** | Every service implements common interface |
| **CLI Independence** | CLI works WITHOUT OpenClaw agent |

### Boundary Diagram

```
┌─────────────────────────────────────────────────────────┐
│               STANDALONE LAYER (Independent)            │
│  ┌────────────────────────────────────────────────────┐ │
│  │  CLI Binary (copilot)                              │ │
│  │  $ copilot discover --subreddits saas,startups     │ │
│  │  $ copilot validate --idea "AI writing tool"       │ │
│  │  $ copilot leads --keywords "looking for"          │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                               │
│                         ▼                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Core Engine                                       │ │
│  │  Discovery | Validation | Monitor | Leads          │ │
│  └────────────────────────────────────────────────────┘ │
│                         │                               │
│                         ▼                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Provider Layer (Swappable)                        │ │
│  │  Scrapers | LLMs | Storage | CRM                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           SKILL LAYER (OpenClaw Enhancement)            │
│  • Guides users through CLI setup                      │
│  • Manages cron jobs for scheduled execution           │
│  • Interprets results and provides insights            │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
founder-copilot/
├── README.md              # Context source of truth
├── MVP_SPEC.md            # Full technical spec (90KB)
├── UPGRADE_SPEC_V1.1.md   # V1.1 improvements
├── UPGRADE_SPEC_V1.2.md   # V1.2 roadmap
├── COMPREHENSIVE_RESEARCH_SaaS.md
├── copilot/               # Main package
│   ├── cli/               # CLI interface (Typer-based)
│   ├── core/              # Business logic
│   ├── models/            # Pydantic data models
│   ├── modules/           # Feature modules
│   │   ├── discovery.py   # Multi-platform discovery
│   │   ├── validation.py  # Idea validation
│   │   ├── leads.py       # Lead generation
│   │   ├── monitor.py     # Competitor monitoring
│   │   ├── scoring.py     # 7D opportunity scoring
│   │   ├── persona.py     # ICP generation
│   │   ├── outreach.py    # Outreach automation
│   │   └── export.py      # CRM export
│   ├── providers/         # Data providers
│   │   ├── scrapers/      # Reddit, HN, G2, ProductHunt, IndieHackers
│   │   ├── llm/           # Groq, Ollama
│   │   ├── storage/       # SQLite
│   │   └── crm/           # HubSpot, Salesforce
│   └── dashboard/         # Web dashboard (FastAPI)
├── bin/                   # Entry scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
└── venv/                  # Virtual environment
```

---

## ✅ Completed Features

### V1.0 - Foundation
| Feature | Status |
|---------|--------|
| Core Architecture | ✅ DONE |
| CLI Interface (Typer) | ✅ DONE |
| Provider Registry | ✅ DONE |
| SQLite Storage | ✅ DONE |
| Pydantic Models | ✅ DONE |
| Reddit Scraper | ✅ DONE |
| Discovery Module | ✅ DONE |
| Test Suite (86%) | ✅ DONE |

### V1.1 - Multi-Platform Expansion
| Feature | Status |
|---------|--------|
| Hacker News Provider | ✅ DONE |
| G2 Scraper (via Apify) | ✅ DONE |
| Capterra Scraper | ✅ DONE |
| ProductHunt Scraper | ✅ DONE |
| IndieHackers Scraper | ✅ DONE |
| 7D Opportunity Scoring | ✅ DONE |
| Persona Generation | ✅ DONE |
| CRM Export (HubSpot, Salesforce) | ✅ DONE |

### V1.2 - Growth Engine
| Feature | Status |
|---------|--------|
| Outreach Module | ✅ DONE |
| Web Dashboard (FastAPI) | ✅ DONE |
| Multi-channel Verification | ✅ DONE |

---

## 🔧 7D Opportunity Scoring Engine

The unified scoring algorithm ranks signals on 7 dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Pain Intensity** | 20% | LLM-analyzed frustration levels |
| **Engagement** | 20% | Normalized upvotes/comments across platforms |
| **Validation Evidence** | 15% | Presence of "me too" or solution requests |
| **Sentiment Intensity** | 15% | Depth of emotional expression |
| **Recency** | 10% | Time-decayed relevance |
| **Trend Momentum** | 10% | Growth in discussion volume |
| **Market Signal** | 10% | Cross-platform corroboration bonus |

---

## 🔌 Provider System

### Scrapers

| Provider | Location | Status |
|----------|----------|--------|
| Reddit | `scrapers/reddit.py` | ✅ Working |
| Hacker News | `scrapers/hackernews.py` | ✅ Working |
| G2 | `scrapers/apify_g2.py` | ✅ Working |
| Capterra | `scrapers/apify_capterra.py` | ✅ Working |
| ProductHunt | `scrapers/producthunt.py` | ✅ Working |
| IndieHackers | `scrapers/indiehackers.py` | ✅ Working |

### LLM Providers

| Provider | Location | Usage |
|----------|----------|-------|
| Groq | `llm/groq.py` | Cloud LLM (fast inference) |
| Ollama | `llm/ollama.py` | Local LLM (zero-cost) |

### CRM Providers

| Provider | Location | Status |
|----------|----------|--------|
| HubSpot | `crm/hubspot_provider.py` | ✅ Working |
| Salesforce | `crm/salesforce_provider.py` | ✅ Working |

---

## 🛠️ CLI Commands

```bash
# Activate environment
source venv/bin/activate

# Discovery
copilot discover --subreddits saas,startups --limit 50
copilot discover --source hackernews --query "pain points"
copilot discover --source all --query "notion" --min-score 0.7

# Validation
copilot validate --idea "AI writing tool" --depth deep

# Lead Generation
copilot leads --keywords "looking for,recommend" --alert email

# Export
copilot export --type leads --format hubspot --output leads_import.csv

# Monitor
copilot monitor --competitors "notion,roam" --interval 24h

# Outreach
copilot outreach --lead-id <id> --channel linkedin

# Dashboard
copilot dashboard --port 8000
```

---

## 📊 Data Models

### Core Models (Pydantic)

| Model | Purpose |
|-------|---------|
| `Signal` | Raw discovered pain point/opportunity |
| `Opportunity` | Scored and validated idea |
| `Lead` | Qualified potential customer |
| `Persona` | Ideal Customer Profile (ICP) |
| `OutreachRecord` | Tracked engagement attempt |

### Database Schema (SQLite)

| Table | Purpose |
|-------|---------|
| `signals` | Raw discovery data |
| `opportunities` | Scored opportunities |
| `leads` | Qualified leads |
| `personas` | Generated ICPs |
| `outreach_history` | Outreach tracking |
| `crm_sync_log` | CRM sync history |

---

## 🔐 Configuration

### Environment Variables (`.env`)

```bash
# LLM
GROQ_API_KEY=your_groq_key
OLLAMA_BASE_URL=http://localhost:11434

# Scrapers
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT=founder-copilot/1.0
APIFY_API_KEY=xxx

# CRM
HUBSPOT_API_KEY=xxx
SALESFORCE_CLIENT_ID=xxx
SALESFORCE_CLIENT_SECRET=xxx
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=copilot --cov-report=html

# Target: 80%+ coverage
```

---

## 📈 V1.2 Roadmap (DRAFT)

### Phase 1: Dashboard & Expansion (Week 1-2)
- [ ] Implement FastAPI backend
- [ ] Build initial Streamlit dashboard
- [ ] Add IndieHackers & Product Hunt scrapers

### Phase 2: Outreach & Tracking (Week 3-4)
- [ ] Implement OutreachModule
- [ ] Add outreach status tracking
- [ ] CLI command: `copilot outreach --lead-id <id>`

### Phase 3: CRM & Final Polish (Week 5-6)
- [ ] Implement SyncModule (HubSpot focus)
- [ ] Transition Dashboard to robust UI
- [ ] Final V1.2 documentation and E2E tests

---

## 🔗 Related Projects

| Project | Relationship |
|---------|--------------|
| Micro SaaS Project | Market research and idea validation |
| SecCheck One | Validated SaaS idea from Founder Co-Pilot |
| Tsukuyomi | Main project (funded by Micro SaaS) |

---

## 📝 Key Files

| File | Purpose |
|------|---------|
| `MVP_SPEC.md` | Full technical specification (90KB) |
| `UPGRADE_SPEC_V1.1.md` | V1.1 feature additions |
| `UPGRADE_SPEC_V1.2.md` | V1.2 roadmap |
| `docs/RELEASE_NOTES_V1.1.md` | V1.1 release notes |
| `copilot/SKILL.md` | OpenClaw skill wrapper |

---

## 🎯 Next Steps

1. **Strategic Review** — Evaluate market fit and prioritization
2. **User Testing** — Test CLI with real-world scenarios
3. **Documentation** — Complete user guide and API docs
4. **V1.2 Completion** — Finish dashboard and outreach features

---

*Last Updated: February 19, 2026*
