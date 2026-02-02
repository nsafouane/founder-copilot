import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from typing import List, Optional
import os

from ..core.config import ConfigManager
from ..providers.registry import ProviderRegistry
from ..providers.groq import GroqProvider
from ..providers.reddit_scraper import RedditScraper
from ..providers.storage.sqlite_provider import SQLiteProvider
from ..modules.discovery import DiscoveryModule
from ..modules.validation import ValidationModule
from ..modules.monitor import MonitorModule
from ..modules.leads import LeadModule

app = typer.Typer(help="Founder Co-Pilot CLI - Discovery and Validation Engine.")
console = Console()
config_manager = ConfigManager()

def get_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    
    # Setup Storage
    db_path = config_manager.get("db_path")
    storage = SQLiteProvider(db_path=db_path)
    storage.initialize()
    registry.register_storage(storage)
    
    # Setup LLM
    llm_name = config_manager.get("llm_provider")
    if llm_name == "groq":
        api_key = config_manager.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        llm = GroqProvider()
        llm.configure({"api_key": api_key})
        registry.register_llm(llm)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_name}")
        
    # Setup Scraper
    scraper_name = config_manager.get("scraper_provider")
    if scraper_name == "reddit":
        scraper = RedditScraper()
        scraper.configure({
            "client_id": config_manager.get("reddit_client_id") or os.getenv("REDDIT_CLIENT_ID"),
            "client_secret": config_manager.get("reddit_client_secret") or os.getenv("REDDIT_CLIENT_SECRET"),
            "user_agent": config_manager.get("reddit_user_agent")
        })
        registry.register_scraper(scraper)
    else:
        raise ValueError(f"Unsupported Scraper provider: {scraper_name}")
        
    return registry

def get_discovery_module(registry: ProviderRegistry) -> DiscoveryModule:
    llm_name = config_manager.get("llm_provider")
    scraper_name = config_manager.get("scraper_provider")
    return DiscoveryModule(
        scraper=registry.get_scraper(scraper_name),
        llm=registry.get_llm(llm_name),
        storage=registry.get_storage("sqlite")
    )

@app.command()
def discover(
    subreddits: Optional[List[str]] = typer.Option(None, "--sub", "-s", help="Subreddits to search"),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit per subreddit"),
    min_score: float = typer.Option(0.4, "--min-score", "-m", help="Minimum composite score (0.0-1.0)")
):
    """Discover high-signal pain points from social media."""
    subs = subreddits or config_manager.get("subreddits")
    registry = get_registry()
    
    with console.status(f"[bold green]Discovering pain points in r/{', r/'.join(subs)}..."):
        module = get_discovery_module(registry)
        results = module.discover(subs, min_score=min_score)
        
    if not results:
        console.print("[yellow]No high-signal pain points found with current criteria.[/yellow]")
        return

    table = Table(title="Discovered Opportunity Signals")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Subreddit", style="green")
    table.add_column("Pain Intensity", justify="right")
    
    for post, pain in results:
        table.add_row(
            f"{pain.composite_value:.2f}",
            post.title[:60] + "..." if len(post.title) > 60 else post.title,
            f"r/{post.subreddit}",
            f"{pain.score:.2f}"
        )
        
    console.print(table)
    console.print(f"\n[bold green]Found {len(results)} signals. Data saved to {config_manager.get('db_path')}[/bold green]")

@app.command()
def config(
    key: Optional[str] = typer.Argument(None),
    value: Optional[str] = typer.Argument(None)
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
def validate(post_id: str):
    """Deep validation logic for a specific post."""
    registry = get_registry()
    llm_name = config_manager.get("llm_provider")
    module = ValidationModule(
        llm=registry.get_llm(llm_name),
        storage=registry.get_storage("sqlite")
    )
    
    with console.status(f"[bold green]Performing deep research on post {post_id}..."):
        try:
            report = module.validate_idea(post_id)
            md_content = module.format_report_markdown(report)
            console.print(Markdown(md_content))
        except Exception as e:
            console.print(f"[red]Validation failed: {e}[/red]")

@app.command()
def monitor(
    subreddits: Optional[List[str]] = typer.Option(None, "--sub", "-s", help="Subreddits to monitor"),
    competitors: Optional[List[str]] = typer.Option(None, "--comp", "-c", help="Competitors to track")
):
    """Monitor subreddits for new signals and competitor mentions."""
    subs = subreddits or config_manager.get("subreddits")
    comps = competitors or ["OpenAI", "Anthropic", "Cursor", "Windsurf"] # Defaults
    
    registry = get_registry()
    discovery = get_discovery_module(registry)
    module = MonitorModule(discovery=discovery, storage=registry.get_storage("sqlite"))
    
    with console.status(f"[bold blue]Monitoring r/{', r/'.join(subs)} for mentions of {', '.join(comps)}..."):
        mentions = module.monitor_competitors(subs, comps)
        new_signals = module.run_periodic_discovery(subs)
        
    console.print(Panel(
        f"Monitoring Run Complete.\n\n- Competitor Mentions Found: [bold]{mentions}[/bold]\n- New Pain Signals Found: [bold]{new_signals}[/bold]",
        title="Monitor Results",
        style="blue"
    ))

@app.command()
def leads():
    """Scan for and view potential customer leads."""
    registry = get_registry()
    llm_name = config_manager.get("llm_provider")
    storage = registry.get_storage("sqlite")
    module = LeadModule(llm=registry.get_llm(llm_name), storage=storage)
    
    with console.status("[bold gold3]Scanning for high-intent leads..."):
        new_leads = module.scan_for_leads()
    
    all_leads = storage.get_leads(limit=50)
    
    if not all_leads:
        console.print("[yellow]No leads found yet. Try running discovery or monitoring first.[/yellow]")
        return

    table = Table(title="Potential Customer Leads (Intent > 0.6)")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Author", style="magenta")
    table.add_column("Needs Summary", style="green")
    table.add_column("Link")
    
    for lead in all_leads:
        table.add_row(
            f"{lead.intent_score:.2f}",
            lead.author,
            lead.content_snippet[:80] + "..." if len(lead.content_snippet) > 80 else lead.content_snippet,
            lead.contact_url
        )
        
    console.print(table)
    if new_leads:
        console.print(f"\n[bold green]Identified {len(new_leads)} new leads in this run![/bold green]")

if __name__ == "__main__":
    app()
