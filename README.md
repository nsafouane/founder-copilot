# 🚀 Founder Co-Pilot

**Path:** `/root/.openclaw/workspace/founder-copilot/`
**Type:** Standalone CLI Tool for SaaS Founders
**Nature:** Open-source, modular, locally-runnable

---

## 🎯 Vision

A CLI tool for the full founder journey:
- **Discovery:** Find real pain points from Reddit, HN, ProductHunt
- **Validation:** Score and verify market demand
- **Lead Generation:** Extract and qualify potential customers

---

## 📂 Structure

```
founder-copilot/
├── README.md          # This file (context source of truth)
├── MVP_SPEC.md        # Technical specification (90KB)
├── copilot/           # Main package
│   ├── cli/           # CLI interface (Click-based)
│   ├── core/          # Business logic
│   ├── models/        # Data models
│   ├── modules/       # Feature modules (discovery, validation, leads)
│   └── providers/     # Data providers (Reddit, HN, etc.)
├── bin/               # Entry scripts
├── tests/             # Test suite
├── docs/              # Documentation
└── venv/              # Virtual environment
```

---

## 🛠️ Tech Stack

| Component | Tool |
|-----------|------|
| Language | Python 3.11+ |
| CLI Framework | Click |
| Data Providers | PRAW (Reddit), custom scrapers |
| LLM | GLM 4.7 for analysis |
| Testing | pytest (80%+ coverage) |

---

## 📋 Current Status

| Task | Status |
|------|--------|
| Core Architecture | ✅ DONE |
| CLI Interface | ✅ DONE |
| Discovery Module | ✅ DONE (Multi-Platform ready) |
| Validation Module | ✅ DONE |
| Lead Gen Module | ✅ DONE |
| Opportunity Score | ✅ DONE (7-dimensional engine) |
| Hacker News Provider | ✅ DONE |
| Review Scrapers (G2) | ✅ DONE |
| Multi-channel Verification | 🚧 IN PROGRESS |

---

## 🎯 CURRENT PRIORITY

**Test & Debug CLI with Multiple Scenarios**
1. Run CLI through various real-world scenarios
2. Document bugs and edge cases
3. Review output quality and accuracy
4. Confirm tool is ready for improvements

**Deep Research: Best Improvements**
1. Research similar tools in the market
2. Identify missing features and UX gaps
3. Prioritize improvements by impact

---

## 🔧 Commands

```bash
# Activate environment
source venv/bin/activate

# Run CLI
python -m copilot.cli --help

# Run tests
pytest tests/ -v --cov=copilot
```

---

## 📜 Rules & Conventions

1. **Modular design** — Each feature is a separate module
2. **Provider abstraction** — Data sources are swappable
3. **Test everything** — 80%+ coverage minimum
4. **CLI-first** — All features accessible via CLI

---

## 🔗 Related

- **Task Tracking:** `PROJECT_TREE.md` in workspace root
- **Market Research:** `/root/.openclaw/workspace/micro-saas-project/`
- **Research/Reports:** `/root/.openclaw/workspace/research-reports/`

---

*Load this README before any Founder Co-Pilot task.*
