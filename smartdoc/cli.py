"""
Command-line interface for SmartDoc2.
"""

import click
import logging
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


@click.group()
def cli():
    """SmartDoc2: LlamaIndex-powered documentation system."""
    pass


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option('--no-schematics', is_flag=True, help='Skip schematic analysis')
@click.option('--query', type=str, help='Initial query context for schematic analysis')
def index_pdf(pdf_path, no_schematics, query):
    """Index a PDF document."""
    console.print(f"[bold blue]Indexing PDF:[/bold blue] {pdf_path}")
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        ingestor = PDFIngestor(registry, chroma)
        
        result = ingestor.ingest(
            pdf_path,
            analyze_schematics=not no_schematics,
            initial_query=query
        )
        
        console.print(f"[bold green]✓ Success![/bold green]")
        console.print(f"  Chunks added: {result['chunks_added']}")
        console.print(f"  Text chunks: {result['metadata']['text_chunks']}")
        console.print(f"  Schematic chunks: {result['metadata']['schematic_chunks']}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument('repo_url')
@click.option('--branch', type=str, help='Branch to clone (default: main/master)')
def fetch_repo(repo_url, branch):
    """Fetch and index a GitHub repository."""
    console.print(f"[bold blue]Fetching repository:[/bold blue] {repo_url}")
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        ingestor = GitHubIngestor(registry, chroma)
        
        kwargs = {}
        if branch:
            kwargs['branch'] = branch
        
        result = ingestor.ingest(repo_url, **kwargs)
        
        console.print(f"[bold green]✓ Success![/bold green]")
        console.print(f"  Files processed: {result['files_processed']}")
        console.print(f"  Chunks added: {result['chunks_added']}")
        console.print(f"  Commit: {result['commit_sha'][:8]}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument('url')
def web(url):
    """Scrape and index a web page."""
    console.print(f"[bold blue]Scraping web page:[/bold blue] {url}")
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        ingestor = WebIngestor(registry, chroma)
        
        result = ingestor.ingest(url)
        
        console.print(f"[bold green]✓ Success![/bold green]")
        console.print(f"  Title: {result['metadata'].get('title', 'N/A')}")
        console.print(f"  Chunks added: {result['chunks_added']}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument('query_text')
@click.option('--reprocess', is_flag=True, help='Automatically reprocess schematics if needed')
@click.option('--source', type=str, help='Filter by source path/URL')
@click.option('--type', 'source_type', type=click.Choice(['pdf', 'github', 'web']), help='Filter by source type')
def query(query_text, reprocess, source, source_type):
    """Query the knowledge base."""
    console.print(f"[bold blue]Querying:[/bold blue] {query_text}\n")
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        engine = QueryEngine(registry, chroma)
        
        if reprocess:
            results = engine.query_with_reprocess(query_text)
        else:
            results = engine.query(
                query_text,
                source_filter=source,
                source_type_filter=source_type
            )
        
        # Display results
        console.print(f"[bold]Confidence:[/bold] {results['confidence']:.2f}")
        console.print(f"[bold]Total Results:[/bold] {results['total_results']}\n")
        
        if results.get('should_reprocess'):
            console.print(f"[yellow]⚠️  {results['reprocess_suggestion']}[/yellow]")
            console.print("[yellow]Run with --reprocess flag to enable automatic reprocessing[/yellow]\n")
        
        if results.get('reprocessed'):
            console.print("[green]🔄 Results enhanced with schematic reprocessing[/green]\n")
        
        # Display top results
        for idx, result in enumerate(results['results'], 1):
            console.print(f"[bold cyan]{idx}. {result['citation']}[/bold cyan]")
            console.print(f"   Score: {result['score']:.2f}")
            
            content = result['content']
            if len(content) > 300:
                content = content[:300] + "..."
            console.print(f"   {content}\n")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
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
            sources = registry.list_sources(source_type)
        
        if not sources:
            console.print("[yellow]No sources found[/yellow]")
            return
        
        # Create table
        table = Table(title="Indexed Sources")
        table.add_column("Type", style="cyan")
        table.add_column("Source", style="white")
        table.add_column("Status", style="green")
        table.add_column("Indexed", style="blue")
        table.add_column("Size", style="magenta")
        
        for source in sources:
            size_str = f"{source['file_size'] / 1024 / 1024:.1f}MB" if source['file_size'] else "N/A"
            table.add_row(
                source['source_type'],
                source['source_path'][:60] + "..." if len(source['source_path']) > 60 else source['source_path'],
                source['status'],
                source['indexed_at'],
                size_str
            )
        
        console.print(table)
        console.print(f"\n[bold]Total sources:[/bold] {len(sources)}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
def stats():
    """Display database statistics."""
    try:
        registry = Registry()
        chroma = ChromaManager()
        
        # Registry stats
        reg_stats = registry.get_stats()
        
        # ChromaDB stats
        chroma_stats = chroma.get_stats()
        
        console.print("[bold cyan]SmartDoc2 Statistics[/bold cyan]\n")
        
        console.print("[bold]Registry:[/bold]")
        console.print(f"  Total sources: {reg_stats['total_sources']}")
        console.print(f"  Cached schematics: {reg_stats['cached_schematics']}")
        
        if reg_stats['sources_by_type']:
            console.print("\n  Sources by type:")
            for source_type in reg_stats['sources_by_type']:
                console.print(f"    {source_type['source_type']}: {source_type['count']}")
        
        console.print(f"\n[bold]ChromaDB:[/bold]")
        console.print(f"  Total documents: {chroma_stats['total_documents']}")
        console.print(f"  Total sources: {chroma_stats['total_sources']}")
        console.print(f"  Collection: {chroma_stats['collection_name']}")
        
        if chroma_stats.get('documents_by_type'):
            console.print("\n  Documents by type:")
            for doc_type, count in chroma_stats['documents_by_type'].items():
                console.print(f"    {doc_type}: {count}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.argument('source_path')
def remove(source_path):
    """Remove a source from the database."""
    console.print(f"[bold yellow]Removing source:[/bold yellow] {source_path}")
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        
        # Check if source exists
        source = registry.get_source(source_path)
        if not source:
            console.print("[bold red]✗ Source not found[/bold red]")
            return
        
        # Confirm
        if not click.confirm("Are you sure you want to remove this source?"):
            console.print("Cancelled")
            return
        
        # Remove from ChromaDB
        chroma.delete_source(source_path)
        
        # Remove from registry
        registry.delete_source(source_path)
        
        console.print("[bold green]✓ Source removed[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


@cli.command()
@click.option('--confirm', is_flag=True, help='Confirm reset without prompting')
def reset(confirm):
    """Reset the entire database (⚠️  destructive!)."""
    console.print("[bold red]⚠️  WARNING: This will delete ALL indexed data![/bold red]")
    
    if not confirm:
        if not click.confirm("Are you ABSOLUTELY sure?"):
            console.print("Cancelled")
            return
    
    try:
        registry = Registry()
        chroma = ChromaManager()
        
        # Reset ChromaDB
        chroma.reset_collection()
        
        # Delete registry database
        import os
        from .config import REGISTRY_DB
        if os.path.exists(REGISTRY_DB):
            os.remove(REGISTRY_DB)
        
        # Reinitialize
        registry = Registry()
        
        console.print("[bold green]✓ Database reset complete[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()

