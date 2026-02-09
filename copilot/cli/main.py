import typer
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from typing import List, Optional, Dict
import os
from pathlib import Path
from datetime import datetime

from ..core.config import ConfigManager
from ..providers.registry import ProviderRegistry, ScraperCapability
from ..providers.llm.groq import GroqProvider
from ..providers.llm.ollama import OllamaProvider
from ..providers.scrapers.reddit import RedditScraper
from ..providers.scrapers.hackernews import HackerNewsScraper
from ..providers.scrapers.apify_g2 import ApifyG2Scraper
from ..providers.scrapers.apify_capterra import ApifyCapterraScraper
from ..providers.scrapers.producthunt import ProductHuntScraper
from ..providers.storage.sqlite_provider import SQLiteProvider
from ..providers.storage.base import StorageProvider
from ..modules.discovery import DiscoveryModule
from ..modules.validation import ValidationModule
from ..modules.monitor import MonitorModule
from ..modules.leads import LeadModule
from ..modules.outreach import OutreachModule
from ..providers.crm.hubspot_provider import HubSpotProvider
from ..providers.crm.salesforce_provider import SalesForceProvider
from ..modules.export import ExportModule
from ..modules.scoring import ScoringModule
from ..modules.persona import PersonaModule

app = typer.Typer(help="Founder Co-Pilot CLI - Discovery and Validation Engine.")
console = Console()
config_manager = ConfigManager()


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
        api_key = config_manager.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        llm = GroqProvider()
        llm.configure({"api_key": api_key})
        registry.register_llm(llm)
    elif llm_name == "ollama":
        llm = OllamaProvider()
        llm.configure(
            {
                "host": config_manager.get("ollama_host", "http://localhost:11434"),
                "model": config_manager.get("ollama_model", "llama3"),
            }
        )
        registry.register_llm(llm)
    elif llm_name == "mock":
        from ..providers.llm.mock import MockLLMProvider

        llm = MockLLMProvider()
        llm.configure({})
        registry.register_llm(llm)
    else:
        raise ValueError(f"Unsupported LLM: {llm_name}. Available: groq, ollama, mock")

    # --- CRM ---
    crm_name = config_manager.get("crm_provider")
    if crm_name == "hubspot":
        crm = HubSpotProvider()
        crm.configure(
            {
                "client_id": config_manager.get("hubspot_client_id")
                or os.getenv("HUBSPOT_CLIENT_ID"),
                "client_secret": config_manager.get("hubspot_client_secret")
                or os.getenv("HUBSPOT_CLIENT_SECRET"),
                "redirect_uri": config_manager.get("hubspot_redirect_uri")
                or os.getenv("HUBSPOT_REDIRECT_URI"),
                "access_token": config_manager.get("hubspot_access_token"),
                "refresh_token": config_manager.get("hubspot_refresh_token"),
                "expires_at": config_manager.get("hubspot_access_token_expires_at", 0),
            }
        )
        registry.register_crm(crm)
    elif crm_name == "salesforce":
        crm = SalesForceProvider()
        crm.configure(
            {
                "client_id": config_manager.get("salesforce_client_id")
                or os.getenv("SALESFORCE_CLIENT_ID"),
                "client_secret": config_manager.get("salesforce_client_secret")
                or os.getenv("SALESFORCE_CLIENT_SECRET"),
                "redirect_uri": config_manager.get("salesforce_redirect_uri")
                or os.getenv("SALESFORCE_REDIRECT_URI"),
                "access_token": config_manager.get("salesforce_access_token"),
                "refresh_token": config_manager.get("salesforce_refresh_token"),
                "instance_url": config_manager.get("salesforce_instance_url"),
                "expires_at": config_manager.get("salesforce_access_token_expires_at", 0),
            }
        )
        registry.register_crm(crm)
    elif crm_name:
        console.print(
            f"[yellow]Warning: Unsupported CRM provider '{crm_name}'. Skipping configuration.[/yellow]"
        )

    # --- Scrapers (register ALL configured scrapers) ---
    active_scrapers = config_manager.get("active_scrapers", ["reddit"])

    if "reddit" in active_scrapers:
        scraper = RedditScraper()
        scraper.configure(
            {
                "client_id": config_manager.get("reddit_client_id")
                or os.getenv("REDDIT_CLIENT_ID"),
                "client_secret": config_manager.get("reddit_client_secret")
                or os.getenv("REDDIT_CLIENT_SECRET"),
                "user_agent": config_manager.get("reddit_user_agent"),
            }
        )
        registry.register_scraper(scraper)

    if "hackernews" in active_scrapers:
        scraper = HackerNewsScraper()
        scraper.configure(
            {
                "user_agent": config_manager.get(
                    "reddit_user_agent", "FounderCopilot/1.1"
                ),
            }
        )
        registry.register_scraper(scraper)

    if "g2" in active_scrapers:
        apify_token = config_manager.get("apify_api_token") or os.getenv(
            "APIFY_API_TOKEN"
        )
        if apify_token:
            scraper = ApifyG2Scraper()
            scraper.configure({"apify_api_token": apify_token})
            registry.register_scraper(scraper)

    if "capterra" in active_scrapers:
        apify_token = config_manager.get("apify_api_token") or os.getenv(
            "APIFY_API_TOKEN"
        )
        if apify_token:
            scraper = ApifyCapterraScraper()
            scraper.configure({"apify_api_token": apify_token})
            registry.register_scraper(scraper)

    if "producthunt" in active_scrapers:
        ph_token = config_manager.get("producthunt_api_token") or os.getenv(
            "PRODUCTHUNT_API_TOKEN"
        )
        if ph_token:
            scraper = ProductHuntScraper()
            scraper.configure({"api_token": ph_token})
            registry.register_scraper(scraper)

    return registry


def get_discovery_module(registry: ProviderRegistry) -> DiscoveryModule:
    llm_name = config_manager.get("llm_provider")
    scraper_name = config_manager.get("default_scraper", "reddit")
    # For backward compatibility, get the default scraper.
    # But DiscoveryModule can take a list now?
    # The existing code in main.py passed a single scraper.
    # Let's keep it simple for get_discovery_module to return a module with the default scraper,
    # or handle the multi-scraper case inside the commands.

    try:
        scraper = registry.get_scraper(scraper_name)
    except ValueError:
        # Fallback to first available if default not found
        all_scrapers = registry.get_all_scrapers()
        if all_scrapers:
            scraper = all_scrapers[0]
        else:
            raise ValueError("No scrapers registered. Check your config.")

    return DiscoveryModule(
        scraper=scraper,
        llm=registry.get_llm(llm_name),
        storage=registry.get_storage("sqlite"),
    )


def _build_targets_dict(
    registry: ProviderRegistry, source: Optional[str], targets: List[str]
) -> Dict[str, List[str]]:
    """Build targets dictionary from source and target lists."""
    if source == "all":
        all_scrapers = registry.list_scraper_names()
        # If no explicit targets, use defaults? Or empty?
        # The spec implies target argument is applied to the source.
        # But if source=all, apply target to all?
        result = {scraper: targets for scraper in all_scrapers}
        return result

    if source is None:
        source = config_manager.get("default_scraper", "reddit")

    result = {str(source): targets}
    return result


@app.command()
def discover(
    subreddits: Optional[List[str]] = typer.Option(
        None, "--sub", "-s", help="Subreddits to search (Reddit only) [multiple]"
    ),
    source: Optional[str] = typer.Option(
        None,
        "--source",
        help="Scraper source to use: 'reddit', 'hackernews', 'g2', 'capterra', 'producthunt', or 'all'",
    ),
    target: Optional[List[str]] = typer.Option(
        None,
        "--target",
        "-t",
        help="Platform-specific target (HN: ask/top/show/search, G2/Capterra: product slug) [multiple]",
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit per source/target"),
    min_score: float = typer.Option(
        0.4, "--min-score", "-m", help="Minimum score (0.0-1.0)"
    ),
    sentiment: str = typer.Option(
        "all",
        "--sentiment",
        help="Filter by sentiment: 'frustrated', 'desperate', 'all'",
    ),
):
    """Discover high-signal pain points from social media."""
    registry = get_registry()
    llm_name = config_manager.get("llm_provider")
    storage = registry.get_storage("sqlite")

    # Resolve targets
    targets_dict = {}
    if target:
        targets_dict = _build_targets_dict(registry, source, target)
    else:
        # Legacy fallback
        subs = subreddits or config_manager.get("subreddits")
        targets_dict = {"reddit": subs}  # Default to reddit if no source specified

    # Initialize modules
    # DiscoveryModule needs the list of scrapers relevant to targets_dict
    relevant_scrapers = []
    for s_name in targets_dict.keys():
        try:
            relevant_scrapers.append(registry.get_scraper(s_name))
        except ValueError:
            console.print(
                f"[yellow]Warning: Scraper '{s_name}' not available. Skipping.[/yellow]"
            )

    if not relevant_scrapers:
        console.print("[red]No valid scrapers available for discovery.[/red]")
        return

    discovery_module = DiscoveryModule(
        scraper=relevant_scrapers,
        llm=registry.get_llm(llm_name),
        storage=storage,
    )
    scoring_module = ScoringModule(storage)

    with console.status("[bold green]Discovering pain points..."):
        # Discovery returns (post, pain_score)
        results = discovery_module.discover(
            targets_dict, min_score=0.0
        )  # Get all, filter later by OppScore

    if not results:
        console.print("[yellow]No signals found with current criteria.[/yellow]")
        return

    # Compute Opportunity Scores
    with console.status("[bold blue]Computing Opportunity Scores..."):
        # This saves scores to DB
        opp_scores = scoring_module.compute_scores_for_posts(results)

    # Filter & Sort
    filtered_scores = []
    for score in opp_scores:
        if score.final_score < min_score:
            continue

        # Check sentiment filter
        # Need to fetch the signal to check sentiment label?
        # Or check if OpportunityScore has it? OpportunityScore has sentiment_intensity
        # But filter is by label.
        # We can look up the post/signal from results list or storage.
        # Optimization: OpportunityScore doesn't store label.
        # But we have 'results' list which has (post, pain).

        # Find corresponding pain info
        pain = next((p for post, p in results if post.id == score.post_id), None)
        if sentiment != "all" and pain:
            if pain.sentiment_label != sentiment:
                continue

        filtered_scores.append(score)

    if not filtered_scores:
        console.print(
            f"[yellow]No signals found with score >= {min_score} and sentiment='{sentiment}'.[/yellow]"
        )
        return

    table = Table(title="Discovered Opportunity Signals")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Source", style="blue")
    table.add_column("Title", style="magenta")
    table.add_column("Channel", style="green")
    table.add_column("Pain", justify="right")
    table.add_column("Engage", justify="right")

    for score in filtered_scores[
        : limit * len(targets_dict)
    ]:  # Approximate limit display
        # Fetch post title/channel for display
        post = storage.get_post_by_id(score.post_id)
        if not post:
            continue

        table.add_row(
            f"{score.final_score:.2f}",
            score.source,
            post.title[:50] + "..." if len(post.title) > 50 else post.title,
            post.display_channel,
            f"{score.pain_intensity:.2f}",
            f"{score.engagement_norm:.2f}",
        )

    console.print(table)
    console.print(
        f"\n[bold green]Found {len(filtered_scores)} signals. Data saved to {config_manager.get('db_path')}[/bold green]"
    )


@app.command()
def scan(
    query: str = typer.Option(
        ..., "--query", "-q", help="Search query applied to all sources"
    ),
    limit: int = typer.Option(25, "--limit", "-l", help="Limit per source"),
    min_score: float = typer.Option(
        0.5, "--min-score", "-m", help="Minimum Opportunity Score"
    ),
    sentiment: str = typer.Option(
        "all", "--sentiment", help="Filter: 'frustrated', 'desperate', 'all'"
    ),
    sort: str = typer.Option(
        "score", "--sort", help="Sort results: 'score', 'recency', 'engagement'"
    ),
):
    """Run discovery across ALL active scrapers simultaneously."""
    registry = get_registry()
    storage = registry.get_storage("sqlite")
    llm_name = config_manager.get("llm_provider")

    # Get all scrapers with SEARCH capability
    scrapers = registry.get_scrapers_with_capability(ScraperCapability.SEARCH)
    if not scrapers:
        console.print("[red]No scrapers with SEARCH capability found.[/red]")
        return

    discovery_module = DiscoveryModule(
        scraper=scrapers,
        llm=registry.get_llm(llm_name),
        storage=storage,
    )
    scoring_module = ScoringModule(storage)

    # Build targets: {scraper_name: [query]}
    targets_dict = {s.name: [query] for s in scrapers}

    with console.status(
        f"[bold green]Scanning {len(scrapers)} platforms for '{query}'...[/bold green]"
    ):
        results = discovery_module.discover(targets_dict, min_score=0.0)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    with console.status("[bold blue]Computing Scores..."):
        opp_scores = scoring_module.compute_scores_for_posts(results)

    # Filter
    filtered = []
    for score in opp_scores:
        if score.final_score < min_score:
            continue

        pain = next((p for post, p in results if post.id == score.post_id), None)
        if sentiment != "all" and pain and pain.sentiment_label != sentiment:
            continue

        filtered.append(score)

    # Sort
    if sort == "recency":
        filtered.sort(key=lambda x: x.recency, reverse=True)
    elif sort == "engagement":
        filtered.sort(key=lambda x: x.engagement_norm, reverse=True)
    else:  # score
        filtered.sort(key=lambda x: x.final_score, reverse=True)

    # Display
    table = Table(title=f"Scan Results: '{query}'")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Source", style="blue")
    table.add_column("Title", style="magenta")
    table.add_column("Sentiment", style="yellow")

    for score in filtered[: limit * len(scrapers)]:
        post = storage.get_post_by_id(score.post_id)
        pain = storage.get_signal(score.post_id)
        if not post:
            continue

        sent_label = pain.sentiment_label if pain else "N/A"

        table.add_row(
            f"{score.final_score:.2f}",
            score.source,
            post.title[:60] + "...",
            sent_label,
        )

    console.print(table)


@app.command()
def providers(
    command: Optional[str] = typer.Argument(
        "list", help="Subcommand: list, info, health"
    ),
):
    """List and inspect registered providers."""
    registry = get_registry()

    if command == "list":
        table = Table(title="Registered Providers")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Platform", style="green")
        table.add_column("Capabilities")

        for s in registry.get_all_scrapers():
            caps = ", ".join([c.value for c in s.capabilities])
            table.add_row("Scraper", s.name, s.platform, caps)

        for name in registry.list_llm_names():
            table.add_row("LLM", name, "-", "-")

        table.add_row("Storage", "sqlite", "SQLite", "posts, signals, leads, reports")
        console.print(table)

    elif command == "health":
        with console.status("Running health checks..."):
            for s in registry.get_all_scrapers():
                status = "OK" if s.health_check() else "FAIL"
                color = "green" if status == "OK" else "red"
                console.print(f"[{color}]{s.name}: {status}[/{color}]")


@app.command()
def rank(
    limit: int = typer.Option(500, "--limit", help="Max posts to re-rank"),
    top: int = typer.Option(20, "--top", help="Show top N results"),
    source: str = typer.Option("all", "--source", help="Source filter"),
):
    """Re-compute Opportunity Scores for stored posts."""
    registry = get_registry()
    storage = registry.get_storage("sqlite")
    scoring = ScoringModule(storage)

    src_filter = None if source == "all" else source
    posts = storage.get_posts(limit=limit, source=src_filter)

    results = []
    for post in posts:
        pain = storage.get_signal(post.id)
        if pain:
            results.append((post, pain))

    with console.status(f"[bold blue]Re-ranking {len(results)} posts..."):
        scores = scoring.compute_scores_for_posts(results)

    table = Table(title=f"Top {top} Re-Ranked Opportunities")
    table.add_column("Score", style="cyan")
    table.add_column("Source", style="blue")
    table.add_column("Title", style="magenta")

    for score in scores[:top]:
        post = storage.get_post_by_id(score.post_id)
        if post:
            table.add_row(f"{score.final_score:.2f}", score.source, post.title[:60])

    console.print(table)


@app.command()
def sentiment(
    limit: int = typer.Option(100, "--limit", help="Max posts to analyze"),
    source: str = typer.Option("all", "--source", help="Source filter"),
    force: bool = typer.Option(
        False, "--force", help="Re-analyze even if sentiment exists"
    ),
):
    """Run sentiment analysis on stored posts."""
    registry = get_registry()
    storage = registry.get_storage("sqlite")
    # Need discovery module to use analyze_pain_intensity (or extract just that part)
    # Ideally should use DiscoveryModule but bypass scraping.
    # However DiscoveryModule.analyze_pain_intensity is what we need.
    discovery = get_discovery_module(registry)

    src_filter = None if source == "all" else source
    posts = storage.get_posts(limit=limit, source=src_filter)

    count = 0
    with console.status("[bold green]Analyzing sentiment..."):
        for post in posts:
            signal = storage.get_signal(post.id)

            # Skip if signal exists and has sentiment, unless forced
            if signal and not force and signal.sentiment_label:
                continue

            # Re-analyze using LLM
            new_pain = discovery.analyze_pain_intensity(post)

            if signal:
                # Update existing signal
                signal.sentiment_label = new_pain.sentiment_label
                signal.sentiment_intensity = new_pain.sentiment_intensity
                storage.save_signal(post.id, signal)
            else:
                # Create new signal (backfill)
                storage.save_signal(post.id, new_pain)

            # Also update post table
            post.sentiment_label = new_pain.sentiment_label
            post.sentiment_intensity = new_pain.sentiment_intensity
            storage.save_post(post)

            count += 1

    console.print(
        f"[bold green]Successfully analyzed and updated {count} posts.[/bold green]"
    )


@app.command()
def config(
    key: Optional[str] = typer.Argument(None),
    value: Optional[str] = typer.Argument(None),
):
    """View or update configuration."""
    if key and value:
        config_manager.set(key, value)
        console.print(f"[green]Set {key} = {value}[/green]")
    elif key:
        val = config_manager.get(key)
        console.print(f"{key}: {val}")
    else:
        table = Table(title="Founder Co-Pilot Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in config_manager.all.items():
            display_v = v if "key" not in k and "secret" not in k else "********"
            table.add_row(k, str(display_v))
        console.print(table)
        console.print(f"\nConfig file: {config_manager.config_path}")


@app.command()
def validate(
    post_id: str,
    deep: bool = typer.Option(
        False, "--deep", "-d", help="Use deep research (Tavily MCP) for mapping"
    ),
):
    """Deep validation logic for a specific post."""
    registry = get_registry()
    llm_name = config_manager.get("llm_provider")
    module = ValidationModule(
        llm=registry.get_llm(llm_name), storage=registry.get_storage("sqlite")
    )

    status_msg = (
        "[bold green]Performing deep research landscape mapping..."
        if deep
        else f"[bold green]Performing validation research on post {post_id}..."
    )

    with console.status(status_msg):
        try:
            report = module.validate_idea(post_id, deep=deep)
            md_content = module.format_report_markdown(report)
            console.print(Markdown(md_content))
        except Exception as e:
            console.print(f"[red]Validation failed: {e}[/red]")


@app.command()
def monitor(
    subreddits: Optional[List[str]] = typer.Option(
        None, "--sub", "-s", help="Subreddits to monitor"
    ),
    competitors: Optional[List[str]] = typer.Option(
        None, "--comp", "-c", help="Competitors to track"
    ),
):
    """Monitor subreddits for new signals and competitor mentions."""
    subs = subreddits or config_manager.get("subreddits")
    comps = competitors or ["OpenAI", "Anthropic", "Cursor", "Windsurf"]  # Defaults

    registry = get_registry()
    discovery = get_discovery_module(registry)
    llm_name = config_manager.get("llm_provider")
    module = MonitorModule(
        discovery=discovery,
        storage=registry.get_storage("sqlite"),
        llm=registry.get_llm(llm_name),
    )

    with console.status(
        f"[bold blue]Monitoring r/{', r/'.join(subs)} for mentions of {', '.join(comps)}..."
    ):
        mentions = module.monitor_competitors(subs, comps)
        new_signals = module.run_periodic_discovery(subs)

    console.print(
        Panel(
            f"Monitoring Run Complete.\n\n- Competitor Mentions Found: [bold]{mentions}[/bold]\n- New Pain Signals Found: [bold]{new_signals}[/bold]",
            title="Monitor Results",
            style="blue",
        )
    )


@app.command()
def leads(
    verify: bool = typer.Option(
        False,
        "--verify",
        "-v",
        help="Attempt to verify leads via multi-channel research",
    ),
    limit: int = typer.Option(
        50, "--limit", "-l", help="Number of leads to display/verify"
    ),
):
    """Scan for and view potential customer leads."""
    registry = get_registry()
    llm_name = config_manager.get("llm_provider")
    storage = registry.get_storage("sqlite")
    module = LeadModule(llm=registry.get_llm(llm_name), storage=storage)

    if verify:
        with console.status("[bold gold3]Verifying leads across channels..."):
            count = module.verify_leads_multi_channel(limit=limit)
            console.print(f"[green]Successfully verified {count} leads.[/green]")

    with console.status("[bold gold3]Scanning for high-intent leads..."):
        new_leads = module.scan_for_leads()

    all_leads = storage.get_leads(limit=limit)

    if not all_leads:
        console.print(
            "[yellow]No leads found yet. Try running discovery or monitoring first.[/yellow]"
        )
        return

    table = Table(title="Potential Customer Leads (Intent > 0.6)")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Author", style="magenta")
    table.add_column("Source", style="blue")
    table.add_column("Verified Profiles", style="green")
    table.add_column("Link")

    for lead in all_leads:
        profiles = ", ".join([f"{k}: {v}" for k, v in lead.verified_profiles.items()])
        table.add_row(
            f"{lead.intent_score:.2f}",
            lead.author,
            lead.source,
            profiles if profiles else "[grey]N/A[/grey]",
            lead.contact_url,
        )

    console.print(table)
    if new_leads:
        console.print(
            f"\n[bold green]Identified {len(new_leads)} new leads in this run![/bold green]"
        )


@app.command()
def outreach(
    platform: str = typer.Option(
        ..., "--platform", "-p", help="Platform for outreach (linkedin, twitter, email)"
    ),
    recipient: str = typer.Option(
        ..., "--recipient", "-r", help="Recipient name or identifier"
    ),
    template: str = typer.Option(
        "cold_introduction",
        "--template",
        "-t",
        help="Template to use (e.g., cold_introduction, linkedin_connection)",
    ),
    variables: Optional[str] = typer.Option(
        None, "--vars", "-v", help="JSON string of template variables"
    ),
    tags: Optional[List[str]] = typer.Option(None, "--tag", help="Tags for the draft"),
):
    """Generate and manage outreach message drafts."""
    storage = get_registry().get_storage("sqlite")
    module = OutreachModule(storage=storage)

    vars_dict = {}
    if variables:
        try:
            vars_dict = json.loads(variables)
        except json.JSONDecodeError:
            console.print("[red]Error: --vars must be a valid JSON string.[/red]")
            raise typer.Exit(code=1)

    with console.status("[bold blue]Generating outreach draft..."):
        draft = module.create_draft(
            platform=platform,
            recipient=recipient,
            template_name=template,
            variables=vars_dict,
            tags=tags or [],
        )

    console.print(
        Panel(
            f"[bold blue]Platform:[/bold blue] {draft.platform}\n"
            f"[bold blue]Recipient:[/bold blue] {draft.recipient}\n"
            f"[bold blue]Subject:[/bold blue] {draft.subject}\n"
            f"[bold blue]Body:[/bold blue]\n{draft.body}",
            title=f"Outreach Draft #{draft.id}",
            border_style="green",
        )
    )
    console.print(f"[bold green]Draft saved to storage.[/bold green]")


@app.command()
def export(
    type: str = typer.Option(
        ..., "--type", "-t", help="Type of data to export: 'leads' or 'reports'"
    ),
    format: str = typer.Option(
        ...,
        "--format",
        "-f",
        help="Export format: 'csv', 'md', 'hubspot', 'salesforce'",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. Defaults to a generated filename.",
    ),
):
    """Export found leads or validated reports to CSV, Markdown, or CRM formats."""
    if type not in ["leads", "reports"]:
        console.print("[red]Error: --type must be 'leads' or 'reports'.[/red]")
        raise typer.Exit(code=1)

    allowed_formats = ["csv", "md"]
    if type == "leads":
        allowed_formats.extend(["hubspot", "salesforce"])

    if format not in allowed_formats:
        console.print(
            f"[red]Error: --format for {type} must be one of {allowed_formats}.[/red]"
        )
        raise typer.Exit(code=1)

    registry = get_registry()
    storage = registry.get_storage("sqlite")
    export_module = ExportModule(storage=storage)

    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = "csv" if format in ["csv", "hubspot", "salesforce"] else "md"
        output_filename = f"{type}_{format}_{timestamp}.{ext}"
        output = Path(output_filename)

    export_count = 0
    with console.status(
        f"[bold green]Exporting {type} to {output} in {format} format...[/bold green]"
    ):
        try:
            if type == "leads":
                if format == "csv":
                    export_count = export_module.export_leads_to_csv(output)
                elif format == "md":
                    export_count = export_module.export_leads_to_md(output)
                elif format == "hubspot":
                    export_count = export_module.export_leads_to_hubspot_csv(output)
                elif format == "salesforce":
                    export_count = export_module.export_leads_to_salesforce_csv(output)
            elif type == "reports":
                if format == "csv":
                    export_count = export_module.export_reports_to_csv(output)
                elif format == "md":
                    export_count = export_module.export_reports_to_md(output)

            console.print(
                f"[bold green]Successfully exported {export_count} {type} to {output}[/bold green]"
            )
        except Exception as e:
            console.print(f"[red]Error during export: {e}[/red]")
            raise typer.Exit(code=1)


@app.command()
def persona(
    persona_type: str = typer.Option(
        "startup_founder",
        "-p",
        "--type",
        help="Persona type to generate (default: startup_founder)",
    ),
    limit: int = typer.Option(
        5, "--limit", "-n", help="Number of personas to generate"
    ),
):
    """Generate target customer profiles based on top opportunities."""
    registry = get_registry()
    storage = registry.get_storage("sqlite")
    scoring = ScoringModule(storage)
    from ..modules.persona import PersonaModule

    console.print(
        f"[bold blue]Generating {limit} {persona_type} personas...[/bold blue]"
    )

    # Get top opportunities for persona generation
    scored_posts = storage.get_opportunity_scores(limit=limit, min_score=0.5)

    if not scored_posts:
        console.print(
            "[yellow]No opportunities with sufficient score found. Run discovery first.[/yellow]"
        )
        return

    # Generate personas
    module = PersonaModule(
        llm=registry.get_llm(config_manager.get("llm_provider")), storage=storage
    )
    profiles = module.generate_profiles_for_opportunities(
        scored_posts, persona_type=persona_type
    )

    table = Table(title=f"Generated {persona_type.replace('_', ' ')} personas")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="magenta")
    table.add_column("Industry", style="green")
    table.add_column("Budget", style="yellow")
    table.add_column("Communication", style="blue")

    for profile in profiles:
        table.add_row(
            profile.persona.name,
            profile.persona.role,
            profile.persona.industry,
            profile.persona.budget,
            profile.persona.preferred_communication,
        )

    console.print(table)
    console.print(
        f"\n[bold green]Generated {len(profiles)} personas. Use them for personalized outreach campaigns![/bold green]"
    )


crm_app = typer.Typer(name="crm", help="CRM Integrations and OAuth management.")


@crm_app.command("auth-hubspot")
def crm_auth_hubspot(
    client_id: Optional[str] = typer.Option(None, help="HubSpot Client ID"),
    client_secret: Optional[str] = typer.Option(None, help="HubSpot Client Secret"),
    redirect_uri: Optional[str] = typer.Option(None, help="HubSpot Redirect URI"),
):
    """Initiate HubSpot OAuth flow to get access and refresh tokens."""
    # Temporarily configure HubSpotProvider
    hubspot = HubSpotProvider()

    # Use provided values or config_manager/env for setup
    cfg = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    # Filter out None values
    cfg = {k: v for k, v in cfg.items() if v is not None}

    # Configure with what's available
    hubspot.configure(cfg)

    # Fallback to config manager if not provided
    if not hubspot._client_id:
        hubspot._client_id = config_manager.get("hubspot_client_id") or os.getenv(
            "HUBSPOT_CLIENT_ID"
        )
    if not hubspot._client_secret:
        hubspot._client_secret = config_manager.get(
            "hubspot_client_secret"
        ) or os.getenv("HUBSPOT_CLIENT_SECRET")
    if not hubspot._redirect_uri:
        hubspot._redirect_uri = config_manager.get("hubspot_redirect_uri") or os.getenv(
            "HUBSPOT_REDIRECT_URI", "http://localhost:8000/hubspot-oauth-callback"
        )

    if (
        not hubspot._client_id
        or not hubspot._client_secret
        or not hubspot._redirect_uri
    ):
        console.print(
            "[red]Error: HubSpot Client ID, Client Secret, and Redirect URI must be configured.[/red]"
        )
        console.print(
            "[yellow]Please provide them as options or set them in your config/environment.[/yellow]"
        )
        raise typer.Exit(code=1)

    auth_url = hubspot.get_authorization_url()
    console.print(
        f"[bold blue]Please open this URL in your browser to authorize HubSpot:[/bold blue]"
    )
    console.print(f"[link={auth_url}]{auth_url}[/link]")
    console.print(
        "\n[bold yellow]After authorization, you will be redirected to your redirect URI.[/bold yellow]"
    )
    console.print(
        "[bold yellow]Copy the 'code' parameter from the URL in your browser and paste it here.[/bold yellow]"
    )

    auth_code = typer.prompt("Paste the authorization code here")

    with console.status(
        "[bold green]Exchanging authorization code for tokens...[/bold green]"
    ):
        try:
            hubspot.exchange_code_for_tokens(auth_code)

            # Persist tokens to config manager
            config_manager.set("hubspot_access_token", hubspot._access_token)
            config_manager.set("hubspot_refresh_token", hubspot._refresh_token)
            config_manager.set("hubspot_access_token_expires_at", hubspot._expires_at)
            config_manager.save()

            console.print(
                "[bold green]HubSpot OAuth successful! Tokens saved.[/bold green]"
            )
        except Exception as e:
            console.print(f"[red]Error during token exchange: {e}[/red]")
            raise typer.Exit(code=1)


@crm_app.command("auth-salesforce")
def crm_auth_salesforce(
    client_id: Optional[str] = typer.Option(None, help="SalesForce Client ID"),
    client_secret: Optional[str] = typer.Option(None, help="SalesForce Client Secret"),
    redirect_uri: Optional[str] = typer.Option(None, help="SalesForce Redirect URI"),
):
    """Initiate SalesForce OAuth flow to get access and refresh tokens."""
    # Temporarily configure SalesForceProvider
    salesforce = SalesForceProvider()

    # Use provided values or config_manager/env for setup
    cfg = {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    # Filter out None values
    cfg = {k: v for k, v in cfg.items() if v is not None}

    # Configure with what's available
    salesforce.configure(cfg)

    # Fallback to config manager if not provided
    if not salesforce._client_id:
        salesforce._client_id = config_manager.get("salesforce_client_id") or os.getenv(
            "SALESFORCE_CLIENT_ID"
        )
    if not salesforce._client_secret:
        salesforce._client_secret = config_manager.get(
            "salesforce_client_secret"
        ) or os.getenv("SALESFORCE_CLIENT_SECRET")
    if not salesforce._redirect_uri:
        salesforce._redirect_uri = config_manager.get("salesforce_redirect_uri") or os.getenv(
            "SALESFORCE_REDIRECT_URI", "http://localhost:8000/salesforce-oauth-callback"
        )

    if (
        not salesforce._client_id
        or not salesforce._client_secret
        or not salesforce._redirect_uri
    ):
        console.print(
            "[red]Error: SalesForce Client ID, Client Secret, and Redirect URI must be configured.[/red]"
        )
        console.print(
            "[yellow]Please provide them as options or set them in your config/environment.[/yellow]"
        )
        raise typer.Exit(code=1)

    auth_url = salesforce.get_authorization_url()
    console.print(
        f"[bold blue]Please open this URL in your browser to authorize SalesForce:[/bold blue]"
    )
    console.print(f"[link={auth_url}]{auth_url}[/link]")
    console.print(
        "\n[bold yellow]After authorization, you will be redirected to your redirect URI.[/bold yellow]"
    )
    console.print(
        "[bold yellow]Copy the 'code' parameter from the URL in your browser and paste it here.[/bold yellow]"
    )

    auth_code = typer.prompt("Paste the authorization code here")

    with console.status(
        "[bold green]Exchanging authorization code for tokens...[/bold green]"
    ):
        try:
            salesforce.exchange_code_for_tokens(auth_code)

            # Persist tokens to config manager
            config_manager.set("salesforce_access_token", salesforce._access_token)
            config_manager.set("salesforce_refresh_token", salesforce._refresh_token)
            config_manager.set("salesforce_instance_url", salesforce._instance_url)
            config_manager.set("salesforce_access_token_expires_at", salesforce._expires_at)
            config_manager.save()

            console.print(
                "[bold green]SalesForce OAuth successful! Tokens saved.[/bold green]"
            )
        except Exception as e:
            console.print(f"[red]Error during token exchange: {e}[/red]")
            raise typer.Exit(code=1)


app.add_typer(crm_app, name="crm")

if __name__ == "__main__":
    app()
