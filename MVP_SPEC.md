# OpenClaw Founder Co-Pilot: Technical Specification
**Version:** 2.0  
**Codename:** `founder-copilot`  
**Author:** Technical Architecture Team  
**Date:** 2026-02-01  
**Status:** Draft

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Architectural Overview](#2-architectural-overview)
3. [Component 1: Standalone CLI Tool](#3-component-1-standalone-cli-tool)
4. [Component 2: Provider System](#4-component-2-provider-system)
5. [Component 3: OpenClaw Skill Wrapper](#5-component-3-openclaw-skill-wrapper)
6. [Data Schemas](#6-data-schemas)
7. [Configuration & Environment](#7-configuration--environment)
8. [Development Roadmap](#8-development-roadmap)
9. [Appendices](#9-appendices)

---

## 1. Executive Summary

### 1.1 Project Vision
**OpenClaw Founder Co-Pilot** is an open-source, local-first toolkit for the complete founder journey: Idea Discovery, Validation, Competitor Monitoring, and Lead Generation. It is designed with a clear separation between:

| Layer | Description |
|-------|-------------|
| **Standalone CLI** | A fully functional Python CLI tool that runs independently in any terminal |
| **Provider System** | Swappable backends for scrapers, LLMs, and databases |
| **OpenClaw Skill** | An optional wrapper that lets an OpenClaw agent orchestrate the CLI |

### 1.2 Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Local-First** | All data stored locally by default (SQLite); zero external dependencies required |
| **Privacy-Centric** | Credentials stored in `.env` files; no data leaves the machine unless explicitly configured |
| **Zero-Cost Default** | Works entirely offline with local LLMs; cloud APIs are optional enhancements |
| **Decoupled Providers** | Every service (scraper, LLM, database) implements a common interface |
| **CLI Independence** | The CLI tool must work WITHOUT the OpenClaw agent; the Skill is an enhancement layer |

### 1.3 Boundary Definition: Standalone vs Skill

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BOUNDARY DIAGRAM                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                    STANDALONE LAYER (Works Independently)                   │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                         CLI Binary (copilot)                          │  │ │
│  │  │                                                                        │  │ │
│  │  │  $ copilot discover --subreddits saas,startups --limit 50             │  │ │
│  │  │  $ copilot validate --idea "AI writing tool" --depth deep             │  │ │
│  │  │  $ copilot monitor --competitors "notion,roam" --interval 24h         │  │ │
│  │  │  $ copilot leads --keywords "looking for,recommend" --alert email     │  │ │
│  │  │                                                                        │  │ │
│  │  └────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                    │                                         │ │
│  │                                    │ Python API                              │ │
│  │                                    ▼                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                         Core Engine                                    │  │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │ │
│  │  │  │ Discovery  │  │ Validation │  │  Monitor   │  │  Lead Engine   │  │  │ │
│  │  │  │  Module    │  │   Module   │  │   Module   │  │    Module      │  │  │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  │                                    │                                         │ │
│  │                                    │ Provider Interface                      │ │
│  │                                    ▼                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                      Provider Layer (Swappable)                        │  │ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                       │  │ │
│  │  │  │  Scrapers  │  │    LLMs    │  │  Databases │                       │  │ │
│  │  │  │ PRAW/Scrapy│  │ Groq/Ollama│  │SQLite/PG   │                       │  │ │
│  │  │  └────────────┘  └────────────┘  └────────────┘                       │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
│  ════════════════════════════════════════════════════════════════════════════   │
│                              INTEGRATION BOUNDARY                                │
│  ════════════════════════════════════════════════════════════════════════════   │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                    SKILL LAYER (OpenClaw Enhancement)                       │ │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    OpenClaw Skill: founder-copilot                     │  │ │
│  │  │                                                                        │  │ │
│  │  │  • Guides users through CLI setup via natural language                │  │ │
│  │  │  • Manages cron jobs for scheduled execution                          │  │ │
│  │  │  • Interprets results and provides actionable insights                │  │ │
│  │  │  • Orchestrates multi-step founder workflows                          │  │ │
│  │  │                                                                        │  │ │
│  │  └──────────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architectural Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        OPENCLAW FOUNDER CO-PILOT ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                              ┌──────────────────┐                                │
│                              │   User Terminal  │                                │
│                              │   or OpenClaw    │                                │
│                              │     Agent        │                                │
│                              └────────┬─────────┘                                │
│                                       │                                          │
│                          ┌────────────┴────────────┐                             │
│                          │                         │                             │
│                          ▼                         ▼                             │
│               ┌──────────────────┐      ┌──────────────────┐                    │
│               │   CLI Interface  │      │  OpenClaw Skill  │                    │
│               │   (copilot)      │      │  (wrapper)       │                    │
│               └────────┬─────────┘      └────────┬─────────┘                    │
│                        │                         │                               │
│                        └───────────┬─────────────┘                               │
│                                    │                                             │
│                                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                           CORE ENGINE                                     │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │    │
│  │  │                        Module Registry                               │ │    │
│  │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐   │ │    │
│  │  │  │ discovery  │ │ validation │ │  monitor   │ │    leads       │   │ │    │
│  │  │  └────────────┘ └────────────┘ └────────────┘ └────────────────┘   │ │    │
│  │  └─────────────────────────────────────────────────────────────────────┘ │    │
│  │                                    │                                       │    │
│  │                                    ▼                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────────────┐ │    │
│  │  │                      Provider Manager                                │ │    │
│  │  │                                                                       │ │    │
│  │  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │ │    │
│  │  │  │ ScraperProvider │  │   LLMProvider   │  │ StorageProvider │      │ │    │
│  │  │  │   Interface     │  │    Interface    │  │    Interface    │      │ │    │
│  │  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │ │    │
│  │  │           │                    │                    │                │ │    │
│  │  │     ┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐         │ │    │
│  │  │     ▼           ▼        ▼           ▼        ▼           ▼         │ │    │
│  │  │  ┌──────┐  ┌────────┐ ┌──────┐  ┌────────┐ ┌────────┐ ┌────────┐   │ │    │
│  │  │  │ PRAW │  │ Scrapy │ │ Groq │  │ Ollama │ │ SQLite │ │Postgres│   │ │    │
│  │  │  └──────┘  └────────┘ └──────┘  └────────┘ └────────┘ └────────┘   │ │    │
│  │  └─────────────────────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **CLI Framework** | Typer + Rich | Modern Python CLI with beautiful output |
| **Core Engine** | Python 3.11+ | Type hints, async support, dataclasses |
| **Default Scraper** | PRAW | Official Reddit API, well-documented |
| **Alt Scraper** | Scrapy | For Hacker News, IndieHackers, Twitter |
| **Default LLM** | Ollama (local) | Zero-cost, privacy-first, offline capable |
| **Alt LLM** | Groq API | 14,400 req/day free, ultra-fast inference |
| **Default Storage** | SQLite | Zero setup, single file, portable |
| **Alt Storage** | PostgreSQL | For scaling, multi-user, production |
| **Config** | TOML + .env | Human-readable config, secure secrets |
| **Scheduling** | System cron | Native OS scheduler, no dependencies |

---

## 3. Component 1: Standalone CLI Tool

### 3.1 Installation

```bash
# From PyPI (planned)
pip install openclaw-copilot

# From source
git clone https://github.com/openclaw/founder-copilot.git
cd founder-copilot
pip install -e .

# Verify installation
copilot --version
copilot --help
```

### 3.2 Command Structure

```
copilot
├── init                    # Initialize configuration
│   ├── --provider          # Configure specific provider
│   └── --minimal           # Skip optional providers
│
├── discover                # Idea Discovery Module
│   ├── --subreddits        # Comma-separated subreddit list
│   ├── --sources           # reddit,hackernews,indiehackers
│   ├── --keywords          # Filter keywords
│   ├── --limit             # Posts per source (default: 100)
│   ├── --min-score         # Minimum pain score threshold
│   └── --output            # json,table,markdown
│
├── validate                # Idea Validation Module
│   ├── --idea              # Idea description to validate
│   ├── --depth             # quick,standard,deep
│   ├── --competitors       # Include competitor analysis
│   └── --report            # Generate validation report
│
├── monitor                 # Competitor Monitoring Module
│   ├── --competitors       # Comma-separated competitor names
│   ├── --track             # mentions,pricing,features,all
│   ├── --interval          # Check interval (e.g., 24h, 7d)
│   └── --alert             # Alert method: email,webhook,none
│
├── leads                   # Lead Generation Module
│   ├── --keywords          # Intent keywords to match
│   ├── --subreddits        # Target subreddits
│   ├── --min-intent        # Minimum intent score (0-1)
│   ├── --realtime          # Enable real-time monitoring
│   └── --notify            # Notification method
│
├── config                  # Configuration Management
│   ├── show                # Display current config
│   ├── set <key> <value>   # Set config value
│   ├── providers           # List available providers
│   └── test                # Test provider connections
│
├── db                      # Database Operations
│   ├── migrate             # Run migrations
│   ├── export              # Export data to JSON/CSV
│   ├── import              # Import from backup
│   └── stats               # Show database statistics
│
└── schedule                # Cron Job Management
    ├── add                 # Add scheduled job
    ├── list                # List scheduled jobs
    ├── remove              # Remove scheduled job
    └── run                 # Run scheduled jobs manually
```

### 3.3 CLI Implementation

```python
# copilot/cli/main.py
import typer
from rich.console import Console
from rich.table import Table
from typing import Optional, List
from enum import Enum

app = typer.Typer(
    name="copilot",
    help="OpenClaw Founder Co-Pilot: Your AI-powered founder journey assistant",
    add_completion=True
)

console = Console()

class OutputFormat(str, Enum):
    json = "json"
    table = "table"
    markdown = "markdown"

class ValidationDepth(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"

@app.command()
def init(
    provider: Optional[str] = typer.Option(None, help="Configure specific provider"),
    minimal: bool = typer.Option(False, help="Skip optional providers")
):
    """Initialize copilot configuration and providers."""
    from copilot.core.config import ConfigManager
    from copilot.core.setup import SetupWizard
    
    config = ConfigManager()
    wizard = SetupWizard(config)
    
    if minimal:
        wizard.minimal_setup()
    elif provider:
        wizard.setup_provider(provider)
    else:
        wizard.interactive_setup()
    
    console.print("[green]Configuration complete![/green]")

@app.command()
def discover(
    subreddits: str = typer.Option("saas,startups,entrepreneur", help="Comma-separated subreddits"),
    sources: str = typer.Option("reddit", help="Data sources: reddit,hackernews,indiehackers"),
    keywords: Optional[str] = typer.Option(None, help="Filter keywords"),
    limit: int = typer.Option(100, help="Posts per source"),
    min_score: float = typer.Option(0.5, help="Minimum pain score"),
    output: OutputFormat = typer.Option(OutputFormat.table, help="Output format")
):
    """
    Discover business opportunities from pain points across communities.
    
    Example:
        copilot discover --subreddits saas,startups --limit 50 --min-score 0.7
    """
    from copilot.modules.discovery import DiscoveryModule
    from copilot.core.engine import Engine
    
    engine = Engine.from_config()
    discovery = DiscoveryModule(engine)
    
    with console.status("[bold blue]Discovering opportunities..."):
        results = discovery.run(
            subreddits=subreddits.split(","),
            sources=sources.split(","),
            keywords=keywords.split(",") if keywords else None,
            limit=limit,
            min_score=min_score
        )
    
    _output_results(results, output, "discovery")

@app.command()
def validate(
    idea: str = typer.Argument(..., help="Idea description to validate"),
    depth: ValidationDepth = typer.Option(ValidationDepth.standard, help="Validation depth"),
    competitors: bool = typer.Option(True, help="Include competitor analysis"),
    report: bool = typer.Option(False, help="Generate detailed report")
):
    """
    Validate a business idea with market research and competitor analysis.
    
    Example:
        copilot validate "AI-powered code review tool" --depth deep --report
    """
    from copilot.modules.validation import ValidationModule
    from copilot.core.engine import Engine
    
    engine = Engine.from_config()
    validator = ValidationModule(engine)
    
    with console.status(f"[bold blue]Validating idea ({depth.value} analysis)..."):
        result = validator.run(
            idea=idea,
            depth=depth.value,
            include_competitors=competitors
        )
    
    if report:
        validator.generate_report(result)
    else:
        _display_validation_result(result)

@app.command()
def monitor(
    competitors: str = typer.Argument(..., help="Comma-separated competitor names"),
    track: str = typer.Option("all", help="Track: mentions,pricing,features,all"),
    interval: str = typer.Option("24h", help="Check interval"),
    alert: str = typer.Option("none", help="Alert method: email,webhook,none")
):
    """
    Monitor competitors for mentions, pricing changes, and feature updates.
    
    Example:
        copilot monitor "notion,roam,obsidian" --track mentions --alert email
    """
    from copilot.modules.monitor import MonitorModule
    from copilot.core.engine import Engine
    
    engine = Engine.from_config()
    monitor_mod = MonitorModule(engine)
    
    result = monitor_mod.run(
        competitors=competitors.split(","),
        track_types=track.split(",") if track != "all" else ["mentions", "pricing", "features"],
        interval=interval,
        alert_method=alert
    )
    
    _display_monitor_result(result)

@app.command()
def leads(
    keywords: str = typer.Option("looking for,recommend,alternative to", help="Intent keywords"),
    subreddits: str = typer.Option("saas,startups", help="Target subreddits"),
    min_intent: float = typer.Option(0.6, help="Minimum intent score"),
    realtime: bool = typer.Option(False, help="Enable real-time monitoring"),
    notify: str = typer.Option("none", help="Notification: email,webhook,desktop,none")
):
    """
    Find high-intent leads actively seeking solutions.
    
    Example:
        copilot leads --keywords "need a tool,anyone know" --min-intent 0.8 --notify desktop
    """
    from copilot.modules.leads import LeadsModule
    from copilot.core.engine import Engine
    
    engine = Engine.from_config()
    leads_mod = LeadsModule(engine)
    
    if realtime:
        console.print("[yellow]Starting real-time lead monitoring (Ctrl+C to stop)...[/yellow]")
        leads_mod.stream(
            keywords=keywords.split(","),
            subreddits=subreddits.split(","),
            min_intent=min_intent,
            notify_method=notify
        )
    else:
        result = leads_mod.run(
            keywords=keywords.split(","),
            subreddits=subreddits.split(","),
            min_intent=min_intent
        )
        _display_leads_result(result)

def _output_results(results, format: OutputFormat, module: str):
    """Format and display results based on output type."""
    if format == OutputFormat.json:
        import json
        console.print_json(json.dumps(results, default=str))
    elif format == OutputFormat.table:
        _display_as_table(results, module)
    else:
        _display_as_markdown(results, module)

def _display_as_table(results, module: str):
    """Display results as a rich table."""
    table = Table(title=f"{module.title()} Results")
    
    if module == "discovery":
        table.add_column("Score", style="cyan", width=8)
        table.add_column("Title", style="white", width=50)
        table.add_column("Source", style="green", width=12)
        table.add_column("Engagement", style="yellow", width=12)
        
        for item in results.get("opportunities", []):
            table.add_row(
                f"{item['pain_score']:.2f}",
                item['title'][:50],
                item['source'],
                f"{item['upvotes']}↑ {item['comments']}💬"
            )
    
    console.print(table)

if __name__ == "__main__":
    app()
```

### 3.4 Example Workflows

#### Workflow 1: Full Founder Journey (CLI Only)

```bash
# Step 1: Initialize
copilot init

# Step 2: Discover opportunities
copilot discover --subreddits saas,startups,entrepreneur --min-score 0.7 --output json > opportunities.json

# Step 3: Validate top idea
copilot validate "AI-powered invoice reconciliation for SMBs" --depth deep --report

# Step 4: Set up competitor monitoring
copilot monitor "bill.com,melio,ramp" --track all --interval 24h --alert email

# Step 5: Start lead monitoring
copilot leads --keywords "invoice,accounting,bookkeeping" --min-intent 0.7 --notify desktop
```

#### Workflow 2: Scheduled Discovery Pipeline

```bash
# Add daily discovery job
copilot schedule add "discover-daily" \
    --command "copilot discover --min-score 0.6 --output json" \
    --cron "0 8 * * *" \
    --output-dir "./reports"

# Add weekly validation digest
copilot schedule add "validate-weekly" \
    --command "copilot validate --from-top-discoveries 5 --report" \
    --cron "0 9 * * 1"

# List scheduled jobs
copilot schedule list
```

---

## 4. Component 2: Provider System

### 4.1 Provider Interface Definitions

```python
# copilot/providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime

# ============================================================================
# SCRAPER PROVIDER INTERFACE
# ============================================================================

@dataclass
class ScrapedPost:
    """Unified post representation across all sources."""
    id: str
    source: str  # reddit, hackernews, indiehackers
    title: str
    body: Optional[str]
    author: str
    url: str
    upvotes: int
    comments_count: int
    created_at: datetime
    subreddit: Optional[str] = None  # Reddit-specific
    metadata: Dict[str, Any] = None

class ScraperProvider(ABC):
    """Abstract base class for all scraper implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'praw', 'scrapy')."""
        pass
    
    @property
    @abstractmethod
    def supported_sources(self) -> List[str]:
        """List of supported data sources."""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the provider with credentials and settings."""
        pass
    
    @abstractmethod
    def scrape(
        self,
        source: str,
        target: str,  # subreddit name, HN category, etc.
        limit: int = 100,
        **kwargs
    ) -> List[ScrapedPost]:
        """Scrape posts from a source."""
        pass
    
    @abstractmethod
    async def scrape_async(
        self,
        source: str,
        target: str,
        limit: int = 100,
        **kwargs
    ) -> List[ScrapedPost]:
        """Async version of scrape."""
        pass
    
    @abstractmethod
    def stream(
        self,
        source: str,
        target: str,
        **kwargs
    ) -> AsyncIterator[ScrapedPost]:
        """Stream posts in real-time (if supported)."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Verify provider is configured and accessible."""
        pass


# ============================================================================
# LLM PROVIDER INTERFACE
# ============================================================================

@dataclass
class LLMResponse:
    """Unified LLM response representation."""
    content: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    raw_response: Optional[Dict[str, Any]] = None

@dataclass
class ClassificationResult:
    """Result from classification tasks."""
    label: str
    confidence: float
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = None

class LLMProvider(ABC):
    """Abstract base class for all LLM implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'groq', 'ollama', 'openai')."""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """List of supported model names."""
        pass
    
    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider runs locally (privacy-first)."""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the provider with API keys and settings."""
        pass
    
    @abstractmethod
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion for the given prompt."""
        pass
    
    @abstractmethod
    async def complete_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Async version of complete."""
        pass
    
    @abstractmethod
    def classify(
        self,
        text: str,
        categories: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ClassificationResult:
        """Classify text into one of the given categories."""
        pass
    
    @abstractmethod
    def extract_json(
        self,
        text: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract structured JSON from text according to schema."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Verify provider is configured and accessible."""
        pass


# ============================================================================
# STORAGE PROVIDER INTERFACE
# ============================================================================

@dataclass
class QueryResult:
    """Result from database queries."""
    rows: List[Dict[str, Any]]
    count: int
    metadata: Optional[Dict[str, Any]] = None

class StorageProvider(ABC):
    """Abstract base class for all storage implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'sqlite', 'postgres')."""
        pass
    
    @property
    @abstractmethod
    def is_persistent(self) -> bool:
        """Whether data persists across sessions."""
        pass
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the provider with connection details."""
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize database schema (run migrations)."""
        pass
    
    @abstractmethod
    def store_posts(self, posts: List[ScrapedPost]) -> int:
        """Store scraped posts, returning number of new posts."""
        pass
    
    @abstractmethod
    def store_analysis(
        self,
        post_id: str,
        analysis_type: str,
        result: Dict[str, Any]
    ) -> None:
        """Store analysis results for a post."""
        pass
    
    @abstractmethod
    def query_posts(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> QueryResult:
        """Query posts with optional filters."""
        pass
    
    @abstractmethod
    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a single post by ID."""
        pass
    
    @abstractmethod
    def export(self, format: str = "json") -> str:
        """Export all data to the specified format."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Verify provider is configured and accessible."""
        pass
```

### 4.2 Provider Implementations

#### 4.2.1 PRAW Scraper (Reddit)

```python
# copilot/providers/scrapers/praw_scraper.py
import praw
from datetime import datetime, timezone
from typing import List, Dict, Any, AsyncIterator, Optional
import asyncio
from ..base import ScraperProvider, ScrapedPost

class PRAWScraper(ScraperProvider):
    """Reddit scraper using PRAW (Python Reddit API Wrapper)."""
    
    def __init__(self):
        self._reddit: Optional[praw.Reddit] = None
        self._config: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "praw"
    
    @property
    def supported_sources(self) -> List[str]:
        return ["reddit"]
    
    def configure(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._reddit = praw.Reddit(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            user_agent=config.get("user_agent", "OpenClawCopilot/1.0")
        )
    
    def scrape(
        self,
        source: str,
        target: str,
        limit: int = 100,
        sort: str = "new",
        min_upvotes: int = 1,
        **kwargs
    ) -> List[ScrapedPost]:
        if source != "reddit":
            raise ValueError(f"PRAW only supports Reddit, not {source}")
        
        subreddit = self._reddit.subreddit(target)
        posts = []
        
        # Get posts based on sort method
        if sort == "new":
            submissions = subreddit.new(limit=limit)
        elif sort == "hot":
            submissions = subreddit.hot(limit=limit)
        elif sort == "top":
            submissions = subreddit.top(limit=limit, time_filter=kwargs.get("time_filter", "week"))
        else:
            submissions = subreddit.new(limit=limit)
        
        for submission in submissions:
            if submission.score < min_upvotes:
                continue
            if submission.removed_by_category or submission.selftext == "[removed]":
                continue
            
            posts.append(ScrapedPost(
                id=submission.fullname,
                source="reddit",
                title=submission.title,
                body=submission.selftext if submission.is_self else None,
                author=str(submission.author) if submission.author else "[deleted]",
                url=f"https://reddit.com{submission.permalink}",
                upvotes=submission.score,
                comments_count=submission.num_comments,
                created_at=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                subreddit=target,
                metadata={
                    "upvote_ratio": submission.upvote_ratio,
                    "flair": submission.link_flair_text,
                    "is_self": submission.is_self
                }
            ))
        
        return posts
    
    async def scrape_async(
        self,
        source: str,
        target: str,
        limit: int = 100,
        **kwargs
    ) -> List[ScrapedPost]:
        # PRAW is synchronous, run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.scrape(source, target, limit, **kwargs)
        )
    
    async def stream(
        self,
        source: str,
        target: str,
        **kwargs
    ) -> AsyncIterator[ScrapedPost]:
        if source != "reddit":
            raise ValueError(f"PRAW only supports Reddit, not {source}")
        
        subreddit = self._reddit.subreddit(target)
        
        for submission in subreddit.stream.submissions(skip_existing=True):
            yield ScrapedPost(
                id=submission.fullname,
                source="reddit",
                title=submission.title,
                body=submission.selftext if submission.is_self else None,
                author=str(submission.author) if submission.author else "[deleted]",
                url=f"https://reddit.com{submission.permalink}",
                upvotes=submission.score,
                comments_count=submission.num_comments,
                created_at=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                subreddit=target,
                metadata={"upvote_ratio": submission.upvote_ratio}
            )
    
    def health_check(self) -> bool:
        try:
            self._reddit.user.me()
            return True
        except Exception:
            # Read-only mode doesn't require auth
            try:
                list(self._reddit.subreddit("test").new(limit=1))
                return True
            except Exception:
                return False
```

#### 4.2.2 Ollama LLM Provider (Local)

```python
# copilot/providers/llms/ollama_provider.py
import requests
import json
from typing import List, Dict, Any, Optional
from ..base import LLMProvider, LLMResponse, ClassificationResult

class OllamaProvider(LLMProvider):
    """Local LLM provider using Ollama."""
    
    def __init__(self):
        self._base_url: str = "http://localhost:11434"
        self._default_model: str = "llama3.2"
        self._config: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "ollama"
    
    @property
    def supported_models(self) -> List[str]:
        return ["llama3.2", "llama3.1", "mistral", "mixtral", "phi3", "gemma2"]
    
    @property
    def is_local(self) -> bool:
        return True
    
    def configure(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._base_url = config.get("base_url", "http://localhost:11434")
        self._default_model = config.get("default_model", "llama3.2")
    
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        model = model or self._default_model
        
        response = requests.post(
            f"{self._base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["response"],
            model=model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            },
            raw_response=data
        )
    
    async def complete_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        import aiohttp
        model = model or self._default_model
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": kwargs.get("temperature", 0.1)}
                }
            ) as response:
                data = await response.json()
                return LLMResponse(
                    content=data["response"],
                    model=model,
                    usage={"total_tokens": data.get("eval_count", 0)},
                    raw_response=data
                )
    
    def classify(
        self,
        text: str,
        categories: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ClassificationResult:
        prompt = f"""Classify the following text into exactly ONE of these categories: {', '.join(categories)}

Text: {text}

Respond with ONLY a JSON object:
{{"category": "<category>", "confidence": 0.0-1.0, "reasoning": "<brief explanation>"}}"""
        
        response = self.complete(prompt, model=model, temperature=0.1)
        
        try:
            result = json.loads(response.content)
            return ClassificationResult(
                label=result["category"],
                confidence=float(result["confidence"]),
                reasoning=result.get("reasoning"),
                metadata={"raw_response": response.raw_response}
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback: try to extract category from text
            for cat in categories:
                if cat.lower() in response.content.lower():
                    return ClassificationResult(
                        label=cat,
                        confidence=0.5,
                        reasoning="Extracted from unstructured response"
                    )
            return ClassificationResult(
                label=categories[0],
                confidence=0.0,
                reasoning="Failed to parse response"
            )
    
    def extract_json(
        self,
        text: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        schema_str = json.dumps(schema, indent=2)
        prompt = f"""Extract information from the following text and return it as JSON matching this schema:

Schema:
{schema_str}

Text:
{text}

Respond with ONLY the JSON object, no explanation."""
        
        response = self.complete(prompt, model=model, temperature=0.1)
        
        # Try to parse JSON from response
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        return json.loads(content)
    
    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self._base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
```

#### 4.2.3 Groq LLM Provider (Cloud)

```python
# copilot/providers/llms/groq_provider.py
from groq import Groq
import json
from typing import List, Dict, Any, Optional
from ..base import LLMProvider, LLMResponse, ClassificationResult

class GroqProvider(LLMProvider):
    """Cloud LLM provider using Groq API."""
    
    def __init__(self):
        self._client: Optional[Groq] = None
        self._default_model: str = "llama-3.3-70b-versatile"
        self._config: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "groq"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
    
    @property
    def is_local(self) -> bool:
        return False
    
    def configure(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._client = Groq(api_key=config["api_key"])
        self._default_model = config.get("default_model", "llama-3.3-70b-versatile")
    
    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        **kwargs
    ) -> LLMResponse:
        model = model or self._default_model
        
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            raw_response=response.model_dump()
        )
    
    async def complete_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        # Groq client is synchronous, use thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.complete(prompt, model, **kwargs)
        )
    
    def classify(
        self,
        text: str,
        categories: List[str],
        model: Optional[str] = None,
        **kwargs
    ) -> ClassificationResult:
        prompt = f"""Classify the following text into exactly ONE of these categories: {', '.join(categories)}

Text: {text}

Respond with ONLY a JSON object:
{{"category": "<category>", "confidence": 0.0-1.0, "reasoning": "<brief explanation>"}}"""
        
        response = self.complete(prompt, model=model, temperature=0.1)
        result = json.loads(response.content)
        
        return ClassificationResult(
            label=result["category"],
            confidence=float(result["confidence"]),
            reasoning=result.get("reasoning"),
            metadata={"raw_response": response.raw_response}
        )
    
    def extract_json(
        self,
        text: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        schema_str = json.dumps(schema, indent=2)
        prompt = f"""Extract information from the following text and return it as JSON matching this schema:

Schema:
{schema_str}

Text:
{text}

Respond with ONLY the JSON object, no explanation."""
        
        response = self.complete(prompt, model=model, temperature=0.1)
        return json.loads(response.content)
    
    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
```

#### 4.2.4 SQLite Storage Provider

```python
# copilot/providers/storage/sqlite_provider.py
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..base import StorageProvider, ScrapedPost, QueryResult

class SQLiteProvider(StorageProvider):
    """Local SQLite storage provider."""
    
    def __init__(self):
        self._db_path: Path = Path.home() / ".copilot" / "data.db"
        self._conn: Optional[sqlite3.Connection] = None
    
    @property
    def name(self) -> str:
        return "sqlite"
    
    @property
    def is_persistent(self) -> bool:
        return True
    
    def configure(self, config: Dict[str, Any]) -> None:
        if "db_path" in config:
            self._db_path = Path(config["db_path"])
        
        # Ensure directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect with row factory for dict results
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
    
    def initialize(self) -> None:
        """Create database schema."""
        schema = """
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            author TEXT,
            url TEXT,
            upvotes INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            subreddit TEXT,
            metadata JSON,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            result JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
        
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            pain_score REAL,
            engagement_score REAL,
            validation_score REAL,
            composite_score REAL,
            signal_type TEXT,
            keywords JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
        
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            domain TEXT,
            tracking_config JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS competitor_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            post_id TEXT,
            mention_type TEXT,
            sentiment REAL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
        CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit);
        CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_analyses_post ON analyses(post_id);
        CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(composite_score DESC);
        """
        
        self._conn.executescript(schema)
        self._conn.commit()
    
    def store_posts(self, posts: List[ScrapedPost]) -> int:
        """Store posts, return count of new posts."""
        cursor = self._conn.cursor()
        new_count = 0
        
        for post in posts:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO posts 
                    (id, source, title, body, author, url, upvotes, comments_count, created_at, subreddit, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post.id,
                    post.source,
                    post.title,
                    post.body,
                    post.author,
                    post.url,
                    post.upvotes,
                    post.comments_count,
                    post.created_at.isoformat() if post.created_at else None,
                    post.subreddit,
                    json.dumps(post.metadata) if post.metadata else None
                ))
                if cursor.rowcount > 0:
                    new_count += 1
            except sqlite3.IntegrityError:
                pass
        
        self._conn.commit()
        return new_count
    
    def store_analysis(
        self,
        post_id: str,
        analysis_type: str,
        result: Dict[str, Any]
    ) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO analyses (post_id, analysis_type, result)
            VALUES (?, ?, ?)
        """, (post_id, analysis_type, json.dumps(result)))
        self._conn.commit()
    
    def query_posts(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> QueryResult:
        query = "SELECT * FROM posts"
        params = []
        
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    placeholders = ",".join("?" * len(value))
                    conditions.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        if order_by:
            query += f" ORDER BY {order_by}"
        else:
            query += " ORDER BY created_at DESC"
        
        query += f" LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM posts"
        if filters:
            count_query += " WHERE " + " AND ".join(
                f"{k} = ?" if not isinstance(v, list) else f"{k} IN ({','.join('?' * len(v))})"
                for k, v in filters.items()
            )
        cursor.execute(count_query, [v for k, v in (filters or {}).items() for v in ([v] if not isinstance(v, list) else v)])
        total = cursor.fetchone()[0]
        
        return QueryResult(rows=rows, count=total)
    
    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def export(self, format: str = "json") -> str:
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM posts")
        posts = [dict(row) for row in cursor.fetchall()]
        
        if format == "json":
            return json.dumps(posts, indent=2, default=str)
        elif format == "csv":
            import csv
            import io
            output = io.StringIO()
            if posts:
                writer = csv.DictWriter(output, fieldnames=posts[0].keys())
                writer.writeheader()
                writer.writerows(posts)
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def health_check(self) -> bool:
        try:
            self._conn.execute("SELECT 1")
            return True
        except Exception:
            return False
```

### 4.3 Provider Registry

```python
# copilot/providers/registry.py
from typing import Dict, Type, Optional
from .base import ScraperProvider, LLMProvider, StorageProvider

class ProviderRegistry:
    """Central registry for all providers."""
    
    _scrapers: Dict[str, Type[ScraperProvider]] = {}
    _llms: Dict[str, Type[LLMProvider]] = {}
    _storage: Dict[str, Type[StorageProvider]] = {}
    
    @classmethod
    def register_scraper(cls, name: str, provider_class: Type[ScraperProvider]):
        cls._scrapers[name] = provider_class
    
    @classmethod
    def register_llm(cls, name: str, provider_class: Type[LLMProvider]):
        cls._llms[name] = provider_class
    
    @classmethod
    def register_storage(cls, name: str, provider_class: Type[StorageProvider]):
        cls._storage[name] = provider_class
    
    @classmethod
    def get_scraper(cls, name: str) -> Optional[Type[ScraperProvider]]:
        return cls._scrapers.get(name)
    
    @classmethod
    def get_llm(cls, name: str) -> Optional[Type[LLMProvider]]:
        return cls._llms.get(name)
    
    @classmethod
    def get_storage(cls, name: str) -> Optional[Type[StorageProvider]]:
        return cls._storage.get(name)
    
    @classmethod
    def list_scrapers(cls) -> Dict[str, Type[ScraperProvider]]:
        return cls._scrapers.copy()
    
    @classmethod
    def list_llms(cls) -> Dict[str, Type[LLMProvider]]:
        return cls._llms.copy()
    
    @classmethod
    def list_storage(cls) -> Dict[str, Type[StorageProvider]]:
        return cls._storage.copy()


# Auto-register built-in providers
def _register_builtins():
    from .scrapers.praw_scraper import PRAWScraper
    from .llms.ollama_provider import OllamaProvider
    from .llms.groq_provider import GroqProvider
    from .storage.sqlite_provider import SQLiteProvider
    
    ProviderRegistry.register_scraper("praw", PRAWScraper)
    ProviderRegistry.register_llm("ollama", OllamaProvider)
    ProviderRegistry.register_llm("groq", GroqProvider)
    ProviderRegistry.register_storage("sqlite", SQLiteProvider)

_register_builtins()
```

---

## 5. Component 3: OpenClaw Skill Wrapper

### 5.1 Skill Definition

The OpenClaw Skill acts as an intelligent wrapper around the CLI tool, enabling natural language interaction and workflow orchestration.

```yaml
# skill.yaml
name: founder-copilot
version: "1.0.0"
description: "AI-powered founder journey assistant: discovery, validation, monitoring, and leads"

triggers:
  - "help me find startup ideas"
  - "discover pain points"
  - "validate my idea"
  - "monitor competitors"
  - "find leads"
  - "founder copilot"

capabilities:
  - name: setup
    description: "Guide user through CLI installation and configuration"
    commands:
      - "copilot init"
      - "copilot config test"
  
  - name: discover
    description: "Find business opportunities from community pain points"
    commands:
      - "copilot discover"
    parameters:
      - subreddits
      - keywords
      - min_score
  
  - name: validate
    description: "Validate a business idea with market research"
    commands:
      - "copilot validate"
    parameters:
      - idea
      - depth
  
  - name: monitor
    description: "Monitor competitors for mentions and updates"
    commands:
      - "copilot monitor"
    parameters:
      - competitors
      - track
      - alert
  
  - name: leads
    description: "Find high-intent leads seeking solutions"
    commands:
      - "copilot leads"
    parameters:
      - keywords
      - min_intent
  
  - name: schedule
    description: "Set up automated scheduled jobs"
    commands:
      - "copilot schedule add"
      - "copilot schedule list"

requirements:
  - python >= 3.11
  - pip package: openclaw-copilot

files:
  - path: "~/.copilot/config.toml"
    purpose: "Configuration file"
  - path: "~/.copilot/data.db"
    purpose: "Local SQLite database"
  - path: "~/.copilot/.env"
    purpose: "API credentials (secrets)"
```

### 5.2 Skill Implementation

```python
# skill/founder_copilot_skill.py
"""
OpenClaw Skill: Founder Co-Pilot

This skill enables an OpenClaw agent to:
1. Guide users through CLI setup
2. Execute founder journey workflows
3. Manage scheduled cron jobs
4. Interpret results and provide insights
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class SkillContext:
    """Context passed to skill functions."""
    working_dir: Path
    config_dir: Path
    env_file: Path
    is_configured: bool
    available_providers: Dict[str, List[str]]

class FounderCopilotSkill:
    """OpenClaw skill wrapper for the Founder Co-Pilot CLI."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".copilot"
        self.env_file = self.config_dir / ".env"
        self.config_file = self.config_dir / "config.toml"
        self.db_file = self.config_dir / "data.db"
    
    # =========================================================================
    # SETUP & CONFIGURATION
    # =========================================================================
    
    def check_installation(self) -> Dict[str, Any]:
        """Check if the CLI tool is installed and configured."""
        result = {
            "cli_installed": False,
            "cli_version": None,
            "config_exists": self.config_file.exists(),
            "env_exists": self.env_file.exists(),
            "db_exists": self.db_file.exists(),
            "providers_configured": {}
        }
        
        # Check CLI installation
        try:
            output = subprocess.run(
                ["copilot", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if output.returncode == 0:
                result["cli_installed"] = True
                result["cli_version"] = output.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check provider configuration
        if result["config_exists"]:
            try:
                output = subprocess.run(
                    ["copilot", "config", "providers"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if output.returncode == 0:
                    result["providers_configured"] = json.loads(output.stdout)
            except Exception:
                pass
        
        return result
    
    def guide_setup(self) -> str:
        """Generate setup instructions based on current state."""
        status = self.check_installation()
        
        instructions = []
        
        if not status["cli_installed"]:
            instructions.append("""
## Step 1: Install the CLI Tool

```bash
pip install openclaw-copilot
```

Or from source:
```bash
git clone https://github.com/openclaw/founder-copilot.git
cd founder-copilot
pip install -e .
```
""")
        
        if not status["config_exists"]:
            instructions.append("""
## Step 2: Initialize Configuration

Run the setup wizard:
```bash
copilot init
```

This will:
- Create ~/.copilot/config.toml
- Guide you through provider selection
- Test connections
""")
        
        if not status["env_exists"]:
            instructions.append("""
## Step 3: Configure API Credentials

Create ~/.copilot/.env with your credentials:

```bash
# Reddit API (required for discovery)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# LLM Provider (choose one)
GROQ_API_KEY=your_groq_key  # For cloud inference
# Or use Ollama (local) - no API key needed

# Optional: Email alerts
RESEND_API_KEY=your_resend_key
ALERT_EMAIL=your@email.com
```
""")
        
        if not instructions:
            return "The Founder Co-Pilot is fully configured and ready to use!"
        
        return "\n".join(instructions)
    
    def run_init(self, minimal: bool = False) -> Dict[str, Any]:
        """Run the CLI init command."""
        cmd = ["copilot", "init"]
        if minimal:
            cmd.append("--minimal")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    def test_providers(self) -> Dict[str, bool]:
        """Test all configured providers."""
        result = subprocess.run(
            ["copilot", "config", "test"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    
    # =========================================================================
    # DISCOVERY MODULE
    # =========================================================================
    
    def discover(
        self,
        subreddits: List[str] = ["saas", "startups", "entrepreneur"],
        keywords: Optional[List[str]] = None,
        limit: int = 100,
        min_score: float = 0.5,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Discover business opportunities from community pain points.
        
        Args:
            subreddits: List of subreddits to scan
            keywords: Optional filter keywords
            limit: Maximum posts per subreddit
            min_score: Minimum pain score threshold
            output_format: Output format (json, table, markdown)
        
        Returns:
            Dictionary with discovered opportunities
        """
        cmd = [
            "copilot", "discover",
            "--subreddits", ",".join(subreddits),
            "--limit", str(limit),
            "--min-score", str(min_score),
            "--output", output_format
        ]
        
        if keywords:
            cmd.extend(["--keywords", ",".join(keywords)])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes for scraping
        )
        
        if result.returncode == 0:
            if output_format == "json":
                return json.loads(result.stdout)
            return {"output": result.stdout, "format": output_format}
        
        return {"error": result.stderr}
    
    def interpret_discovery_results(self, results: Dict[str, Any]) -> str:
        """Provide human-readable insights from discovery results."""
        if "error" in results:
            return f"Discovery failed: {results['error']}"
        
        opportunities = results.get("opportunities", [])
        
        if not opportunities:
            return "No significant opportunities found in this scan. Try adjusting your subreddits or lowering the minimum score threshold."
        
        # Group by signal type
        by_type = {}
        for opp in opportunities:
            signal = opp.get("signal_type", "unknown")
            if signal not in by_type:
                by_type[signal] = []
            by_type[signal].append(opp)
        
        insights = [f"## Discovery Results: {len(opportunities)} Opportunities Found\n"]
        
        # Top opportunities
        top_5 = sorted(opportunities, key=lambda x: x.get("composite_score", 0), reverse=True)[:5]
        insights.append("### Top 5 Opportunities by Score:\n")
        for i, opp in enumerate(top_5, 1):
            insights.append(f"{i}. **{opp['title'][:60]}...** (Score: {opp['composite_score']:.2f})")
            insights.append(f"   - Source: r/{opp.get('subreddit', 'unknown')} | {opp.get('upvotes', 0)} upvotes")
            insights.append(f"   - Signal: {opp.get('signal_type', 'unknown')}")
            insights.append("")
        
        # Signal breakdown
        insights.append("### Signal Type Breakdown:\n")
        for signal, opps in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            insights.append(f"- **{signal}**: {len(opps)} opportunities")
        
        return "\n".join(insights)
    
    # =========================================================================
    # VALIDATION MODULE
    # =========================================================================
    
    def validate(
        self,
        idea: str,
        depth: str = "standard",
        include_competitors: bool = True,
        generate_report: bool = False
    ) -> Dict[str, Any]:
        """
        Validate a business idea with market research.
        
        Args:
            idea: Business idea description
            depth: Validation depth (quick, standard, deep)
            include_competitors: Include competitor analysis
            generate_report: Generate detailed markdown report
        
        Returns:
            Validation results
        """
        cmd = [
            "copilot", "validate",
            idea,
            "--depth", depth
        ]
        
        if include_competitors:
            cmd.append("--competitors")
        if generate_report:
            cmd.append("--report")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for deep validation
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    
    # =========================================================================
    # MONITORING MODULE
    # =========================================================================
    
    def monitor(
        self,
        competitors: List[str],
        track_types: List[str] = ["mentions", "pricing", "features"],
        interval: str = "24h",
        alert_method: str = "none"
    ) -> Dict[str, Any]:
        """
        Set up competitor monitoring.
        
        Args:
            competitors: List of competitor names
            track_types: What to track (mentions, pricing, features)
            interval: Check interval
            alert_method: Alert method (email, webhook, none)
        
        Returns:
            Monitoring configuration result
        """
        cmd = [
            "copilot", "monitor",
            ",".join(competitors),
            "--track", ",".join(track_types),
            "--interval", interval,
            "--alert", alert_method
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    
    # =========================================================================
    # LEADS MODULE
    # =========================================================================
    
    def find_leads(
        self,
        keywords: List[str] = ["looking for", "recommend", "alternative to"],
        subreddits: List[str] = ["saas", "startups"],
        min_intent: float = 0.6
    ) -> Dict[str, Any]:
        """
        Find high-intent leads seeking solutions.
        
        Args:
            keywords: Intent keywords to match
            subreddits: Target subreddits
            min_intent: Minimum intent score
        
        Returns:
            Found leads
        """
        cmd = [
            "copilot", "leads",
            "--keywords", ",".join(keywords),
            "--subreddits", ",".join(subreddits),
            "--min-intent", str(min_intent)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    
    def schedule_job(
        self,
        name: str,
        command: str,
        cron_expression: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a scheduled cron job.
        
        Args:
            name: Job identifier
            command: CLI command to run
            cron_expression: Cron schedule (e.g., "0 8 * * *")
            output_dir: Directory to save output
        
        Returns:
            Schedule result
        """
        cmd = [
            "copilot", "schedule", "add",
            name,
            "--command", command,
            "--cron", cron_expression
        ]
        
        if output_dir:
            cmd.extend(["--output-dir", output_dir])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {"success": True, "job": name, "cron": cron_expression}
        return {"error": result.stderr}
    
    def list_schedules(self) -> Dict[str, Any]:
        """List all scheduled jobs."""
        result = subprocess.run(
            ["copilot", "schedule", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr}
    
    # =========================================================================
    # WORKFLOW ORCHESTRATION
    # =========================================================================
    
    def full_founder_workflow(
        self,
        domain: str,
        subreddits: List[str],
        competitors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run a complete founder journey workflow:
        1. Discover opportunities in target subreddits
        2. Validate top opportunities
        3. Set up competitor monitoring
        4. Start lead tracking
        
        Args:
            domain: Business domain/niche
            subreddits: Target subreddits
            competitors: Known competitors (optional)
        
        Returns:
            Complete workflow results
        """
        results = {
            "domain": domain,
            "steps": {}
        }
        
        # Step 1: Discovery
        discovery = self.discover(
            subreddits=subreddits,
            limit=50,
            min_score=0.6
        )
        results["steps"]["discovery"] = discovery
        
        # Step 2: Validate top opportunity
        if "opportunities" in discovery and discovery["opportunities"]:
            top_idea = discovery["opportunities"][0]["title"]
            validation = self.validate(
                idea=top_idea,
                depth="standard"
            )
            results["steps"]["validation"] = validation
        
        # Step 3: Competitor monitoring
        if competitors:
            monitoring = self.monitor(
                competitors=competitors,
                track_types=["mentions", "features"]
            )
            results["steps"]["monitoring"] = monitoring
        
        # Step 4: Lead tracking
        leads = self.find_leads(
            subreddits=subreddits,
            min_intent=0.7
        )
        results["steps"]["leads"] = leads
        
        return results


# Skill entry point for OpenClaw
def get_skill():
    return FounderCopilotSkill()
```

### 5.3 Agent Interaction Examples

```markdown
## Example Agent Interactions

### Setup Flow
**User:** "I want to use the founder copilot to find startup ideas"

**Agent:** 
Let me check if the Founder Co-Pilot is installed and configured...

*[Runs check_installation()]*

I see the CLI tool isn't installed yet. Here's how to set it up:

1. Install the CLI:
   ```bash
   pip install openclaw-copilot
   ```

2. Initialize configuration:
   ```bash
   copilot init
   ```

3. You'll need a Reddit API key. Would you like me to guide you through getting one?

---

### Discovery Flow
**User:** "Find me pain points in the SaaS and startup communities"

**Agent:**
I'll scan r/saas and r/startups for business opportunities...

*[Runs discover(subreddits=["saas", "startups"], min_score=0.6)]*

## Discovery Results: 23 Opportunities Found

### Top 5 Opportunities by Score:

1. **"Why isn't there a simple invoicing tool that doesn't..."** (Score: 0.87)
   - Source: r/saas | 145 upvotes
   - Signal: wish

2. **"Frustrated with X - it keeps breaking when..."** (Score: 0.82)
   - Source: r/startups | 89 upvotes
   - Signal: frustration

Would you like me to validate any of these ideas or set up monitoring for this space?

---

### Scheduled Workflow
**User:** "Set up daily discovery reports for the AI space"

**Agent:**
I'll configure a daily scheduled job for AI-focused discovery.

*[Runs schedule_job(...)]*

Done! I've set up a daily discovery job:
- **Name:** ai-discovery-daily
- **Schedule:** Every day at 8:00 AM
- **Subreddits:** r/MachineLearning, r/artificial, r/LocalLLaMA
- **Output:** ~/copilot-reports/ai/

The first report will run tomorrow morning. Would you like me to run a quick scan now to preview what you'll get?
```

---

## 6. Data Schemas

### 6.1 Configuration Schema (config.toml)

```toml
# ~/.copilot/config.toml
# OpenClaw Founder Co-Pilot Configuration

[general]
version = "1.0.0"
data_dir = "~/.copilot"
log_level = "INFO"

[providers]
# Active providers (one per category)
scraper = "praw"    # praw, scrapy
llm = "ollama"      # ollama, groq, openai
storage = "sqlite"  # sqlite, postgres

[providers.praw]
user_agent = "OpenClawCopilot/1.0"
# Credentials in .env: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

[providers.ollama]
base_url = "http://localhost:11434"
default_model = "llama3.2"

[providers.groq]
default_model = "llama-3.3-70b-versatile"
# API key in .env: GROQ_API_KEY

[providers.sqlite]
db_path = "~/.copilot/data.db"

[providers.postgres]
# Connection string in .env: DATABASE_URL

[discovery]
default_subreddits = ["saas", "startups", "entrepreneur", "indiehackers"]
default_limit = 100
min_upvotes = 5
include_comments = true
max_comment_depth = 3

[scoring]
# Composite score weights
pain_weight = 0.40
engagement_weight = 0.25
validation_weight = 0.25
recency_weight = 0.10

[alerts]
method = "none"  # none, email, webhook, desktop
# Email config in .env: RESEND_API_KEY, ALERT_EMAIL

[alerts.webhook]
url = ""
headers = {}

[schedule]
cron_dir = "~/.copilot/cron"
output_dir = "~/.copilot/reports"
```

### 6.2 Environment Variables (.env)

```bash
# ~/.copilot/.env
# SECRETS - Never commit this file!

# Reddit API (Required for scraping)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# LLM Providers (Choose one)
GROQ_API_KEY=gsk_xxxxxxxxxxxx        # For Groq cloud
OPENAI_API_KEY=sk-xxxxxxxxxxxx       # For OpenAI (optional)

# Database (Optional - for PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Alerts (Optional)
RESEND_API_KEY=re_xxxxxxxxxxxx
ALERT_EMAIL=your@email.com
ALERT_WEBHOOK_URL=https://your-webhook.com/alerts

# Search (Optional - for competitor research)
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
```

### 6.3 Output Schemas

#### Discovery Output
```json
{
  "scan_id": "uuid",
  "timestamp": "2026-02-01T12:00:00Z",
  "config": {
    "subreddits": ["saas", "startups"],
    "limit": 100,
    "min_score": 0.5
  },
  "stats": {
    "posts_scanned": 200,
    "posts_filtered": 156,
    "opportunities_found": 44
  },
  "opportunities": [
    {
      "id": "t3_abc123",
      "source": "reddit",
      "subreddit": "saas",
      "title": "Why isn't there a simple...",
      "body": "...",
      "author": "user123",
      "url": "https://reddit.com/...",
      "upvotes": 145,
      "comments_count": 67,
      "created_at": "2026-02-01T10:00:00Z",
      "signal_type": "wish",
      "pain_score": 0.85,
      "engagement_score": 0.72,
      "validation_score": 0.68,
      "recency_score": 0.95,
      "composite_score": 0.79,
      "matched_keywords": ["simple", "alternative"],
      "matched_patterns": ["why isn't there"]
    }
  ]
}
```

#### Validation Output
```json
{
  "validation_id": "uuid",
  "timestamp": "2026-02-01T12:00:00Z",
  "idea": "AI-powered invoice reconciliation for SMBs",
  "depth": "deep",
  "scores": {
    "market_demand": 0.78,
    "competition_level": 0.65,
    "feasibility": 0.82,
    "uniqueness": 0.71,
    "overall": 0.74
  },
  "market_analysis": {
    "target_market": "Small and medium businesses",
    "market_size_estimate": "$2.5B",
    "growth_trend": "Growing",
    "pain_points_validated": [
      "Manual reconciliation takes hours",
      "Existing tools too expensive",
      "Poor integration with accounting software"
    ]
  },
  "competitors": [
    {
      "name": "Bill.com",
      "positioning": "Enterprise-focused",
      "pricing": "$45/user/month",
      "strengths": ["Brand recognition", "Integrations"],
      "weaknesses": ["Expensive", "Complex"]
    }
  ],
  "recommendations": [
    "Focus on SMB segment underserved by enterprise tools",
    "Competitive pricing under $20/month",
    "Prioritize QuickBooks/Xero integration"
  ]
}
```

---

## 7. Configuration & Environment

### 7.1 Directory Structure

```
~/.copilot/
├── config.toml          # Main configuration
├── .env                 # API credentials (gitignored)
├── data.db             # SQLite database
├── cron/               # Cron job definitions
│   ├── daily-discovery.json
│   └── weekly-report.json
├── reports/            # Generated reports
│   ├── 2026-02-01/
│   │   ├── discovery.json
│   │   └── validation.md
│   └── ...
├── cache/              # Temporary cache
└── logs/               # Application logs
    └── copilot.log
```

### 7.2 First-Run Setup Flow

```
$ copilot init

╔══════════════════════════════════════════════════════════════╗
║           OpenClaw Founder Co-Pilot Setup Wizard             ║
╚══════════════════════════════════════════════════════════════╝

Step 1/4: Scraper Configuration
─────────────────────────────────
? Select your scraper provider:
  > PRAW (Reddit API) - Recommended
    Scrapy (Multi-source)

? Enter Reddit Client ID: [your_id]
? Enter Reddit Client Secret: [your_secret]
✓ Reddit API connection successful!

Step 2/4: LLM Configuration
─────────────────────────────────
? Select your LLM provider:
  > Ollama (Local) - Free, Privacy-first
    Groq (Cloud) - Fast, Free tier
    OpenAI (Cloud) - Paid

? Is Ollama running locally? [Y/n]
✓ Ollama detected with model: llama3.2

Step 3/4: Storage Configuration
─────────────────────────────────
? Select your storage provider:
  > SQLite (Local) - Recommended
    PostgreSQL (Cloud/Self-hosted)

✓ SQLite database initialized at ~/.copilot/data.db

Step 4/4: Optional Features
─────────────────────────────────
? Enable email alerts? [y/N]
? Enable scheduled jobs? [Y/n]

╔══════════════════════════════════════════════════════════════╗
║                    Setup Complete!                            ║
╠══════════════════════════════════════════════════════════════╣
║  Config: ~/.copilot/config.toml                              ║
║  Secrets: ~/.copilot/.env                                    ║
║  Database: ~/.copilot/data.db                                ║
║                                                               ║
║  Get started:                                                 ║
║    copilot discover --subreddits saas,startups               ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 8. Development Roadmap

### Phase 1: Core Engine (Week 1-2)
**Goal:** Working provider system with basic discovery

| Day | Task | Deliverable |
|-----|------|-------------|
| 1-2 | Provider interfaces | `copilot/providers/base.py` with all ABCs |
| 3-4 | SQLite provider | Working local storage |
| 5-6 | PRAW scraper | Reddit scraping working |
| 7-8 | Ollama LLM provider | Local classification working |
| 9-10 | Core engine | Provider orchestration |
| 11-12 | Discovery module | `copilot discover` functional |
| 13-14 | Tests & docs | 80% test coverage |

**Milestone:** `copilot discover --subreddits saas --output json` works end-to-end

### Phase 2: CLI Interface (Week 3)
**Goal:** Full CLI with all commands

| Day | Task | Deliverable |
|-----|------|-------------|
| 15-16 | Typer CLI scaffold | All commands stubbed |
| 17-18 | Validation module | `copilot validate` working |
| 19 | Monitor module | `copilot monitor` working |
| 20 | Leads module | `copilot leads` working |
| 21 | Config command | `copilot config` working |

**Milestone:** All CLI commands functional, PyPI package published

### Phase 3: OpenClaw Skill (Week 4)
**Goal:** Agent integration complete

| Day | Task | Deliverable |
|-----|------|-------------|
| 22-23 | Skill definition | `skill.yaml` complete |
| 24-25 | Skill implementation | Python wrapper complete |
| 26 | Agent interaction tests | Integration tests |
| 27 | Schedule/cron integration | `copilot schedule` working |
| 28 | Documentation | README, examples, tutorials |

**Milestone:** OpenClaw agent can run full founder workflow

### Phase 4: Polish & Launch (Week 5)
**Goal:** Production-ready release

| Day | Task | Deliverable |
|-----|------|-------------|
| 29-30 | Groq provider | Cloud LLM option |
| 31-32 | PostgreSQL provider | Scalable storage option |
| 33-34 | Alert system | Email/webhook alerts |
| 35 | Final testing | Full integration tests |

**Milestone:** v1.0.0 release

---

## 9. Appendices

### 9.1 API Reference Summary

| Command | Description | Key Options |
|---------|-------------|-------------|
| `copilot init` | Setup wizard | `--minimal`, `--provider` |
| `copilot discover` | Find opportunities | `--subreddits`, `--min-score`, `--output` |
| `copilot validate` | Validate idea | `--depth`, `--competitors`, `--report` |
| `copilot monitor` | Track competitors | `--track`, `--interval`, `--alert` |
| `copilot leads` | Find leads | `--keywords`, `--min-intent`, `--notify` |
| `copilot config` | Manage config | `show`, `set`, `test` |
| `copilot schedule` | Manage cron jobs | `add`, `list`, `remove` |
| `copilot db` | Database ops | `migrate`, `export`, `stats` |

### 9.2 Provider Comparison

| Provider | Type | Cost | Privacy | Setup |
|----------|------|------|---------|-------|
| PRAW | Scraper | Free | Moderate | API keys required |
| Scrapy | Scraper | Free | High | Complex config |
| Ollama | LLM | Free | High (local) | Install Ollama |
| Groq | LLM | Free tier | Low (cloud) | API key required |
| SQLite | Storage | Free | High (local) | Zero config |
| PostgreSQL | Storage | Varies | Configurable | Database setup |

### 9.3 Glossary

| Term | Definition |
|------|------------|
| **Pain Score** | 0-1 measure of frustration/need intensity in a post |
| **Composite Score** | Weighted combination of pain, engagement, validation, recency |
| **Signal Type** | Classification: complaint, frustration, wish, tool_search, etc. |
| **Intent Score** | 0-1 measure of commercial intent (for leads) |
| **Provider** | Swappable implementation of scraper, LLM, or storage |

---

*Generated for OpenClaw Founder Co-Pilot v2.0*
*Last Updated: 2026-02-01*
