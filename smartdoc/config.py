"""
Configuration settings for SmartDoc2.
"""

import os
import sys
import warnings
import sqlite3
from pathlib import Path
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

# Suppress noisy SSL warnings from urllib3
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL')

# Base paths
INSTALL_DIR = Path(__file__).parent.parent  # SmartDoc installation directory
BASE_DIR = INSTALL_DIR  # Alias for compatibility

# Workspace directory - dynamically named based on current working directory
# Example: If user runs smartdoc in "MyProject" -> creates ".smartdoc_myproject"
WORKSPACE_ROOT = Path(os.getcwd())
PROJECT_NAME = WORKSPACE_ROOT.name.lower().replace(" ", "_").replace("-", "_")
WORKSPACE_DIR = WORKSPACE_ROOT / f".smartdoc_{PROJECT_NAME}"
DATA_DIR = WORKSPACE_DIR  # Alias for compatibility
PDFS_DIR = WORKSPACE_DIR / "pdfs"
TEMP_DIR = WORKSPACE_DIR / "temp"
CHROMA_DIR = WORKSPACE_DIR / "chroma_db"

# Track if this is first initialization
_is_new_workspace = not WORKSPACE_DIR.exists()

# Ensure workspace directory exists
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Ensure directories exist
PDFS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Registry Database path
REGISTRY_DB = str(WORKSPACE_DIR / "registry.db")

# Auto-initialize empty registry database if it doesn't exist
# This allows web-manager to discover empty workspaces
if not Path(REGISTRY_DB).exists():
    try:
        conn = sqlite3.connect(REGISTRY_DB)
        cursor = conn.cursor()
        
        # Sources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_path TEXT NOT NULL UNIQUE,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                status TEXT DEFAULT 'pending',
                metadata TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Schematic cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schematic_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                image_hash TEXT NOT NULL,
                page_number INTEGER,
                last_query TEXT,
                vision_result TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
                UNIQUE(image_hash, last_query)
            )
        """)
        
        # Processing logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                step TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"⚠️  Failed to initialize registry database: {e}", file=sys.stderr)
    finally:
        if 'conn' in locals():
            conn.close()

# Auto-create .env file in workspace if it doesn't exist
ENV_FILE = WORKSPACE_DIR / ".env"
_env_created = False
if not ENV_FILE.exists():
    env_template = """# SmartDoc2 API Keys
# Get your API keys from:
#   - GEMINI_API_KEY: https://makersuite.google.com/app/apikey
#   - LLAMAPARSE_API_KEY: https://cloud.llamaindex.ai/parse (optional)
#   - GITHUB_TOKEN: https://github.com/settings/tokens (optional)

# Required for Gemini Vision schematic analysis
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Enhanced PDF parsing (uses pypdf2 fallback if not set)
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here

# Optional: GitHub Personal Access Token (higher rate limits for public repos)
GITHUB_TOKEN=your_github_token_here

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
"""
    ENV_FILE.write_text(env_template)
    _env_created = True

# Show initialization summary and ask about .cursorrules
if _is_new_workspace and _env_created:
    print(f"\n{'='*70}")
    print(f"🚀 SmartDoc workspace initialized: {WORKSPACE_DIR.name}/")
    print(f"{'='*70}")
    print(f"  📁 Workspace: {WORKSPACE_DIR}")
    print(f"  🔑 API keys:  {WORKSPACE_DIR.name}/.env")
    print(f"{'='*70}")
    
    # Ask about .cursorrules
    CURSORRULES_SOURCE = INSTALL_DIR / ".cursorrules"
    CURSORRULES_DEST = WORKSPACE_ROOT / ".cursorrules"
    
    if CURSORRULES_SOURCE.exists() and not CURSORRULES_DEST.exists():
        print(f"\n📋 Cursor AI Integration:")
        print(f"   SmartDoc includes .cursorrules for natural language commands")
        print(f"   (enables: 'Index PDF', 'Query SmartDoc', hardware file discovery)")
        
        # Only prompt if stdin is available (not in non-interactive mode)
        if sys.stdin.isatty():
            try:
                response = input(f"\n   Create .cursorrules in this project? [Y/n]: ").strip().lower()
                if response in ['', 'y', 'yes']:
                    CURSORRULES_DEST.write_text(CURSORRULES_SOURCE.read_text())
                    print(f"   ✓ Created .cursorrules")
                    print(f"   → Cursor AI will now use SmartDoc integration")
                else:
                    print(f"   ⊘ Skipped .cursorrules")
                    print(f"   → Add later: cp {CURSORRULES_SOURCE} ./")
            except (EOFError, KeyboardInterrupt):
                print(f"\n   ⊘ Skipped .cursorrules (interrupted)")
        else:
            # Non-interactive mode (scripts, CI/CD)
            print(f"   → Add later: cp {CURSORRULES_SOURCE} ./")
    elif CURSORRULES_DEST.exists():
        print(f"\n📋 Cursor AI: .cursorrules already exists")
    
    print(f"\n{'='*70}")
    print(f"⚡ Quick Start:")
    print(f"{'='*70}")
    print(f"  1. Add API keys:    nano {WORKSPACE_DIR.name}/.env")
    print(f"  2. Index PDF:       smartdoc index-pdf <path>")
    print(f"  3. Query database:  smartdoc query \"your question\"")
    print(f"  4. View help:       smartdoc --help")
    print(f"{'='*70}\n")

# Load environment variables from workspace
load_dotenv(dotenv_path=ENV_FILE)

# API Keys
LLAMAPARSE_API_KEY = os.getenv("LLAMAPARSE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# File Size Limits (bytes)
MAX_FILE_SIZE_WARNING = 5 * 1024 * 1024  # 5MB
MAX_FILE_SIZE_HARD = 50 * 1024 * 1024    # 50MB

# Chunking Settings
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 200
CODE_CHUNK_SIZE = 512  # Smaller for code to preserve functions

# Query Settings
CONFIDENCE_THRESHOLD = 0.6  # Trigger vision reprocessing below this
TOP_K_RESULTS = 5
RERANK_TOP_N = 3  # Number of results to return after reranking

# ChromaDB Settings
CHROMA_PERSIST_DIR = str(CHROMA_DIR)
COLLECTION_NAME = "smartdoc_workspace"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"  # Fast and efficient

# GitHub Settings
GITHUB_EXTENSIONS = [".cpp", ".h", ".ino", ".c", ".hpp", ".cc", ".cxx", ".md", ".txt", ".rst"]
GITHUB_EXCLUDE_DIRS = ["node_modules", ".git", "build", "dist", "venv", "__pycache__", "test", "tests"]

# PDF Settings
PDF_DPI = 300  # For image extraction
SUPPORTED_IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".gif", ".bmp"]

# Vision Settings
GEMINI_MODEL = "gemini-2.5-pro"  # Gemini 2.5 Pro (stable, released June 2025)
GEMINI_TEMPERATURE = 0.1  # Low temperature for technical accuracy
VISION_MAX_RETRIES = 3
VISION_CACHE_ENABLED = True

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
