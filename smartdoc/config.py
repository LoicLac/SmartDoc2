"""
Configuration settings for SmartDoc2.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = DATA_DIR / "pdfs"
TEMP_DIR = DATA_DIR / "temp"
CHROMA_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
PDFS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

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

# Registry Database
REGISTRY_DB = str(DATA_DIR / "registry.db")

# Vision Settings
GEMINI_MODEL = "gemini-1.5-flash"  # Fast and cost-effective for vision
GEMINI_TEMPERATURE = 0.1  # Low temperature for technical accuracy
VISION_MAX_RETRIES = 3
VISION_CACHE_ENABLED = True

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

