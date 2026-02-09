# UPGRADE_SPEC_V1.1 — Technical Upgrade Specification
## Founder Co-Pilot: Reddit CLI → Multi-Platform SaaS Lifecycle Engine

**Version:** 1.1  
**Date:** 2026-02-04  
**Status:** DRAFT  
**Authors:** Engineering (Opus 4.6 Assisted)  
**Inputs:**  
- Current Codebase (`copilot/` — modules, providers, registry, models, CLI)  
- `RESEARCH_IMPROVEMENTS.md` (Gap analysis: HN, sentiment, opportunity scoring)  
- `COMPREHENSIVE_RESEARCH_SaaS.md` (60+ platforms, 4 lifecycle layers)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Audit](#2-current-architecture-audit)
3. [Architecture: Provider Integration Patterns](#3-architecture-provider-integration-patterns)
4. [Logic: Unified Opportunity Score Algorithm](#4-logic-unified-opportunity-score-algorithm)
5. [UI: New CLI Commands for Cross-Platform Discovery](#5-ui-new-cli-commands-for-cross-platform-discovery)
6. [Data: Schema Updates for Multi-Source Leads & Reports](#6-data-schema-updates-for-multi-source-leads--reports)
7. [Module Upgrades](#7-module-upgrades)
8. [Configuration & Secrets Management](#8-configuration--secrets-management)
9. [Migration Strategy](#9-migration-strategy)
10. [Implementation Phases](#10-implementation-phases)
11. [Testing Strategy](#11-testing-strategy)
12. [Appendix: File-by-File Change Matrix](#appendix-file-by-file-change-matrix)

---

## 1. Executive Summary

### 1.1 Vision

Transform Founder Co-Pilot from a **Reddit-only CLI tool** with a single scraper provider into a **multi-platform SaaS lifecycle engine** that discovers opportunities across 15+ platforms, validates them with market signals, monitors competitors with sentiment analysis, and generates enriched leads — all through a unified scoring system and extensible provider architecture.

### 1.2 Scope of This Spec

| Dimension | Current (v1.0) | Target (v1.1) |
|-----------|----------------|----------------|
| **Data Sources** | Reddit only | Reddit + HN + G2/Capterra (via Apify) + IndieHackers + Product Hunt |
| **Scoring** | Single-source composite (Pain × 0.4 + Engagement × 0.25 + Validation × 0.25 + Recency × 0.1) | Unified cross-platform Opportunity Score with source-normalization, trend, and sentiment dimensions |
| **Sentiment** | None | Per-post sentiment classification (frustrated/neutral/positive) integrated into scoring |
| **CLI Commands** | 6 flat commands (discover, config, validate, monitor, leads, export) | 10+ commands including cross-platform scan, sentiment filter, opportunity rank, persona generation |
| **Data Schema** | Reddit-centric (subreddit field, Reddit metadata) | Platform-agnostic with source normalization, sentiment fields, opportunity scores, and platform-specific metadata namespaces |
| **Provider Pattern** | Manual if/elif registration, 2 divergent StorageProvider ABCs | Unified ABC hierarchy, auto-registration via entry points, provider capability declarations |

### 1.3 Key Principles

1. **Backward Compatibility** — Existing `discover`, `validate`, `monitor`, `leads`, `export` commands MUST continue working unchanged.
2. **Provider Isolation** — Each new platform scraper is a self-contained `ScraperProvider` subclass. Zero coupling between providers.
3. **Incremental Delivery** — Each phase is independently shippable and testable.
4. **Schema Evolution** — SQLite migrations are additive (new columns/tables only). No destructive changes to existing tables.
5. **Cost Awareness** — Free-tier APIs first (HN, Reddit). Paid scraping (Apify for G2/Capterra) behind feature flags.

---

## 2. Current Architecture Audit

### 2.1 Directory Structure (As-Is)

```
founder-copilot/
├── bin/copilot                          # Entry point (sys.path hack)
├── copilot/
│   ├── cli/main.py                      # Typer app — 6 commands, manual provider wiring
│   ├── core/config.py                   # ConfigManager (JSON file ~/.founder_copilot/config.json)
│   ├── models/schemas.py                # Pydantic v2: ScrapedPost, PainScore, ValidationReport, Lead
│   ├── modules/
│   │   ├── discovery.py                 # DiscoveryModule (scraper + LLM + storage)
│   │   ├── validation.py                # ValidationModule (LLM + storage)
│   │   ├── monitor.py                   # MonitorModule (discovery + LLM + storage)
│   │   ├── leads.py                     # LeadModule (LLM + storage)
│   │   └── export.py                    # ExportModule (storage only)
│   └── providers/
│       ├── base.py                      # ABCs: ScraperProvider, LLMProvider, StorageProvider (minimal)
│       ├── registry.py                  # ProviderRegistry (manual service locator)
│       ├── groq.py                      # GroqProvider (LLMProvider impl)
│       ├── ollama.py                    # OllamaProvider (LLMProvider impl — NEVER REGISTERED)
│       ├── reddit_scraper.py            # RedditScraper (ScraperProvider impl)
│       └── storage/
│           ├── base.py                  # StorageProvider ABC (RICHER — used by SQLiteProvider)
│           └── sqlite_provider.py       # SQLiteProvider (4 tables: raw_posts, signals, leads, validation_reports)
└── tests/
```

### 2.2 Known Architectural Debt

| ID | Issue | Impact | Fix in This Spec |
|----|-------|--------|------------------|
| **DEBT-1** | **Two divergent `StorageProvider` ABCs** — `providers/base.py` defines `store_posts()`, `providers/storage/base.py` defines `save_post()`. SQLiteProvider uses the latter. | New storage providers don't know which ABC to implement. | Consolidate to single ABC in `providers/storage/base.py` (Section 3.3) |
| **DEBT-2** | **`save_report()` / `get_reports()` not in any ABC** — only exist on SQLiteProvider concrete class. | ExportModule calls `storage.get_reports()` but ABC doesn't declare it. Type checkers miss this. | Add to consolidated StorageProvider ABC (Section 6.3) |
| **DEBT-3** | **OllamaProvider never registered** — `get_registry()` has no `elif llm_name == "ollama"` branch. | Config value `"ollama"` raises ValueError. | Add elif branch + feature flag (Section 3.5) |
| **DEBT-4** | **Hard-coded `source="reddit"` in DiscoveryModule** — `fetch_potential_pains()` always passes `source="reddit"` to `scraper.scrape()`. | Cannot use the same discovery pipeline for HN or other sources. | Refactor to pass `source` from scraper's `name` property (Section 7.1) |
| **DEBT-5** | **`subreddit` field on ScrapedPost** — Reddit-specific. HN posts don't have subreddits. | Schema doesn't generalize to other platforms. | Replace with `channel` (generic) + keep `subreddit` as alias (Section 6.1) |
| **DEBT-6** | **No provider capability introspection** — CLI doesn't know what a scraper supports (sort options, search, etc.). | Can't build generic cross-platform commands. | Add `capabilities` property to ScraperProvider (Section 3.2) |

---

## 3. Architecture: Provider Integration Patterns

### 3.1 Revised Provider Hierarchy

**Goal:** A unified, extensible ABC hierarchy that supports multiple scraper types, capability declarations, and auto-registration.

```
copilot/providers/
├── base.py                        # REVISED: Canonical ABCs for all 3 provider types
├── registry.py                    # REVISED: Auto-discovery + manual registration
├── scrapers/                      # NEW: Scraper provider package
│   ├── __init__.py
│   ├── reddit.py                  # MOVED from reddit_scraper.py
│   ├── hackernews.py              # NEW: HN Firebase API scraper
│   ├── apify_g2.py                # NEW: G2 reviews via Apify
│   ├── apify_capterra.py          # NEW: Capterra reviews via Apify
│   ├── indiehackers.py            # NEW: IndieHackers RSS + scraper
│   └── producthunt.py             # NEW: Product Hunt GraphQL scraper
├── llm/                           # NEW: LLM provider package
│   ├── __init__.py
│   ├── groq.py                    # MOVED from groq.py
│   └── ollama.py                  # MOVED from ollama.py (+ registration fix)
└── storage/
    ├── base.py                    # REVISED: Single canonical StorageProvider ABC
    └── sqlite_provider.py         # REVISED: New columns, new tables
```

### 3.2 Revised `ScraperProvider` ABC

```python
# copilot/providers/base.py — REVISED

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from ..models.schemas import ScrapedPost

class ScraperCapability(Enum):
    """Declares what a scraper can do."""
    SEARCH = "search"              # Can search by keyword
    SORT_NEW = "sort_new"          # Can sort by newest
    SORT_HOT = "sort_hot"          # Can sort by popularity/hot
    SORT_TOP = "sort_top"          # Can sort by top/best
    COMMENTS = "comments"          # Can fetch comment threads
    REVIEWS = "reviews"            # Returns review-type data (G2, Capterra)
    REALTIME = "realtime"          # Supports streaming/polling updates
    HISTORICAL = "historical"      # Can fetch historical data

class ScraperProvider(ABC):
    """Abstract base class for all scraper implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'reddit', 'hackernews', 'g2')."""
        ...
    
    @property
    @abstractmethod
    def platform(self) -> str:
        """Human-readable platform name (e.g., 'Reddit', 'Hacker News')."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> Set[ScraperCapability]:
        """Declare supported capabilities for this scraper."""
        ...
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure with credentials and settings."""
        ...
    
    @abstractmethod
    def scrape(
        self,
        target: str,                   # NOTE: 'source' param REMOVED — name is the source
        limit: int = 100,
        **kwargs
    ) -> List[ScrapedPost]:
        """
        Scrape posts/reviews from this provider's platform.
        
        Args:
            target: Platform-specific target (subreddit name, search query, product slug, etc.)
            limit: Maximum items to return
            **kwargs: Provider-specific options (sort, time_range, etc.)
            
        Returns:
            List of ScrapedPost with source=self.name
        """
        ...

    def health_check(self) -> bool:
        """Optional: verify API connectivity. Default returns True."""
        return True
```

**Key Changes from v1.0:**
- **Removed `source` parameter** from `scrape()`. The provider IS the source — `self.name` is used to set `ScrapedPost.source`.
- **Added `platform` property** for display purposes.
- **Added `capabilities` set** for introspection.
- **Added `health_check()`** for monitoring.

### 3.3 Consolidated `StorageProvider` ABC

```python
# copilot/providers/storage/base.py — REVISED (single canonical ABC)

from abc import ABC, abstractmethod
from typing import List, Optional
from ...models.schemas import ScrapedPost, PainScore, Lead, ValidationReport, OpportunityScore

class StorageProvider(ABC):
    """Canonical storage interface. All storage backends MUST implement this."""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def initialize(self) -> None: ...
    
    # --- Posts ---
    @abstractmethod
    def save_post(self, post: ScrapedPost) -> None: ...
    
    @abstractmethod
    def get_posts(self, limit: int = 100, source: Optional[str] = None) -> List[ScrapedPost]: ...
    
    @abstractmethod
    def get_post_by_id(self, post_id: str) -> Optional[ScrapedPost]: ...  # NEW
    
    # --- Signals / Analysis ---
    @abstractmethod
    def save_signal(self, post_id: str, pain_info: PainScore) -> None: ...
    
    # --- Opportunity Scores --- (NEW)
    @abstractmethod
    def save_opportunity_score(self, score: OpportunityScore) -> None: ...
    
    @abstractmethod
    def get_opportunity_scores(self, limit: int = 100, min_score: float = 0.0) -> List[OpportunityScore]: ...
    
    # --- Leads ---
    @abstractmethod
    def save_lead(self, lead: Lead) -> None: ...
    
    @abstractmethod
    def get_leads(self, limit: Optional[int] = 100) -> List[Lead]: ...
    
    # --- Reports ---
    @abstractmethod
    def save_report(self, report: ValidationReport) -> None: ...  # PROMOTED from SQLiteProvider
    
    @abstractmethod
    def get_reports(self, limit: Optional[int] = None) -> List[ValidationReport]: ...  # PROMOTED
```

**Debt Fix:** Remove the minimal `StorageProvider` in `providers/base.py` and update all imports to point to `providers/storage/base.py`.

### 3.4 New Scraper Provider Implementations

#### 3.4.1 Hacker News Provider (`scrapers/hackernews.py`)

```python
# copilot/providers/scrapers/hackernews.py

import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost

HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA = "https://hn.algolia.com/api/v1"

class HackerNewsScraper(ScraperProvider):
    """Hacker News scraper using Firebase API (stories) + Algolia (search)."""
    
    @property
    def name(self) -> str:
        return "hackernews"
    
    @property
    def platform(self) -> str:
        return "Hacker News"
    
    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.SEARCH,
            ScraperCapability.SORT_NEW,
            ScraperCapability.SORT_TOP,
            ScraperCapability.COMMENTS,
            ScraperCapability.HISTORICAL,
        }
    
    def configure(self, config: Dict[str, Any]) -> None:
        # HN API is free, no auth required
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": config.get("user_agent", "FounderCopilot/1.1")
        })
    
    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape HN stories.
        
        Args:
            target: One of 'topstories', 'newstories', 'askhn', 'showhn', 
                    or a search query string (uses Algolia).
            limit: Max stories to return.
            **kwargs:
                sort: 'new' | 'top' (default: 'new')
                search: If True, use Algolia search with target as query.
        """
        if kwargs.get("search", False):
            return self._search_algolia(query=target, limit=limit, **kwargs)
        else:
            return self._fetch_stories(feed=target, limit=limit)
    
    def _fetch_stories(self, feed: str, limit: int) -> List[ScrapedPost]:
        """Fetch from HN Firebase API (topstories, newstories, etc.)."""
        feed_map = {
            "top": "topstories",
            "new": "newstories",
            "ask": "askstories",
            "show": "showstories",
            "jobs": "jobstories",
        }
        endpoint = feed_map.get(feed, feed)
        
        resp = self._session.get(f"{HN_BASE}/{endpoint}.json")
        resp.raise_for_status()
        story_ids = resp.json()[:limit]
        
        posts = []
        for sid in story_ids:
            item = self._session.get(f"{HN_BASE}/item/{sid}.json").json()
            if item and item.get("type") == "story" and not item.get("deleted"):
                posts.append(self._item_to_post(item))
        return posts
    
    def _search_algolia(self, query: str, limit: int, **kwargs) -> List[ScrapedPost]:
        """Search HN via Algolia API."""
        sort = kwargs.get("sort", "new")
        endpoint = "search" if sort == "top" else "search_by_date"
        
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": min(limit, 1000),
        }
        resp = self._session.get(f"{HN_ALGOLIA}/{endpoint}", params=params)
        resp.raise_for_status()
        
        posts = []
        for hit in resp.json().get("hits", []):
            posts.append(ScrapedPost(
                id=f"hn_{hit['objectID']}",
                source="hackernews",
                title=hit.get("title", ""),
                body=hit.get("story_text") or hit.get("comment_text"),
                author=hit.get("author", "unknown"),
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
                upvotes=hit.get("points", 0) or 0,
                comments_count=hit.get("num_comments", 0) or 0,
                created_at=datetime.fromtimestamp(
                    hit.get("created_at_i", 0), tz=timezone.utc
                ),
                channel=f"hn/{hit.get('_tags', ['story'])[0]}",
                metadata={
                    "hn_id": hit["objectID"],
                    "relevancy_score": hit.get("_highlightResult", {}),
                }
            ))
        return posts
    
    def _item_to_post(self, item: dict) -> ScrapedPost:
        return ScrapedPost(
            id=f"hn_{item['id']}",
            source="hackernews",
            title=item.get("title", ""),
            body=item.get("text"),
            author=item.get("by", "unknown"),
            url=item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}",
            upvotes=item.get("score", 0),
            comments_count=len(item.get("kids", [])),
            created_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
            channel=f"hn/{'ask' if item.get('title','').startswith('Ask HN') else 'show' if item.get('title','').startswith('Show HN') else 'story'}",
            metadata={
                "hn_id": item["id"],
                "hn_type": item.get("type"),
                "descendants": item.get("descendants", 0),
            }
        )
```

#### 3.4.2 G2 Reviews Provider (`scrapers/apify_g2.py`)

```python
# copilot/providers/scrapers/apify_g2.py

from typing import List, Dict, Any, Set
from datetime import datetime, timezone
from ..base import ScraperProvider, ScraperCapability
from ...models.schemas import ScrapedPost

class ApifyG2Scraper(ScraperProvider):
    """G2 review scraper using Apify Actor 'misceres/g2-product-scraper'."""
    
    @property
    def name(self) -> str:
        return "g2"
    
    @property
    def platform(self) -> str:
        return "G2"
    
    @property
    def capabilities(self) -> Set[ScraperCapability]:
        return {
            ScraperCapability.REVIEWS,
            ScraperCapability.SEARCH,
            ScraperCapability.SORT_NEW,
            ScraperCapability.HISTORICAL,
        }
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Requires Apify API token."""
        self._api_token = config["apify_api_token"]
        self._actor_id = config.get("actor_id", "misceres/g2-product-scraper")
        # Optional: import apify_client here to defer dependency
    
    def scrape(self, target: str, limit: int = 100, **kwargs) -> List[ScrapedPost]:
        """
        Scrape G2 reviews for a product.
        
        Args:
            target: G2 product slug (e.g., 'slack', 'notion')
            limit: Max reviews to return
            **kwargs:
                star_rating: Filter by star rating (1-5)
                sort: 'newest' | 'most_helpful'
        """
        from apify_client import ApifyClient  # Lazy import — optional dependency
        
        client = ApifyClient(self._api_token)
        run_input = {
            "productUrl": f"https://www.g2.com/products/{target}/reviews",
            "maxReviews": limit,
            "sort": kwargs.get("sort", "newest"),
        }
        
        run = client.actor(self._actor_id).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        posts = []
        for item in items[:limit]:
            review_id = item.get("reviewId", item.get("id", ""))
            posts.append(ScrapedPost(
                id=f"g2_{target}_{review_id}",
                source="g2",
                title=item.get("title", f"G2 Review of {target}"),
                body=self._combine_review_text(item),
                author=item.get("reviewerName", "anonymous"),
                url=item.get("reviewUrl", f"https://www.g2.com/products/{target}/reviews"),
                upvotes=item.get("helpfulCount", 0),
                comments_count=0,  # G2 reviews don't have comments
                created_at=self._parse_date(item.get("reviewDate")),
                channel=f"g2/{target}",
                metadata={
                    "star_rating": item.get("starRating", 0),
                    "pros": item.get("pros", ""),
                    "cons": item.get("cons", ""),
                    "reviewer_role": item.get("reviewerRole", ""),
                    "company_size": item.get("companySize", ""),
                    "industry": item.get("industry", ""),
                    "review_source": "g2",
                    "product_slug": target,
                }
            ))
        return posts
    
    def _combine_review_text(self, item: dict) -> str:
        parts = []
        if item.get("pros"):
            parts.append(f"PROS: {item['pros']}")
        if item.get("cons"):
            parts.append(f"CONS: {item['cons']}")
        if item.get("reviewBody"):
            parts.append(item["reviewBody"])
        return "\n\n".join(parts)
    
    def _parse_date(self, date_str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
```

#### 3.4.3 Capterra Reviews Provider (`scrapers/apify_capterra.py`)

```python
# copilot/providers/scrapers/apify_capterra.py
# Structure mirrors ApifyG2Scraper with Capterra-specific actor and field mappings.
# Actor: 'apify/capterra-reviews-scraper'
# Key differences:
#   - target = Capterra product URL slug
#   - Fields: overallRating, easeOfUse, customerService, functionality, valueForMoney
#   - metadata includes Capterra-specific scoring dimensions
```

*(Full implementation follows same pattern as G2 — omitted for brevity. See Appendix A for scaffold.)*

### 3.5 Revised `ProviderRegistry` with Auto-Discovery

```python
# copilot/providers/registry.py — REVISED

from typing import Dict, Optional, List, Set
from .base import ScraperProvider, LLMProvider, ScraperCapability
from .storage.base import StorageProvider  # Single canonical import

class ProviderRegistry:
    """Service locator with capability querying and multi-scraper support."""
    
    def __init__(self):
        self._scrapers: Dict[str, ScraperProvider] = {}
        self._llms: Dict[str, LLMProvider] = {}
        self._storage: Dict[str, StorageProvider] = {}

    # --- Registration ---
    def register_scraper(self, provider: ScraperProvider) -> None:
        self._scrapers[provider.name] = provider

    def register_llm(self, provider: LLMProvider) -> None:
        self._llms[provider.name] = provider

    def register_storage(self, provider: StorageProvider) -> None:
        self._storage[provider.name] = provider

    # --- Retrieval ---
    def get_scraper(self, name: str) -> ScraperProvider:
        if name not in self._scrapers:
            available = ", ".join(self._scrapers.keys()) or "(none)"
            raise ValueError(f"Scraper '{name}' not registered. Available: {available}")
        return self._scrapers[name]

    def get_llm(self, name: str) -> LLMProvider:
        if name not in self._llms:
            available = ", ".join(self._llms.keys()) or "(none)"
            raise ValueError(f"LLM '{name}' not registered. Available: {available}")
        return self._llms[name]

    def get_storage(self, name: str) -> StorageProvider:
        if name not in self._storage:
            raise ValueError(f"Storage '{name}' not registered.")
        return self._storage[name]

    # --- NEW: Multi-scraper queries ---
    def get_all_scrapers(self) -> List[ScraperProvider]:
        """Return all registered scrapers."""
        return list(self._scrapers.values())
    
    def get_scrapers_with_capability(self, cap: ScraperCapability) -> List[ScraperProvider]:
        """Return scrapers that declare a specific capability."""
        return [s for s in self._scrapers.values() if cap in s.capabilities]
    
    def list_scraper_names(self) -> List[str]:
        """Return names of all registered scrapers."""
        return list(self._scrapers.keys())
    
    def list_llm_names(self) -> List[str]:
        return list(self._llms.keys())
```

### 3.6 Revised `get_registry()` in CLI

```python
# copilot/cli/main.py — get_registry() REVISED

def get_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    
    # --- Storage (always SQLite for now) ---
    db_path = config_manager.get("db_path")
    storage = SQLiteProvider(db_path=db_path)
    storage.initialize()
    registry.register_storage(storage)
    
    # --- LLM ---
    llm_name = config_manager.get("llm_provider")
    if llm_name == "groq":
        from ..providers.llm.groq import GroqProvider
        api_key = config_manager.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        llm = GroqProvider()
        llm.configure({"api_key": api_key})
        registry.register_llm(llm)
    elif llm_name == "ollama":                          # DEBT-3 FIX
        from ..providers.llm.ollama import OllamaProvider
        llm = OllamaProvider()
        llm.configure({
            "host": config_manager.get("ollama_host", "http://localhost:11434"),
            "model": config_manager.get("ollama_model", "llama3"),
        })
        registry.register_llm(llm)
    else:
        raise ValueError(f"Unsupported LLM: {llm_name}. Available: groq, ollama")
        
    # --- Scrapers (register ALL configured scrapers) ---
    active_scrapers = config_manager.get("active_scrapers", ["reddit"])
    
    if "reddit" in active_scrapers:
        from ..providers.scrapers.reddit import RedditScraper
        scraper = RedditScraper()
        scraper.configure({
            "client_id": config_manager.get("reddit_client_id") or os.getenv("REDDIT_CLIENT_ID"),
            "client_secret": config_manager.get("reddit_client_secret") or os.getenv("REDDIT_CLIENT_SECRET"),
            "user_agent": config_manager.get("reddit_user_agent"),
        })
        registry.register_scraper(scraper)
    
    if "hackernews" in active_scrapers:
        from ..providers.scrapers.hackernews import HackerNewsScraper
        scraper = HackerNewsScraper()
        scraper.configure({
            "user_agent": config_manager.get("reddit_user_agent", "FounderCopilot/1.1"),
        })
        registry.register_scraper(scraper)
    
    if "g2" in active_scrapers:
        apify_token = config_manager.get("apify_api_token") or os.getenv("APIFY_API_TOKEN")
        if apify_token:
            from ..providers.scrapers.apify_g2 import ApifyG2Scraper
            scraper = ApifyG2Scraper()
            scraper.configure({"apify_api_token": apify_token})
            registry.register_scraper(scraper)
    
    if "capterra" in active_scrapers:
        apify_token = config_manager.get("apify_api_token") or os.getenv("APIFY_API_TOKEN")
        if apify_token:
            from ..providers.scrapers.apify_capterra import ApifyCapterraScraper
            scraper = ApifyCapterraScraper()
            scraper.configure({"apify_api_token": apify_token})
            registry.register_scraper(scraper)
    
    return registry
```

**Key Change:** The registry now holds **multiple scrapers simultaneously**. The `active_scrapers` config key controls which are enabled. Default: `["reddit"]` (backward compatible).

---

## 4. Logic: Unified Opportunity Score Algorithm

### 4.1 Problem Statement

The current `PainScore.composite_value` is Reddit-specific:
```
composite = Pain × 0.4 + Engagement × 0.25 + Validation × 0.25 + Recency × 0.1
```

This breaks for multi-source because:
- **Engagement normalization differs** — 100 HN upvotes ≠ 100 Reddit upvotes ≠ 5 G2 "helpful" votes.
- **No sentiment dimension** — RESEARCH_IMPROVEMENTS.md identifies this as a key gap.
- **No cross-source corroboration** — An idea mentioned on BOTH Reddit and HN is stronger than one on either alone.
- **No trend momentum** — A growing pain (more mentions over time) is more valuable than a static one.

### 4.2 Unified Opportunity Score Design

The new **Opportunity Score** replaces `composite_value` as the primary ranking metric. It is a **7-dimensional weighted formula** computed per post, with an optional cross-source bonus.

```
OpportunityScore = Σ(Wi × Di) + CrossSourceBonus

Where:
  D1: pain_intensity      — LLM-assessed problem severity (0-1)         W1 = 0.25
  D2: engagement_norm     — Source-normalized engagement (0-1)           W2 = 0.15
  D3: validation_evidence — LLM-assessed evidence of real need (0-1)    W3 = 0.15
  D4: sentiment_intensity — How frustrated/negative the author is (0-1) W4 = 0.15
  D5: recency             — Time decay function (0-1)                   W5 = 0.08
  D6: trend_momentum      — Growth in similar mentions over time (0-1)  W6 = 0.12
  D7: market_signal       — Keyword match strength for SaaS intent (0-1)W7 = 0.10

  CrossSourceBonus: +0.05 per additional source confirming the same pain topic
```

### 4.3 Dimension Computation Details

#### D1: Pain Intensity (`pain_intensity`)
- **Source:** LLM analysis (existing `PainScore.score`). No change.
- **Prompt enhancement:** Add explicit instruction to score 0.0 for non-pain content (announcements, celebrations).

#### D2: Engagement Normalization (`engagement_norm`)
- **Problem:** 100 Reddit upvotes, 50 HN points, and 3 G2 "helpful" votes represent similar signal strength but wildly different numbers.
- **Solution:** Per-source normalization using percentile-based scaling.

```python
# Engagement normalization constants (calibrated from platform data)
ENGAGEMENT_NORMALIZERS = {
    "reddit": {
        "upvote_cap": 500,      # 500+ upvotes → 1.0
        "upvote_weight": 0.5,
        "comment_cap": 200,     # 200+ comments → 1.0
        "comment_weight": 0.5,
    },
    "hackernews": {
        "upvote_cap": 300,      # HN points cap
        "upvote_weight": 0.6,
        "comment_cap": 150,     # Descendants cap
        "comment_weight": 0.4,
    },
    "g2": {
        "upvote_cap": 20,       # "Helpful" votes on G2 reviews
        "upvote_weight": 0.3,
        "comment_cap": 1,       # G2 reviews rarely have comments
        "comment_weight": 0.0,
        "star_rating_weight": 0.7,  # Star rating is primary signal for reviews
    },
    "capterra": {
        "upvote_cap": 15,
        "upvote_weight": 0.2,
        "comment_cap": 1,
        "comment_weight": 0.0,
        "star_rating_weight": 0.8,
    },
}

def calculate_engagement_norm(post: ScrapedPost) -> float:
    """Normalize engagement to 0-1 regardless of source."""
    norms = ENGAGEMENT_NORMALIZERS.get(post.source, ENGAGEMENT_NORMALIZERS["reddit"])
    
    upvote_score = min(1.0, post.upvotes / norms["upvote_cap"]) * norms["upvote_weight"]
    comment_score = min(1.0, post.comments_count / max(1, norms["comment_cap"])) * norms["comment_weight"]
    
    # For review platforms, factor in star rating if available
    star_weight = norms.get("star_rating_weight", 0.0)
    if star_weight > 0 and "star_rating" in post.metadata:
        # Invert: 1-star = 1.0 (high pain), 5-star = 0.0
        star_pain = max(0.0, (5 - post.metadata["star_rating"]) / 4.0)
        return upvote_score + comment_score + (star_pain * star_weight)
    
    return upvote_score + comment_score
```

#### D3: Validation Evidence (`validation_evidence`)
- **Source:** LLM analysis (existing `PainScore.validation_score`). No change to extraction.
- **Enhancement:** Prompt now explicitly asks: *"Is there evidence others share this problem? (replies agreeing, upvote count, similar posts)"*

#### D4: Sentiment Intensity (`sentiment_intensity`) — NEW

```python
# Added to the LLM analysis prompt in DiscoveryModule.analyze_pain_intensity()

SENTIMENT_PROMPT_ADDITION = """
- sentiment: One of "frustrated", "desperate", "curious", "neutral", "positive"
- sentiment_intensity: Float 0.0-1.0 (How emotionally charged is the post?)
  - 0.0 = casual mention, neutral tone
  - 0.5 = clear frustration, seeking alternatives
  - 0.8 = desperate, strong language, multiple exclamation points
  - 1.0 = urgent, business-critical problem, willing to pay immediately
"""

# Mapping sentiment labels to score multipliers
SENTIMENT_SCORES = {
    "frustrated": 0.7,
    "desperate": 1.0,
    "curious": 0.4,
    "neutral": 0.2,
    "positive": 0.1,
}
```

#### D5: Recency (`recency`)
- **Source:** Existing `calculate_recency_score()`. No change.

#### D6: Trend Momentum (`trend_momentum`) — NEW

```python
def calculate_trend_momentum(post: ScrapedPost, storage: StorageProvider) -> float:
    """
    Calculate trend momentum: are similar pain topics increasing over time?
    
    Strategy: Count posts with similar keywords in the last 30 vs previous 30 days.
    Ratio > 1.0 = growing trend.
    """
    # Extract key pain terms from post title + body (top 3 nouns/phrases)
    key_terms = extract_key_terms(post)  # Uses simple TF-IDF or LLM extraction
    
    recent_count = storage.count_posts_with_terms(key_terms, days=30)
    older_count = storage.count_posts_with_terms(key_terms, days_from=30, days_to=60)
    
    if older_count == 0:
        return 0.5 if recent_count > 0 else 0.0  # New topic, moderate momentum
    
    ratio = recent_count / older_count
    # Sigmoid-normalize to 0-1 range centered at ratio=1.0
    import math
    return 1.0 / (1.0 + math.exp(-2 * (ratio - 1.0)))
```

#### D7: Market Signal (`market_signal`) — NEW

```python
# SaaS intent keyword matching
SAAS_INTENT_KEYWORDS = {
    "high": ["paying for", "subscription", "monthly fee", "enterprise", "API", 
             "B2B", "SaaS", "willing to pay", "shut up and take my money"],
    "medium": ["alternative to", "looking for", "better tool", "recommend", 
               "comparison", "vs", "switch from", "migrate"],
    "low": ["how do I", "tutorial", "help with", "frustrated with", 
            "wish there was", "why doesn't"],
}

def calculate_market_signal(post: ScrapedPost) -> float:
    content = f"{post.title} {post.body or ''}".lower()
    score = 0.0
    for level, keywords in SAAS_INTENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw.lower() in content)
        if level == "high":
            score += matches * 0.3
        elif level == "medium":
            score += matches * 0.15
        else:
            score += matches * 0.05
    return min(1.0, score)
```

### 4.4 Cross-Source Corroboration Bonus

```python
def calculate_cross_source_bonus(post: ScrapedPost, storage: StorageProvider) -> float:
    """
    Bonus for pain topics confirmed across multiple platforms.
    Uses keyword overlap to find corroborating posts from different sources.
    """
    key_terms = extract_key_terms(post)
    sources_with_matches = storage.count_sources_with_terms(key_terms, days=90)
    
    # Subtract 1 for the current source
    additional_sources = max(0, sources_with_matches - 1)
    return additional_sources * 0.05  # +5% per additional source, max practical ~0.15
```

### 4.5 Final Scoring Function

```python
# copilot/modules/scoring.py — NEW FILE

from ..models.schemas import ScrapedPost, PainScore, OpportunityScore
from ..providers.storage.base import StorageProvider

WEIGHTS = {
    "pain_intensity": 0.25,
    "engagement_norm": 0.15,
    "validation_evidence": 0.15,
    "sentiment_intensity": 0.15,
    "recency": 0.08,
    "trend_momentum": 0.12,
    "market_signal": 0.10,
}

def compute_opportunity_score(
    post: ScrapedPost, 
    pain: PainScore, 
    storage: StorageProvider
) -> OpportunityScore:
    """Compute the unified Opportunity Score for a post + its pain analysis."""
    
    d1 = pain.score                                        # pain_intensity
    d2 = calculate_engagement_norm(post)                   # engagement_norm
    d3 = pain.validation_score                             # validation_evidence
    d4 = pain.sentiment_intensity                          # sentiment_intensity (NEW field)
    d5 = calculate_recency_score(post)                     # recency
    d6 = calculate_trend_momentum(post, storage)           # trend_momentum (NEW)
    d7 = calculate_market_signal(post)                     # market_signal (NEW)
    
    base_score = (
        WEIGHTS["pain_intensity"] * d1 +
        WEIGHTS["engagement_norm"] * d2 +
        WEIGHTS["validation_evidence"] * d3 +
        WEIGHTS["sentiment_intensity"] * d4 +
        WEIGHTS["recency"] * d5 +
        WEIGHTS["trend_momentum"] * d6 +
        WEIGHTS["market_signal"] * d7
    )
    
    cross_bonus = calculate_cross_source_bonus(post, storage)
    
    final_score = min(1.0, base_score + cross_bonus)
    
    return OpportunityScore(
        post_id=post.id,
        source=post.source,
        final_score=final_score,
        pain_intensity=d1,
        engagement_norm=d2,
        validation_evidence=d3,
        sentiment_intensity=d4,
        recency=d5,
        trend_momentum=d6,
        market_signal=d7,
        cross_source_bonus=cross_bonus,
        dimensions={
            "pain_intensity": d1,
            "engagement_norm": d2,
            "validation_evidence": d3,
            "sentiment_intensity": d4,
            "recency": d5,
            "trend_momentum": d6,
            "market_signal": d7,
        },
        weights=WEIGHTS,
    )
```

### 4.6 Backward Compatibility

The existing `PainScore.composite_value` field is **retained** and still computed using the v1.0 formula for any code that depends on it. The new `OpportunityScore` is a **separate model** stored in a new table. The `discover` command defaults to showing `OpportunityScore.final_score` but falls back to `PainScore.composite_value` if the scoring module isn't available.

---

## 5. UI: New CLI Commands for Cross-Platform Discovery

### 5.1 Command Architecture

The CLI transitions from 6 flat commands to a **command group** structure:

```
copilot                              # Root (existing)
├── discover                         # ENHANCED: --source flag for multi-platform
├── scan                             # NEW: Cross-platform unified scan
├── validate                         # UNCHANGED
├── monitor                          # ENHANCED: Multi-source monitoring
├── leads                            # ENHANCED: Multi-source leads
├── export                           # ENHANCED: Source filter
├── config                           # ENHANCED: Multi-provider config
├── providers                        # NEW: List/inspect registered providers
├── rank                             # NEW: Re-rank stored posts by OpportunityScore
├── sentiment                        # NEW: Sentiment analysis on stored posts
└── persona                          # NEW: Generate ICP from discovery results
```

### 5.2 Command Specifications

#### `copilot discover` — ENHANCED

```
copilot discover [OPTIONS]

ENHANCED OPTIONS:
  --sub, -s TEXT          Subreddits to search (Reddit only) [multiple]
  --source TEXT           Scraper source to use: 'reddit', 'hackernews', 'g2', 'all'
                          Default: config 'default_scraper' or 'reddit'
  --target, -t TEXT       Platform-specific target (HN: 'ask'/'top'/'show'/search query;
                          G2/Capterra: product slug) [multiple]
  --limit, -l INTEGER     Limit per source/target [default: 10]
  --min-score, -m FLOAT   Minimum Opportunity Score (0.0-1.0) [default: 0.4]
  --sentiment TEXT         Filter by sentiment: 'frustrated', 'desperate', 'all' [default: all]
  
BACKWARD COMPAT:
  `copilot discover -s saas -s startups` works exactly as before (Reddit-only).
  
NEW USAGE:
  `copilot discover --source hackernews --target ask --limit 20`
  `copilot discover --source g2 --target slack --target notion --limit 50`
  `copilot discover --source all -s saas --target ask --sentiment frustrated`
```

#### `copilot scan` — NEW (Cross-Platform Unified Scan)

```
copilot scan [OPTIONS]

PURPOSE: Run discovery across ALL active scrapers simultaneously. The "power command."

OPTIONS:
  --query, -q TEXT        Search query applied to all sources that support SEARCH [required]
  --limit, -l INTEGER     Limit per source [default: 25]
  --min-score, -m FLOAT   Minimum Opportunity Score [default: 0.5]
  --sentiment TEXT         Filter: 'frustrated', 'desperate', 'all' [default: all]
  --sort TEXT              Sort results: 'score', 'recency', 'engagement' [default: score]

OUTPUT:
  Unified Rich table with columns:
  | Score | Source | Title | Channel | Sentiment | Pain | Engagement |

EXAMPLE:
  copilot scan -q "project management frustration" --min-score 0.6 --sentiment frustrated
```

#### `copilot providers` — NEW

```
copilot providers [SUBCOMMAND]

SUBCOMMANDS:
  list       Show all registered providers (scrapers, LLMs, storage)
  info NAME  Show details for a specific provider (capabilities, config status)
  health     Run health_check() on all registered providers

EXAMPLE:
  copilot providers list
  ┌──────────┬─────────────┬──────────────┬────────────────────────────────────┐
  │ Type     │ Name        │ Platform     │ Capabilities                       │
  ├──────────┼─────────────┼──────────────┼────────────────────────────────────┤
  │ Scraper  │ reddit      │ Reddit       │ search, sort_new, sort_hot         │
  │ Scraper  │ hackernews  │ Hacker News  │ search, sort_new, sort_top, ...    │
  │ Scraper  │ g2          │ G2           │ reviews, search, historical        │
  │ LLM      │ groq        │ Groq         │ complete, json_mode                │
  │ Storage  │ sqlite      │ SQLite       │ posts, signals, leads, reports     │
  └──────────┴─────────────┴──────────────┴────────────────────────────────────┘
```

#### `copilot rank` — NEW

```
copilot rank [OPTIONS]

PURPOSE: Re-compute Opportunity Scores for all stored posts using the v1.1 algorithm.
         Useful after adding new data sources or tuning weights.

OPTIONS:
  --source TEXT     Only re-rank posts from this source [default: all]
  --limit INTEGER   Max posts to re-rank [default: 500]
  --top INTEGER     Show top N results [default: 20]
  --weights TEXT    JSON string to override default weights (advanced)

EXAMPLE:
  copilot rank --top 10
  copilot rank --source hackernews --top 5
```

#### `copilot sentiment` — NEW

```
copilot sentiment [OPTIONS]

PURPOSE: Run sentiment analysis on stored posts that don't have sentiment scores.
         Backfill sentiment_intensity and sentiment_label for posts scraped before v1.1.

OPTIONS:
  --source TEXT     Only analyze posts from this source [default: all]
  --limit INTEGER   Max posts to analyze [default: 100]
  --force           Re-analyze even if sentiment already exists

EXAMPLE:
  copilot sentiment --source reddit --limit 200
  copilot sentiment --force  # Re-analyze all
```

#### `copilot persona` — NEW

```
copilot persona [OPTIONS]

PURPOSE: Generate an Ideal Customer Profile (ICP) / user persona based on the top
         pain points discovered so far. Uses LLM to synthesize patterns.

OPTIONS:
  --top INTEGER     Use top N pain points as input [default: 20]
  --source TEXT     Filter posts by source [default: all]
  --output PATH     Write persona to file (Markdown)

OUTPUT:
  Rich-formatted persona card:
  - Demographics, Roles, Company Size
  - Top Pain Points (ranked)
  - Buying Triggers
  - Channels where they hang out
  - Messaging hooks
```

### 5.3 Enhanced Existing Commands

| Command | Enhancement |
|---------|-------------|
| `monitor` | Add `--source` flag. Support monitoring HN for competitor mentions (not just Reddit). |
| `leads` | Add `--source` filter. Show source column in leads table. Sentiment column added. |
| `export` | Add `--source` filter. Add `--type opportunity_scores` for new OpportunityScore data. |
| `config` | New keys displayed: `active_scrapers`, `apify_api_token`, `ollama_host`, etc. |

---

## 6. Data: Schema Updates for Multi-Source Leads & Reports

### 6.1 Revised Pydantic Models

#### `ScrapedPost` — ENHANCED

```python
class ScrapedPost(BaseModel):
    """Unified representation of a post scraped from ANY source."""
    id: str                                     # MUST be globally unique: prefix with source (e.g., "hn_12345")
    source: str                                 # 'reddit', 'hackernews', 'g2', 'capterra', etc.
    title: str
    body: Optional[str] = None
    author: str
    url: str
    upvotes: int
    comments_count: int
    created_at: datetime
    
    # REVISED: Generic channel field replaces subreddit
    channel: Optional[str] = None               # NEW: Generic — 'r/saas', 'hn/ask', 'g2/slack', etc.
    subreddit: Optional[str] = None             # KEPT for backward compat (alias for Reddit channels)
    
    # NEW: Sentiment fields (populated by v1.1 analysis)
    sentiment_label: Optional[str] = None       # 'frustrated', 'desperate', 'curious', 'neutral', 'positive'
    sentiment_intensity: float = 0.0            # 0.0-1.0
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def display_channel(self) -> str:
        """Human-readable channel for display."""
        if self.channel:
            return self.channel
        if self.subreddit:
            return f"r/{self.subreddit}"
        return self.source
```

#### `PainScore` — ENHANCED

```python
class PainScore(BaseModel):
    """Model for pain point intensity scoring."""
    score: float = Field(..., ge=0, le=1)
    reasoning: str
    detected_problems: List[str] = Field(default_factory=list)
    suggested_solutions: List[str] = Field(default_factory=list)
    
    # Existing metrics (kept for backward compat)
    engagement_score: float = Field(default=0.0, ge=0, le=1)
    validation_score: float = Field(default=0.0, ge=0, le=1)
    recency_score: float = Field(default=0.0, ge=0, le=1)
    composite_value: float = Field(default=0.0, ge=0, le=1)  # v1.0 formula
    
    # NEW: Sentiment fields
    sentiment_label: Optional[str] = None       # NEW
    sentiment_intensity: float = Field(default=0.0, ge=0, le=1)  # NEW
```

#### `OpportunityScore` — NEW MODEL

```python
class OpportunityScore(BaseModel):
    """Unified cross-platform opportunity ranking score."""
    post_id: str
    source: str                                 # Post's source platform
    final_score: float = Field(..., ge=0, le=1) # The unified score
    
    # Individual dimensions (all 0-1)
    pain_intensity: float = 0.0
    engagement_norm: float = 0.0
    validation_evidence: float = 0.0
    sentiment_intensity: float = 0.0
    recency: float = 0.0
    trend_momentum: float = 0.0
    market_signal: float = 0.0
    cross_source_bonus: float = 0.0
    
    # Audit trail
    dimensions: Dict[str, float] = Field(default_factory=dict)  # All dimension values
    weights: Dict[str, float] = Field(default_factory=dict)     # Weights used
    
    computed_at: datetime = Field(default_factory=datetime.now)
```

#### `Lead` — ENHANCED

```python
class Lead(BaseModel):
    """Potential customer identified from intent — now multi-source."""
    id: Optional[int] = None
    post_id: str
    source: str = "reddit"                      # NEW: Which platform the lead came from
    author: str
    content_snippet: str
    intent_score: float = Field(..., ge=0, le=1)
    sentiment_label: Optional[str] = None       # NEW
    sentiment_intensity: float = 0.0            # NEW
    contact_url: str
    status: str = "new"
    created_at: datetime = Field(default_factory=datetime.now)
```

#### `ValidationReport` — ENHANCED

```python
class ValidationReport(BaseModel):
    """Deep research report — now includes multi-source evidence."""
    post_id: str
    source: str = "reddit"                      # NEW
    idea_summary: str
    market_size_estimate: str
    competitors: List[Dict[str, str]] = Field(default_factory=list)
    swot_analysis: Dict[str, List[str]] = Field(default_factory=dict)
    validation_verdict: str
    next_steps: List[str] = Field(default_factory=list)
    
    # NEW: Cross-source evidence
    corroborating_sources: List[str] = Field(default_factory=list)  # Other platforms confirming this pain
    corroborating_post_ids: List[str] = Field(default_factory=list)
    
    generated_at: datetime = Field(default_factory=datetime.now)
```

### 6.2 SQLite Schema Migrations

All migrations are **additive** — new columns and new tables only. The `_add_column_if_not_exists()` pattern already in `sqlite_provider.py` is extended.

#### New Columns on Existing Tables

```sql
-- raw_posts: Add channel and sentiment fields
ALTER TABLE raw_posts ADD COLUMN channel TEXT;
ALTER TABLE raw_posts ADD COLUMN sentiment_label TEXT;
ALTER TABLE raw_posts ADD COLUMN sentiment_intensity REAL DEFAULT 0.0;

-- signals: Add sentiment fields
ALTER TABLE signals ADD COLUMN sentiment_label TEXT;
ALTER TABLE signals ADD COLUMN sentiment_intensity REAL DEFAULT 0.0;

-- leads: Add source and sentiment
ALTER TABLE leads ADD COLUMN source TEXT DEFAULT 'reddit';
ALTER TABLE leads ADD COLUMN sentiment_label TEXT;
ALTER TABLE leads ADD COLUMN sentiment_intensity REAL DEFAULT 0.0;

-- validation_reports: Add source and cross-source fields
ALTER TABLE validation_reports ADD COLUMN source TEXT DEFAULT 'reddit';
ALTER TABLE validation_reports ADD COLUMN corroborating_sources TEXT;  -- JSON array
ALTER TABLE validation_reports ADD COLUMN corroborating_post_ids TEXT;  -- JSON array
```

#### New Table: `opportunity_scores`

```sql
CREATE TABLE IF NOT EXISTS opportunity_scores (
    post_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    final_score REAL NOT NULL,
    pain_intensity REAL DEFAULT 0.0,
    engagement_norm REAL DEFAULT 0.0,
    validation_evidence REAL DEFAULT 0.0,
    sentiment_intensity REAL DEFAULT 0.0,
    recency REAL DEFAULT 0.0,
    trend_momentum REAL DEFAULT 0.0,
    market_signal REAL DEFAULT 0.0,
    cross_source_bonus REAL DEFAULT 0.0,
    dimensions TEXT,          -- JSON blob of all dimensions
    weights TEXT,             -- JSON blob of weights used
    computed_at TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES raw_posts (id)
);

-- Index for fast ranking queries
CREATE INDEX IF NOT EXISTS idx_opportunity_final_score ON opportunity_scores (final_score DESC);
CREATE INDEX IF NOT EXISTS idx_opportunity_source ON opportunity_scores (source);
```

#### New Table: `scraper_runs` (Audit/Monitoring)

```sql
CREATE TABLE IF NOT EXISTS scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_name TEXT NOT NULL,
    target TEXT,
    posts_fetched INTEGER DEFAULT 0,
    posts_saved INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    metadata TEXT              -- JSON: error messages, config snapshot, etc.
);
```

### 6.3 SQLiteProvider Updates

New methods to add to `SQLiteProvider`:

```python
# --- Posts (enhanced) ---
def get_post_by_id(self, post_id: str) -> Optional[ScrapedPost]: ...
def get_posts(self, limit: int = 100, source: Optional[str] = None) -> List[ScrapedPost]: ...
def count_posts_with_terms(self, terms: List[str], days: int = 30, 
                            days_from: int = 0, days_to: int = 0) -> int: ...
def count_sources_with_terms(self, terms: List[str], days: int = 90) -> int: ...

# --- Opportunity Scores ---
def save_opportunity_score(self, score: OpportunityScore) -> None: ...
def get_opportunity_scores(self, limit: int = 100, min_score: float = 0.0,
                            source: Optional[str] = None) -> List[OpportunityScore]: ...

# --- Scraper Runs ---
def log_scraper_run(self, run: Dict[str, Any]) -> None: ...

# --- Enhanced Queries ---
def get_posts_without_sentiment(self, limit: int = 100) -> List[ScrapedPost]: ...
def update_post_sentiment(self, post_id: str, label: str, intensity: float) -> None: ...
```

---

## 7. Module Upgrades

### 7.1 DiscoveryModule — Multi-Source Refactor

**Current Issue (DEBT-4):** `fetch_potential_pains()` hard-codes `source="reddit"`.

**Fix:**

```python
class DiscoveryModule:
    """Core logic for finding and classifying high-signal pain points."""
    
    def __init__(
        self, 
        scrapers: List[ScraperProvider],       # CHANGED: Accept multiple scrapers
        llm: LLMProvider, 
        storage: Optional[StorageProvider] = None
    ):
        self.scrapers = scrapers               # List of scrapers
        self.llm = llm
        self.storage = storage
        # ...
    
    def fetch_potential_pains(
        self, 
        targets: Dict[str, List[str]],         # CHANGED: {scraper_name: [target1, target2, ...]}
        limit_per_target: int = 50
    ) -> List[ScrapedPost]:
        """Fetch posts from multiple sources and targets."""
        all_posts = []
        for scraper in self.scrapers:
            scraper_targets = targets.get(scraper.name, [])
            for target in scraper_targets:
                try:
                    posts = scraper.scrape(target=target, limit=limit_per_target)
                    all_posts.extend(posts)
                except Exception as e:
                    logger.error(f"Error scraping {scraper.name}/{target}: {e}")
        return all_posts
    
    def discover(
        self, 
        targets: Dict[str, List[str]],         # CHANGED
        min_score: float = 0.5
    ) -> List[tuple[ScrapedPost, PainScore, OpportunityScore]]:  # CHANGED: 3-tuple
        """Run full discovery pipeline: scrape -> analyze -> score -> filter."""
        posts = self.fetch_potential_pains(targets)
        results = []
        
        for post in posts:
            # Platform-aware pre-filtering
            if not self._passes_prefilter(post):
                continue
            
            pain_info = self.analyze_pain_intensity(post)  # Enhanced with sentiment
            opp_score = compute_opportunity_score(post, pain_info, self.storage)
            
            if opp_score.final_score >= min_score:
                results.append((post, pain_info, opp_score))
                self._persist(post, pain_info, opp_score)
        
        results.sort(key=lambda x: x[2].final_score, reverse=True)
        return results
    
    def _passes_prefilter(self, post: ScrapedPost) -> bool:
        """Platform-aware heuristic filtering before LLM."""
        if post.source == "reddit":
            return post.upvotes >= 5 or post.comments_count >= 2
        elif post.source == "hackernews":
            return post.upvotes >= 3 or post.comments_count >= 1
        elif post.source in ("g2", "capterra"):
            return True  # All reviews are worth analyzing
        return True
```

**Backward Compatibility Shim:**

The existing `discover(subreddits, min_score)` call signature in `cli/main.py` is preserved via an overload:

```python
def discover(self, subreddits_or_targets, min_score=0.5):
    """Accept either legacy List[str] (subreddits) or new Dict format."""
    if isinstance(subreddits_or_targets, list):
        # Legacy path: treat as Reddit subreddits
        targets = {"reddit": subreddits_or_targets}
    else:
        targets = subreddits_or_targets
    return self._discover_impl(targets, min_score)
```

### 7.2 MonitorModule — Multi-Source Monitoring

```python
class MonitorModule:
    def monitor_competitors(
        self, 
        targets: Dict[str, List[str]],     # CHANGED: multi-source targets
        competitors: List[str]
    ) -> int:
        """Scan all active sources for competitor mentions."""
        count = 0
        for scraper in self.discovery.scrapers:
            scraper_targets = targets.get(scraper.name, [])
            for target in scraper_targets:
                try:
                    posts = scraper.scrape(target=target, limit=50)
                    for post in posts:
                        content = f"{post.title} {post.body or ''}".lower()
                        for comp in competitors:
                            if comp.lower() in content:
                                pain_info = self.discovery.analyze_pain_intensity(post)
                                if self.storage:
                                    self.storage.save_post(post)
                                    self.storage.save_signal(post.id, pain_info)
                                count += 1
                except Exception as e:
                    logger.error(f"Error monitoring {scraper.name}/{target}: {e}")
        return count
```

### 7.3 LeadModule — Sentiment-Enriched Leads

```python
class LeadModule:
    INTENT_KEYWORDS = [
        # Existing
        "recommend", "looking for", "how do I", "alternative to", "best tool for",
        # NEW: Review-specific intent
        "switched from", "considering", "evaluating", "need something that",
        "we're looking for", "budget for", "pricing", "free trial",
    ]
    
    def extract_lead_intent(self, post: ScrapedPost) -> Optional[Lead]:
        """Extract lead with sentiment enrichment."""
        # ... existing LLM call ...
        return Lead(
            post_id=post.id,
            source=post.source,                     # NEW
            author=data.get("author", post.author),
            content_snippet=data.get("content_snippet", post.title[:100]),
            intent_score=data.get("intent_score", 0.0),
            sentiment_label=post.sentiment_label,   # NEW: from post
            sentiment_intensity=post.sentiment_intensity,  # NEW
            contact_url=post.url,
            status="new"
        )
```

### 7.4 New Module: `ScoringModule` (`modules/scoring.py`)

Houses the `compute_opportunity_score()` function and all dimension calculators as described in Section 4.

### 7.5 New Module: `PersonaModule` (`modules/persona.py`)

```python
class PersonaModule:
    """Generate Ideal Customer Profiles from aggregated discovery data."""
    
    def __init__(self, llm: LLMProvider, storage: StorageProvider):
        self.llm = llm
        self.storage = storage
    
    def generate_persona(self, top_n: int = 20, source: Optional[str] = None) -> Dict:
        """Synthesize an ICP from the top N pain points."""
        scores = self.storage.get_opportunity_scores(limit=top_n, min_score=0.4)
        posts = [self.storage.get_post_by_id(s.post_id) for s in scores]
        posts = [p for p in posts if p is not None]
        
        if source:
            posts = [p for p in posts if p.source == source]
        
        prompt = f"""
        Based on these {len(posts)} high-signal pain points from multiple platforms,
        generate an Ideal Customer Profile (ICP) / user persona.
        
        Pain Points:
        {self._format_posts_for_prompt(posts)}
        
        Return JSON:
        {{
            "persona_name": "string (e.g., 'Frustrated SaaS Founder')",
            "demographics": {{
                "role": "string",
                "company_size": "string",
                "industry": "string",
                "experience_level": "string"
            }},
            "top_pain_points": ["string"],
            "buying_triggers": ["string"],
            "channels": ["string (where they hang out)"],
            "messaging_hooks": ["string (what resonates)"],
            "willingness_to_pay": "string"
        }}
        """
        response = self.llm.complete(prompt=prompt, 
                                      system_prompt="You are a B2B marketing strategist.", 
                                      response_format={"type": "json_object"})
        return json.loads(response)
```

---

## 8. Configuration & Secrets Management

### 8.1 New Config Keys

```python
# Added to ConfigManager._default_config()
{
    # Existing keys unchanged...
    
    # NEW: Multi-scraper activation
    "active_scrapers": ["reddit"],              # List of enabled scrapers
    "default_scraper": "reddit",                # Default for --source flag
    
    # NEW: Hacker News (no auth needed)
    # (no keys required)
    
    # NEW: Apify (for G2/Capterra)
    "apify_api_token": "",                      # or APIFY_API_TOKEN env var
    
    # NEW: Ollama (DEBT-3 fix)
    "ollama_host": "http://localhost:11434",
    "ollama_model": "llama3",
    
    # NEW: Scoring configuration
    "opportunity_score_weights": {              # Override-able weights
        "pain_intensity": 0.25,
        "engagement_norm": 0.15,
        "validation_evidence": 0.15,
        "sentiment_intensity": 0.15,
        "recency": 0.08,
        "trend_momentum": 0.12,
        "market_signal": 0.10,
    },
    
    # NEW: Feature flags
    "enable_sentiment_analysis": True,
    "enable_trend_momentum": True,
    "enable_cross_source_bonus": True,
}
```

### 8.2 Environment Variable Mapping

| Config Key | Env Var | Required? |
|------------|---------|-----------|
| `groq_api_key` | `GROQ_API_KEY` | Yes (if llm=groq) |
| `reddit_client_id` | `REDDIT_CLIENT_ID` | Yes (if reddit active) |
| `reddit_client_secret` | `REDDIT_CLIENT_SECRET` | Yes (if reddit active) |
| `apify_api_token` | `APIFY_API_TOKEN` | Only if g2/capterra active |
| `tavily_api_key` | `TAVILY_API_KEY` | Only for deep research |

---

## 9. Migration Strategy

### 9.1 Database Migration Plan

```
v1.0 Schema → v1.1 Schema (additive only, no data loss)

Step 1: Add new columns to existing tables (via _add_column_if_not_exists)
Step 2: Create new tables (opportunity_scores, scraper_runs)
Step 3: Create new indexes
Step 4: Backfill channel field from subreddit (UPDATE raw_posts SET channel = 'r/' || subreddit WHERE source = 'reddit')
Step 5: Backfill source field on leads/reports (UPDATE leads SET source = 'reddit' WHERE source IS NULL)
```

All migrations run automatically in `SQLiteProvider.initialize()`. No manual migration commands needed.

### 9.2 Provider File Migration

```
MOVE:  copilot/providers/reddit_scraper.py  →  copilot/providers/scrapers/reddit.py
MOVE:  copilot/providers/groq.py            →  copilot/providers/llm/groq.py
MOVE:  copilot/providers/ollama.py          →  copilot/providers/llm/ollama.py
DELETE: copilot/providers/base.py StorageProvider class (consolidate to storage/base.py)
KEEP:  copilot/providers/base.py ScraperProvider, LLMProvider, ScraperCapability (revised)
```

**Import compatibility:** Add re-exports in old locations:
```python
# copilot/providers/reddit_scraper.py (kept as compatibility shim)
from .scrapers.reddit import RedditScraper  # Re-export for backward compat
```

---

## 10. Implementation Phases

### Phase 1: Foundation Refactor (Week 1-2)
**Goal:** Fix architectural debt, prepare for multi-source.

| Task | Files | Priority |
|------|-------|----------|
| Consolidate StorageProvider ABCs (DEBT-1, DEBT-2) | `providers/base.py`, `providers/storage/base.py` | P0 |
| Add `channel`, `sentiment_label`, `sentiment_intensity` to ScrapedPost | `models/schemas.py` | P0 |
| Add OpportunityScore model | `models/schemas.py` | P0 |
| Move providers to package structure | `providers/scrapers/`, `providers/llm/` | P0 |
| Add `ScraperCapability` enum and revised ScraperProvider ABC | `providers/base.py` | P0 |
| Update `ProviderRegistry` with multi-scraper queries | `providers/registry.py` | P0 |
| SQLite migrations (new columns, new tables) | `providers/storage/sqlite_provider.py` | P0 |
| Fix OllamaProvider registration (DEBT-3) | `cli/main.py` | P1 |
| Update all import paths | All files | P0 |
| Update all existing tests | `tests/` | P0 |

### Phase 2: Hacker News Integration (Week 3-4)
**Goal:** First non-Reddit source working end-to-end.

| Task | Files | Priority |
|------|-------|----------|
| Implement `HackerNewsScraper` | `providers/scrapers/hackernews.py` | P0 |
| Add `hackernews` to `get_registry()` | `cli/main.py` | P0 |
| Refactor DiscoveryModule for multi-scraper (DEBT-4) | `modules/discovery.py` | P0 |
| Add `--source` and `--target` flags to `discover` command | `cli/main.py` | P0 |
| Implement `copilot providers` command | `cli/main.py` | P1 |
| Add HN-specific engagement normalization constants | `modules/scoring.py` | P1 |
| Write HN scraper tests (mock Firebase/Algolia responses) | `tests/test_hackernews.py` | P0 |
| Integration test: `copilot discover --source hackernews --target ask` | `tests/` | P0 |

### Phase 3: Opportunity Score & Sentiment (Week 5-6)
**Goal:** Unified scoring algorithm live.

| Task | Files | Priority |
|------|-------|----------|
| Implement `ScoringModule` with all 7 dimensions | `modules/scoring.py` | P0 |
| Enhance LLM prompt for sentiment extraction (D4) | `modules/discovery.py` | P0 |
| Implement trend momentum calculation (D6) | `modules/scoring.py` | P1 |
| Implement market signal calculation (D7) | `modules/scoring.py` | P1 |
| Implement cross-source bonus | `modules/scoring.py` | P1 |
| Implement `copilot rank` command | `cli/main.py` | P0 |
| Implement `copilot sentiment` command | `cli/main.py` | P1 |
| Implement `copilot scan` command | `cli/main.py` | P0 |
| Update `discover` output to show OpportunityScore | `cli/main.py` | P0 |
| Scoring unit tests (mock data, known outputs) | `tests/test_scoring.py` | P0 |

### Phase 4: G2/Capterra via Apify (Week 7-8)
**Goal:** Review platform integration.

| Task | Files | Priority |
|------|-------|----------|
| Implement `ApifyG2Scraper` | `providers/scrapers/apify_g2.py` | P0 |
| Implement `ApifyCapterraScraper` | `providers/scrapers/apify_capterra.py` | P0 |
| Add review-specific engagement normalization | `modules/scoring.py` | P0 |
| Add `g2`/`capterra` to `get_registry()` | `cli/main.py` | P0 |
| Feature flag: `apify_api_token` required check | `cli/main.py` | P1 |
| Write Apify scraper tests (mock API responses) | `tests/test_apify_scrapers.py` | P0 |

### Phase 5: Persona Generation & Polish (Week 9-10)
**Goal:** ICP generation, UX polish, docs.

| Task | Files | Priority |
|------|-------|----------|
| Implement `PersonaModule` | `modules/persona.py` | P1 |
| Implement `copilot persona` command | `cli/main.py` | P1 |
| Update `leads` command with source/sentiment columns | `cli/main.py` | P1 |
| Update `export` with `--type opportunity_scores` | `cli/main.py` | P1 |
| Update `monitor` for multi-source | `modules/monitor.py`, `cli/main.py` | P1 |
| Update `docs/PROVIDERS.md` with all new providers | `docs/` | P2 |
| End-to-end integration tests (full pipeline) | `tests/` | P0 |

---

## 11. Testing Strategy

### 11.1 Test Categories

| Category | Scope | Tooling | Coverage Target |
|----------|-------|---------|-----------------|
| **Unit** | Individual functions (scoring, normalization, keyword matching) | pytest + fixtures | 90% |
| **Provider** | Each scraper against mock API responses | pytest + responses/httpx_mock | 95% |
| **Integration** | Module → Provider → Storage round-trip | pytest + SQLite in-memory | 80% |
| **CLI** | Command invocation + output format | typer.testing.CliRunner | 70% |
| **Backward Compat** | v1.0 commands produce same output format | regression test suite | 100% |

### 11.2 Key Test Cases

```python
# test_scoring.py
def test_engagement_norm_reddit_vs_hn():
    """100 Reddit upvotes and 100 HN points should produce different normalized scores."""
    
def test_opportunity_score_cross_source_bonus():
    """A pain mentioned on both Reddit and HN scores higher than either alone."""
    
def test_opportunity_score_backward_compat():
    """composite_value (v1.0) is still computed alongside OpportunityScore."""

# test_hackernews.py
def test_hn_search_returns_scraped_posts():
    """Algolia search results are correctly mapped to ScrapedPost."""
    
def test_hn_post_id_prefixed():
    """All HN post IDs are prefixed with 'hn_' to avoid collision with Reddit IDs."""

# test_registry.py
def test_multi_scraper_registration():
    """Registry holds multiple scrapers simultaneously."""
    
def test_capability_query():
    """get_scrapers_with_capability(SEARCH) returns only search-capable scrapers."""

# test_cli_backward_compat.py
def test_discover_legacy_subreddit_args():
    """`copilot discover -s saas` still works (backward compat shim)."""
```

---

## Appendix: File-by-File Change Matrix

| File | Status | Changes |
|------|--------|---------|
| `copilot/providers/base.py` | **REVISED** | Add `ScraperCapability` enum, `platform` property, `capabilities` property, `health_check()`. Remove `StorageProvider` (moved). Remove `source` param from `scrape()`. |
| `copilot/providers/registry.py` | **REVISED** | Add `get_all_scrapers()`, `get_scrapers_with_capability()`, `list_scraper_names()`, `list_llm_names()`. |
| `copilot/providers/storage/base.py` | **REVISED** | Add `get_post_by_id()`, `save_opportunity_score()`, `get_opportunity_scores()`, `save_report()`, `get_reports()`. Add `source` filter to `get_posts()`. |
| `copilot/providers/storage/sqlite_provider.py` | **REVISED** | New tables (`opportunity_scores`, `scraper_runs`). New columns on existing tables. New methods per Section 6.3. Migration logic. |
| `copilot/providers/scrapers/__init__.py` | **NEW** | Package init. |
| `copilot/providers/scrapers/reddit.py` | **MOVED** | From `reddit_scraper.py`. Remove `source` param from `scrape()` (use `self.name`). Add `platform`, `capabilities`. |
| `copilot/providers/scrapers/hackernews.py` | **NEW** | Full implementation per Section 3.4.1. |
| `copilot/providers/scrapers/apify_g2.py` | **NEW** | Full implementation per Section 3.4.2. |
| `copilot/providers/scrapers/apify_capterra.py` | **NEW** | Mirrors G2 pattern with Capterra-specific fields. |
| `copilot/providers/llm/__init__.py` | **NEW** | Package init. |
| `copilot/providers/llm/groq.py` | **MOVED** | From `groq.py`. No logic changes. |
| `copilot/providers/llm/ollama.py` | **MOVED** | From `ollama.py`. No logic changes. |
| `copilot/models/schemas.py` | **REVISED** | Add `OpportunityScore` model. Add `channel`, `sentiment_label`, `sentiment_intensity` to `ScrapedPost`. Add `sentiment_*` to `PainScore`. Add `source`, `sentiment_*` to `Lead`. Add `source`, `corroborating_*` to `ValidationReport`. |
| `copilot/modules/discovery.py` | **REVISED** | Accept `List[ScraperProvider]`. Multi-target `fetch_potential_pains()`. Enhanced LLM prompt with sentiment. Backward-compat `discover()` shim. |
| `copilot/modules/scoring.py` | **NEW** | `compute_opportunity_score()`, all dimension calculators, normalization constants. |
| `copilot/modules/persona.py` | **NEW** | `PersonaModule.generate_persona()`. |
| `copilot/modules/monitor.py` | **REVISED** | Multi-source target dict. |
| `copilot/modules/leads.py` | **REVISED** | Additional intent keywords for reviews. `source` and `sentiment_*` on Lead. |
| `copilot/modules/export.py` | **REVISED** | Add `export_opportunity_scores_to_csv/md()`. Source filter on all exports. |
| `copilot/cli/main.py` | **REVISED** | Revised `get_registry()` with multi-scraper. New commands: `scan`, `providers`, `rank`, `sentiment`, `persona`. Enhanced existing commands with `--source` flag. |
| `copilot/core/config.py` | **REVISED** | New default keys per Section 8.1. |
| `copilot/providers/reddit_scraper.py` | **COMPAT SHIM** | Re-exports `RedditScraper` from new location. |
| `copilot/providers/groq.py` | **COMPAT SHIM** | Re-exports `GroqProvider` from new location. |
| `copilot/providers/ollama.py` | **COMPAT SHIM** | Re-exports `OllamaProvider` from new location. |
| `tests/test_scoring.py` | **NEW** | Unit tests for all scoring dimensions and the unified formula. |
| `tests/test_hackernews.py` | **NEW** | HN scraper tests with mocked API responses. |
| `tests/test_apify_scrapers.py` | **NEW** | G2/Capterra scraper tests. |
| `tests/test_cli_backward_compat.py` | **NEW** | Regression tests ensuring v1.0 commands still work. |
| `tests/test_multi_source.py` | **NEW** | Integration tests for cross-platform discovery pipeline. |

---

## Appendix B: Target Directory Structure (v1.1)

```
founder-copilot/
├── bin/copilot
├── copilot/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py                          # REVISED (10+ commands)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                        # REVISED (new keys)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                       # REVISED (OpportunityScore, sentiment fields)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── discovery.py                     # REVISED (multi-scraper)
│   │   ├── validation.py                    # MINOR REVISIONS
│   │   ├── monitor.py                       # REVISED (multi-source)
│   │   ├── leads.py                         # REVISED (sentiment, source)
│   │   ├── export.py                        # REVISED (new types, source filter)
│   │   ├── scoring.py                       # NEW
│   │   └── persona.py                       # NEW
│   └── providers/
│       ├── __init__.py
│       ├── base.py                          # REVISED (ScraperCapability, revised ABCs)
│       ├── registry.py                      # REVISED (multi-scraper queries)
│       ├── reddit_scraper.py                # COMPAT SHIM → scrapers/reddit.py
│       ├── groq.py                          # COMPAT SHIM → llm/groq.py
│       ├── ollama.py                        # COMPAT SHIM → llm/ollama.py
│       ├── scrapers/
│       │   ├── __init__.py
│       │   ├── reddit.py                    # MOVED + REVISED
│       │   ├── hackernews.py                # NEW
│       │   ├── apify_g2.py                  # NEW
│       │   └── apify_capterra.py            # NEW
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── groq.py                      # MOVED
│       │   └── ollama.py                    # MOVED
│       └── storage/
│           ├── base.py                      # REVISED (canonical ABC)
│           └── sqlite_provider.py           # REVISED (new tables, columns, methods)
├── tests/
│   ├── test_cli.py                          # UPDATED
│   ├── test_cli_backward_compat.py          # NEW
│   ├── test_discovery.py                    # UPDATED
│   ├── test_scoring.py                      # NEW
│   ├── test_hackernews.py                   # NEW
│   ├── test_apify_scrapers.py               # NEW
│   ├── test_multi_source.py                 # NEW
│   ├── test_llm_providers.py                # UPDATED
│   ├── test_new_modules.py                  # UPDATED
│   ├── test_registry.py                     # UPDATED
│   └── test_storage.py                      # UPDATED
├── docs/
│   └── PROVIDERS.md                         # UPDATED
├── UPGRADE_SPEC_V1.1.md                     # THIS DOCUMENT
├── RESEARCH_IMPROVEMENTS.md
├── COMPREHENSIVE_RESEARCH_SaaS.md
├── MVP_SPEC.md
└── README.md
```

---

## Appendix C: Opportunity Score Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPPORTUNITY SCORE v1.1                            │
│                                                                     │
│  Score = Σ(Wi × Di) + CrossSourceBonus         Range: 0.00 - 1.00  │
│                                                                     │
│  ┌──────────────────────┬────────┬──────────────────────────────┐   │
│  │ Dimension            │ Weight │ Source                       │   │
│  ├──────────────────────┼────────┼──────────────────────────────┤   │
│  │ D1: Pain Intensity   │  0.25  │ LLM analysis                │   │
│  │ D2: Engagement Norm  │  0.15  │ Platform-normalized metrics  │   │
│  │ D3: Validation Evid. │  0.15  │ LLM analysis                │   │
│  │ D4: Sentiment Intens.│  0.15  │ LLM sentiment extraction    │   │
│  │ D5: Recency          │  0.08  │ Time decay function          │   │
│  │ D6: Trend Momentum   │  0.12  │ Historical frequency growth  │   │
│  │ D7: Market Signal    │  0.10  │ SaaS intent keyword match   │   │
│  ├──────────────────────┼────────┼──────────────────────────────┤   │
│  │ Cross-Source Bonus   │ +0.05  │ Per additional platform      │   │
│  └──────────────────────┴────────┴──────────────────────────────┘   │
│                                                                     │
│  Interpretation:                                                    │
│    0.00 - 0.29  →  Low signal (noise)                              │
│    0.30 - 0.49  →  Moderate (worth watching)                       │
│    0.50 - 0.69  →  Strong (investigate further)                    │
│    0.70 - 0.84  →  Very Strong (validate immediately)              │
│    0.85 - 1.00  →  Exceptional (rare, multi-source confirmed)      │
└─────────────────────────────────────────────────────────────────────┘
```

---

*End of UPGRADE_SPEC_V1.1 — Technical Upgrade Specification*  
*Generated: 2026-02-04 | Assisted by Opus 4.6*
