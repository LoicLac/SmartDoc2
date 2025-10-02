"""
Command-line interface for SmartDoc2.
"""

import click
import logging
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .core.registry import Registry
from .core.chroma_client import ChromaManager
from .ingestion.pdf_ingestor import PDFIngestor
from .ingestion.github_ingestor import GitHubIngestor
from .ingestion.web_ingestor import WebIngestor
from .query.query_engine import QueryEngine
from .config import LOG_LEVEL, LOG_FORMAT

# Setup logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()

# Config file for storing custom root path
ROOT_CONFIG_FILE = Path.home() / ".smartdoc_root"


def get_default_root() -> Path:
    """Get the default root path for scanning workspaces."""
    # Check if custom root is set
    if ROOT_CONFIG_FILE.exists():
        try:
            custom_root = ROOT_CONFIG_FILE.read_text().strip()
            custom_path = Path(custom_root).expanduser().resolve()
            if custom_path.exists():
                return custom_path
        except Exception:
            pass
    
    # Default to ~/Code
    default_root = Path.home() / "Code"
    return default_root


def set_default_root(root_path: str) -> bool:
    """Set the default root path for scanning workspaces."""
    try:
        root = Path(root_path).expanduser().resolve()
        if not root.exists():
            console.print(f"[bold red]✗ Directory does not exist:[/bold red] {root}")
            return False
        
        ROOT_CONFIG_FILE.write_text(str(root))
        console.print(f"[bold green]✓ Default root set to:[/bold green] {root}")
        console.print(f"[dim]Stored in: {ROOT_CONFIG_FILE}[/dim]")
        return True
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        return False


@click.group()
def cli():
    """SmartDoc2: LlamaIndex-powered documentation system."""
    pass


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--no-schematics', is_flag=True, help='Skip schematic analysis')
@click.option('--query', type=str, help='Query context for better schematic analysis')
def index_pdf(pdf_path, no_schematics, query):
    """Index a PDF document (datasheet, manual, etc.)."""
    try:
        console.print(f"[bold blue]Indexing PDF:[/bold blue] {pdf_path}")
        
        registry = Registry()
        chroma = ChromaManager()
        ingestor = PDFIngestor(registry, chroma)
        
        ingestor.ingest(
            pdf_path,
            analyze_schematics=not no_schematics,
            query_context=query
        )
        
        console.print(f"[bold green]✓ Successfully indexed:[/bold green] {pdf_path}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to index PDF")
        raise click.Abort()


@cli.command()
@click.argument('repo_url')
@click.option('--branch', type=str, help='Branch to clone (default: main/master)')
def fetch_repo(repo_url, branch):
    """Clone and index a GitHub repository."""
    try:
        console.print(f"[bold blue]Fetching repository:[/bold blue] {repo_url}")
        
        registry = Registry()
        chroma = ChromaManager()
        ingestor = GitHubIngestor(registry, chroma)
        
        ingestor.ingest(repo_url, branch=branch)
        
        console.print(f"[bold green]✓ Successfully indexed:[/bold green] {repo_url}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to fetch repository")
        raise click.Abort()


@cli.command()
@click.argument('url')
def web(url):
    """Scrape and index a web page."""
    try:
        console.print(f"[bold blue]Scraping web page:[/bold blue] {url}")
        
        registry = Registry()
        chroma = ChromaManager()
        ingestor = WebIngestor(registry, chroma)
        
        ingestor.ingest(url)
        
        console.print(f"[bold green]✓ Successfully indexed:[/bold green] {url}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to scrape web page")
        raise click.Abort()


@cli.command()
@click.argument('query_text')
@click.option('--reprocess', is_flag=True, help='Automatically reprocess schematics if needed')
@click.option('--source', type=str, help='Filter by source path')
@click.option('--type', 'source_type', type=click.Choice(['pdf', 'github', 'web']), help='Filter by source type')
def query(query_text, reprocess, source, source_type):
    """Query the documentation database."""
    try:
        chroma = ChromaManager()
        registry = Registry()
        engine = QueryEngine(chroma, registry)
        
        # Build filter
        filter_dict = {}
        if source:
            filter_dict['source'] = source
        if source_type:
            filter_dict['source_type'] = source_type
        
        # Query with or without reprocessing
        if reprocess:
            results = engine.query_with_reprocess(query_text, where=filter_dict if filter_dict else None)
        else:
            results = engine.query(query_text, where=filter_dict if filter_dict else None)
        
        # Display results
        if results:
            console.print(f"\n[bold]Query:[/bold] {query_text}\n")
            console.print(engine.format_results(results))
        else:
            console.print("[yellow]No results found.[/yellow]")
            
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Query failed")
        raise click.Abort()


@cli.command()
@click.option('--type', 'source_type', type=click.Choice(['pdf', 'github', 'web', 'all']), default='all')
def list_sources(source_type):
    """List all indexed sources."""
    try:
        registry = Registry()
        
        if source_type == 'all':
            sources = registry.list_sources()
        else:
            sources = registry.list_sources(source_type=source_type)
        
        if not sources:
            console.print("[yellow]No sources indexed yet.[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Indexed Sources ({len(sources)} total)")
        table.add_column("#", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Source", style="green")
        table.add_column("Indexed", style="blue")
        table.add_column("Status", style="yellow")
        
        for idx, source in enumerate(sources, 1):
            source_type = source.get('source_type', 'unknown')
            source_path = source.get('source_path', 'N/A')
            indexed_at = source.get('indexed_at', 'N/A')
            status = source.get('status', 'unknown')
            
            table.add_row(
                str(idx),
                source_type,
                source_path,
                indexed_at,
                status
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to list sources")
        raise click.Abort()


@cli.command()
def stats():
    """Display database statistics."""
    try:
        registry = Registry()
        chroma = ChromaManager()
        
        # Get stats
        sources = registry.list_sources()
        sources_by_type = {}
        for source in sources:
            stype = source.get('source_type', 'unknown')
            sources_by_type[stype] = sources_by_type.get(stype, 0) + 1
        
        # ChromaDB stats
        try:
            collection = chroma.get_collection()
            doc_count = collection.count()
        except:
            doc_count = 0
        
        # Display stats
        console.print("\n[bold]SmartDoc Workspace Statistics[/bold]")
        console.print("=" * 80)
        
        console.print(f"\n[bold cyan]Registry:[/bold cyan]")
        console.print(f"  Total sources: {len(sources)}")
        console.print(f"  Sources by type:")
        for stype, count in sources_by_type.items():
            console.print(f"    {stype}: {count}")
        
        console.print(f"\n[bold cyan]ChromaDB:[/bold cyan]")
        console.print(f"  Total documents: {doc_count}")
        
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to get stats")
        raise click.Abort()


@cli.command()
@click.argument('source_path')
def logs(source_path):
    """Show processing logs for a source."""
    try:
        registry = Registry()
        logs = registry.get_processing_logs(source_path)
        
        if not logs:
            console.print(f"[yellow]No logs found for:[/yellow] {source_path}")
            return
        
        console.print(f"\n[bold]Processing Logs:[/bold] {source_path}")
        console.print("=" * 80)
        
        for log in logs:
            # Status emoji
            status_emoji = {
                'success': '✓',
                'warning': '⚠',
                'failed': '✗',
                'info': 'ℹ'
            }.get(log['status'], '•')
            
            # Timestamp
            timestamp = log.get('timestamp', 'N/A')
            
            # Step name
            step = log.get('step', 'unknown').upper()
            
            # Status
            status = log.get('status', 'unknown').upper()
            
            console.print(f"\n[bold][{timestamp}] {step}[/bold]")
            console.print(f"Status: {status_emoji} {status}")
            
            # Message
            message = log.get('message')
            if message:
                console.print(f"Message: {message}")
            
            # Details
            details = log.get('details')
            if details:
                import json
                try:
                    details_dict = json.loads(details) if isinstance(details, str) else details
                    console.print("Details:")
                    for key, value in details_dict.items():
                        console.print(f"  - {key}: {value}")
                except:
                    console.print(f"Details: {details}")
        
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to get logs")
        raise click.Abort()


@cli.command()
@click.argument('source_path')
def remove(source_path):
    """Remove a source from the database."""
    try:
        console.print(f"[bold yellow]Removing source:[/bold yellow] {source_path}")
        
        # Confirm
        if not click.confirm("Are you sure? This will delete all associated documents."):
            console.print("[dim]Cancelled.[/dim]")
            return
        
        registry = Registry()
        chroma = ChromaManager()
        
        # Get source info
        sources = registry.list_sources()
        source_info = None
        for s in sources:
            if s['source_path'] == source_path:
                source_info = s
                break
        
        if not source_info:
            console.print(f"[bold red]✗ Source not found:[/bold red] {source_path}")
            return
        
        # Delete from ChromaDB
        try:
            collection = chroma.get_collection()
            results = collection.get(where={"source": source_path})
            if results['ids']:
                collection.delete(ids=results['ids'])
                console.print(f"[green]✓ Deleted {len(results['ids'])} documents from ChromaDB[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Warning: Could not delete from ChromaDB: {e}[/yellow]")
        
        # Delete from registry
        registry.remove_source(source_path)
        
        console.print(f"[bold green]✓ Successfully removed:[/bold green] {source_path}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to remove source")
        raise click.Abort()


@cli.command()
@click.option('--confirm', is_flag=True, help='Confirm reset without prompting')
def reset(confirm):
    """Reset the entire database (⚠️ destructive!)."""
    try:
        if not confirm:
            console.print("[bold red]⚠️  WARNING: This will delete ALL indexed data![/bold red]")
            if not click.confirm("Are you absolutely sure?"):
                console.print("[dim]Cancelled.[/dim]")
                return
        
        from .config import REGISTRY_DB
        
        # Delete registry
        registry_path = Path(REGISTRY_DB)
        if registry_path.exists():
            os.remove(registry_path)
            console.print("[green]✓ Deleted registry database[/green]")
        
        # Reset ChromaDB (will be recreated on next use)
        console.print("[bold green]✓ Database reset complete[/bold green]")
        console.print("[dim]Run any index command to recreate the database[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        logger.exception("Failed to reset database")
        raise click.Abort()


@cli.command()
@click.argument('root_path')
def set_root(root_path):
    """Set the default root directory for web-manager scanning."""
    if set_default_root(root_path):
        console.print(f"\n[dim]Use 'smartdoc web-manager' to scan workspaces in: {Path(root_path).expanduser().resolve()}[/dim]")
    else:
        raise click.Abort()


@cli.command()
def show_root():
    """Show the current default root directory."""
    root = get_default_root()
    if ROOT_CONFIG_FILE.exists():
        console.print(f"[bold]Custom root:[/bold] {root}")
        console.print(f"[dim]Stored in: {ROOT_CONFIG_FILE}[/dim]")
    else:
        console.print(f"[bold]Default root:[/bold] {root}")
        console.print(f"[dim]Set custom root with: smartdoc set-root <path>[/dim]")


@cli.command()
@click.option('--root', type=click.Path(exists=True), default=None, help='Root directory to scan (overrides default)')
@click.option('--port', type=int, default=7860, help='Port to run server on')
@click.option('--share', is_flag=True, help='Create public share link')
def web_manager(root, port, share):
    """Launch web-based database manager to view and manage multiple SmartDoc databases."""
    # Suppress verbose logging from httpx and gradio
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("gradio").setLevel(logging.WARNING)
    
    # Disable Gradio analytics and telemetry
    os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
    os.environ["GRADIO_SERVER_NAME"] = "127.0.0.1"
    
    # Determine root path
    if root:
        root_path = Path(root).resolve()
    else:
        root_path = get_default_root()
    
    console.print(f"\n[bold blue]🌐 SmartDoc Database Manager[/bold blue]")
    console.print(f"[dim]Root:[/dim] {root_path}")
    console.print(f"[dim]Server:[/dim] http://127.0.0.1:{port}\n")
    
    if not root_path.exists():
        console.print(f"[bold red]✗ Root directory does not exist:[/bold red] {root_path}")
        console.print(f"[dim]Set a valid root with: smartdoc set-root <path>[/dim]")
        raise click.Abort()
    
    try:
        from .web.ui import launch_ui
        launch_ui(str(root_path), share=share, server_port=port)
    except ImportError as e:
        console.print(f"[bold red]✗ Missing dependency:[/bold red] {e}")
        console.print("[yellow]Run: pip install gradio[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
