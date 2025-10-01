#!/usr/bin/env python3
"""
SmartDoc2 MCP Server for Cursor/Claude integration.
"""

import json
import sys
from typing import Any, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from smartdoc.core.registry import Registry
from smartdoc.core.chroma_client import ChromaManager
from smartdoc.ingestion.pdf_ingestor import PDFIngestor
from smartdoc.ingestion.github_ingestor import GitHubIngestor
from smartdoc.ingestion.web_ingestor import WebIngestor
from smartdoc.query.query_engine import QueryEngine


def read_request():
    """Read JSON-RPC request from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return None


def write_response(response: Dict[str, Any]):
    """Write JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def handle_index_pdf(arguments: Dict[str, Any]) -> str:
    """Handle PDF indexing."""
    pdf_path = arguments.get("pdf_path")
    analyze_schematics = arguments.get("analyze_schematics", True)
    initial_query = arguments.get("initial_query")
    
    registry = Registry()
    chroma = ChromaManager()
    ingestor = PDFIngestor(registry, chroma)
    
    result = ingestor.ingest(
        pdf_path,
        analyze_schematics=analyze_schematics,
        initial_query=initial_query
    )
    
    return f"""✅ Successfully indexed PDF: {pdf_path}
- Total chunks: {result['chunks_added']}
- Text chunks: {result['metadata']['text_chunks']}
- Schematic chunks: {result['metadata']['schematic_chunks']}
- Pages: {result['metadata']['pages']}"""


def handle_fetch_repo(arguments: Dict[str, Any]) -> str:
    """Handle GitHub repository indexing."""
    repo_url = arguments.get("repo_url")
    branch = arguments.get("branch")
    
    registry = Registry()
    chroma = ChromaManager()
    ingestor = GitHubIngestor(registry, chroma)
    
    kwargs = {}
    if branch:
        kwargs['branch'] = branch
    
    result = ingestor.ingest(repo_url, **kwargs)
    
    return f"""✅ Successfully indexed repository: {repo_url}
- Files processed: {result['files_processed']}
- Total chunks: {result['chunks_added']}
- Commit: {result['commit_sha'][:8]}
- Branch: {result['metadata']['branch']}"""


def handle_index_web(arguments: Dict[str, Any]) -> str:
    """Handle web page indexing."""
    url = arguments.get("url")
    
    registry = Registry()
    chroma = ChromaManager()
    ingestor = WebIngestor(registry, chroma)
    
    result = ingestor.ingest(url)
    
    return f"""✅ Successfully indexed web page: {url}
- Title: {result['metadata'].get('title', 'N/A')}
- Total chunks: {result['chunks_added']}"""


def handle_query(arguments: Dict[str, Any]) -> str:
    """Handle documentation query."""
    query_text = arguments.get("query")
    reprocess = arguments.get("reprocess", False)
    source_filter = arguments.get("source_filter")
    source_type = arguments.get("source_type")
    
    registry = Registry()
    chroma = ChromaManager()
    engine = QueryEngine(registry, chroma)
    
    if reprocess:
        results = engine.query_with_reprocess(query_text)
    else:
        results = engine.query(
            query_text,
            source_filter=source_filter,
            source_type_filter=source_type
        )
    
    # Format results
    output = []
    output.append(f"Query: {query_text}")
    output.append(f"Confidence: {results['confidence']:.2f}")
    output.append(f"Found {results['total_results']} results\n")
    
    if results.get('should_reprocess'):
        output.append(f"⚠️ {results['reprocess_suggestion']}\n")
    
    if results.get('reprocessed'):
        output.append("🔄 Results enhanced with schematic reprocessing\n")
    
    output.append("Top Results:")
    output.append("-" * 80)
    
    for idx, result in enumerate(results['results'], 1):
        output.append(f"\n{idx}. {result['citation']}")
        output.append(f"   Score: {result['score']:.2f}")
        content = result['content']
        if len(content) > 400:
            content = content[:400] + "..."
        output.append(f"   {content}")
    
    return '\n'.join(output)


def handle_list_sources(arguments: Dict[str, Any]) -> str:
    """Handle listing sources."""
    source_type = arguments.get("source_type", "all")
    
    registry = Registry()
    
    if source_type == "all":
        sources = registry.list_sources()
    else:
        sources = registry.list_sources(source_type)
    
    if not sources:
        return "No sources found."
    
    output = [f"Indexed Sources ({len(sources)} total):\n"]
    
    for source in sources:
        output.append(f"📄 {source['source_type'].upper()}: {source['source_path']}")
        output.append(f"   Status: {source['status']}")
        output.append(f"   Indexed: {source['indexed_at']}")
        if source['file_size']:
            output.append(f"   Size: {source['file_size'] / 1024 / 1024:.1f}MB")
        output.append("")
    
    return '\n'.join(output)


def handle_stats(arguments: Dict[str, Any]) -> str:
    """Handle database statistics."""
    registry = Registry()
    chroma = ChromaManager()
    
    reg_stats = registry.get_stats()
    chroma_stats = chroma.get_stats()
    
    output = ["SmartDoc2 Database Statistics\n"]
    
    output.append(f"Total Sources: {reg_stats['total_sources']}")
    output.append(f"Cached Schematics: {reg_stats['cached_schematics']}")
    output.append(f"Total Documents: {chroma_stats['total_documents']}")
    
    if reg_stats['sources_by_type']:
        output.append("\nSources by Type:")
        for st in reg_stats['sources_by_type']:
            output.append(f"  {st['source_type']}: {st['count']}")
    
    if chroma_stats.get('documents_by_type'):
        output.append("\nDocuments by Type:")
        for doc_type, count in chroma_stats['documents_by_type'].items():
            output.append(f"  {doc_type}: {count}")
    
    return '\n'.join(output)


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Route tool calls to appropriate handlers."""
    try:
        if tool_name == "smartdoc_index_pdf":
            return handle_index_pdf(arguments)
        elif tool_name == "smartdoc_fetch_repo":
            return handle_fetch_repo(arguments)
        elif tool_name == "smartdoc_index_web":
            return handle_index_web(arguments)
        elif tool_name == "smartdoc_query":
            return handle_query(arguments)
        elif tool_name == "smartdoc_list_sources":
            return handle_list_sources(arguments)
        elif tool_name == "smartdoc_stats":
            return handle_stats(arguments)
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return f"Error executing {tool_name}: {str(e)}"


def get_tool_definitions():
    """Return MCP tool definitions."""
    return {
        "tools": [
            {
                "name": "smartdoc_index_pdf",
                "description": "Index a PDF datasheet or technical document with automatic schematic analysis. Use this when the user asks to index, add, or process a PDF file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "pdf_path": {
                            "type": "string",
                            "description": "Path to the PDF file to index (can be relative or absolute)"
                        },
                        "analyze_schematics": {
                            "type": "boolean",
                            "description": "Whether to analyze schematics with Gemini Vision (default: true)",
                            "default": True
                        },
                        "initial_query": {
                            "type": "string",
                            "description": "Optional initial query context for better schematic analysis (e.g., 'SPI and I2C pinout')"
                        }
                    },
                    "required": ["pdf_path"]
                }
            },
            {
                "name": "smartdoc_fetch_repo",
                "description": "Clone and index a GitHub repository with code-aware chunking. Use when user wants to index code from GitHub.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "GitHub repository URL (e.g., https://github.com/owner/repo)"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Optional branch name (default: main/master)"
                        }
                    },
                    "required": ["repo_url"]
                }
            },
            {
                "name": "smartdoc_index_web",
                "description": "Scrape and index a web page or documentation site. Use when user wants to index online documentation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the web page to index"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "smartdoc_query",
                "description": "Query the indexed documentation with semantic search. Returns relevant information with source citations. Use this to answer technical questions about indexed content.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question or search query"
                        },
                        "reprocess": {
                            "type": "boolean",
                            "description": "Whether to reprocess schematics with query-specific context (recommended for pin/schematic questions)",
                            "default": False
                        },
                        "source_filter": {
                            "type": "string",
                            "description": "Optional filter by specific source path/URL"
                        },
                        "source_type": {
                            "type": "string",
                            "enum": ["pdf", "github", "web"],
                            "description": "Optional filter by source type"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "smartdoc_list_sources",
                "description": "List all indexed sources in the database. Use to show what documentation is available.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_type": {
                            "type": "string",
                            "enum": ["pdf", "github", "web", "all"],
                            "description": "Filter by source type (default: all)",
                            "default": "all"
                        }
                    }
                }
            },
            {
                "name": "smartdoc_stats",
                "description": "Display database statistics including total documents, sources, and cached schematics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    }


def main():
    """Main MCP server loop."""
    logger.info("SmartDoc2 MCP Server starting...")
    
    while True:
        try:
            request = read_request()
            
            if request is None:
                break
            
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            response = {"jsonrpc": "2.0", "id": request_id}
            
            if method == "initialize":
                response["result"] = {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "smartdoc",
                        "version": "0.1.0"
                    }
                }
            
            elif method == "tools/list":
                response["result"] = get_tool_definitions()
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result_text = handle_tool_call(tool_name, arguments)
                
                response["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            
            write_response(response)
            
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
            break
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if request else None,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            write_response(error_response)


if __name__ == "__main__":
    main()

