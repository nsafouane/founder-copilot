# OpenCode Project Rules: Founder Co-Pilot

## 🎯 Vision
Build a modular, open-source CLI tool for solopreneurs to discover and validate SaaS ideas.

## 🛠️ Tech Stack
- **CLI:** Typer + Rich
- **Language:** Python 3.11+
- **Database:** SQLAlchemy (SQLite for local, Postgres for production)
- **AI:** GLM-4.7 (Primary), Groq (Filtering), Ollama (Local)
- **Scrapers:** PRAW (Reddit)

## 🏗️ Architectural Rules
1. **Provider Pattern:** All external services (LLMs, Scrapers, Storage) must be abstracted into `Provider` interfaces.
2. **Decoupling:** The Core Logic (Discovery, Validation) must not depend on the CLI or OpenClaw Skill layer.
3. **Local First:** All data must be stored in `~/.founder_copilot/` by default.
4. **Error Handling:** Use the Circuit Breaker pattern for all API calls (Reddit, Groq).
5. **Types:** Use strict Python type hinting throughout.

## 📜 Coding Standards
- Follow PEP 8.
- Use `pydantic` for configuration and data schemas.
- Comprehensive docstrings for all Provider methods.
- Atomic commits with clear messages.

## 🤖 OpenClaw Integration
- The OpenClaw Skill must only be a wrapper that calls the CLI tool.
- No business logic inside the skill file.
