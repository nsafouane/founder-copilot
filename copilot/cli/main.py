import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import List, Optional
import os

from ..core.config import ConfigManager
from ..providers.registry import ProviderRegistry
from ..providers.groq import GroqProvider
from ..providers.reddit_scraper import RedditScraper
from ..providers.storage.sqlite_provider import SQLiteProvider
from ..modules.discovery import DiscoveryModule

app = typer.Typer(help="Founder Co-Pilot CLI - Discovery and Validation Engine.")
console = Console()
config_manager = ConfigManager()

def get_discovery_module() -> DiscoveryModule:
    registry = ProviderRegistry()
    
    # Setup Storage
    db_path = config_manager.get("db_path")
    storage = SQLiteProvider(db_path=db_path)
    registry.register_storage(storage)
    
    # Setup LLM
    llm_name = config_manager.get("llm_provider")
    if llm_name == "groq":
        api_key = config_manager.get("groq_api_key") or os.getenv("GROQ_API_KEY")
        llm = GroqProvider(api_key=api_key)
        registry.register_llm(llm)
    else:
        # Fallback/Other LLMs could be added here
        raise ValueError(f"Unsupported LLM provider: {llm_name}")
        
    # Setup Scraper
    scraper_name = config_manager.get("scraper_provider")
    if scraper_name == "reddit":
        scraper = RedditScraper(
            client_id=config_manager.get("reddit_client_id") or os.getenv("REDDIT_CLIENT_ID"),
            client_secret=config_manager.get("reddit_client_secret") or os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=config_manager.get("reddit_user_agent")
        )
        registry.register_scraper(scraper)
    else:
        raise ValueError(f"Unsupported Scraper provider: {scraper_name}")
        
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
    
    with console.status(f"[bold green]Discovering pain points in r/{', r/'.join(subs)}..."):
        module = get_discovery_module()
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
    """Placeholder for Phase 4: Validation logic."""
    console.print(Panel(f"Validation logic for post [bold]{post_id}[/bold] will be implemented in detail later in Phase 4.", title="Validate"))

@app.command()
def monitor():
    """Placeholder for Phase 4: Monitoring logic."""
    console.print(Panel("Monitoring subreddits for new signals...", title="Monitor"))

@app.command()
def leads():
    """View saved leads and potential customers."""
    console.print(Panel("Leads management dashboard (SQLite)", title="Leads"))

if __name__ == "__main__":
    app()
