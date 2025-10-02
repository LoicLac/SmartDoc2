# SmartDoc2

**LlamaIndex-powered documentation system for Cursor workspace**

SmartDoc2 enables intelligent ingestion, indexing, and retrieval of technical documentation from PDFs, GitHub repositories, and web pages. It uses ChromaDB for persistent vector storage and Gemini Vision for advanced schematic analysis.

## Features

- 📄 **Smart PDF Processing**: LlamaParse for complex datasheets with tables and diagrams
- 🔍 **Schematic Analysis**: Gemini Vision for analyzing circuit diagrams and pinout schematics
- 🐙 **GitHub Integration**: Full repository indexing with code-aware chunking
- 🌐 **Web Scraping**: Clean documentation extraction from web pages
- 💾 **Persistent Storage**: ChromaDB database that persists with your workspace
- 📊 **Source Tracking**: SQLite registry tracking all indexed sources with metadata
- 🎯 **Smart Retrieval**: Confidence-based reprocessing with vision models
- 🗂️ **Web Manager**: Browser UI to view, delete, and transfer data across multiple workspaces

## Architecture

```
YourProject/
├── .smartdoc_yourproject/  # Auto-created workspace (named after project folder)
│   ├── .env                # API keys (auto-generated with placeholders)
│   ├── pdfs/               # PDF storage
│   ├── chroma_db/          # Persistent vector database
│   ├── registry.db         # Source tracking & cache
│   └── temp/               # Temporary files
└── .cursorrules            # Cursor AI integration (optional)
```

SmartDoc2/
├── smartdoc/               # Core application
│   ├── core/               # Registry & ChromaDB manager
│   ├── ingestion/          # PDF, GitHub, Web ingestors
│   ├── vision/             # Gemini Vision integration
│   ├── query/              # Query engine & citation formatting
│   └── web/                # Web UI for multi-workspace management
└── setup.py                # Installation
```

## Installation

### 1. Clone and Setup

```bash
cd /Users/loic/Code/SmartDoc2
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

**SmartDoc automatically creates `.smartdoc_{project_name}/.env` on first run!**

```bash
# Navigate to your project
cd /path/to/your/project

# Run any smartdoc command (auto-creates workspace + .env with placeholders)
smartdoc --help

# Edit the auto-generated .env file
nano .smartdoc_yourproject/.env  # Replace 'yourproject' with your folder name
```

**Add your API keys to the placeholders:**

```bash
GEMINI_API_KEY=your_gemini_api_key_here          # Required for vision
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here  # Optional (uses fallback)
GITHUB_TOKEN=your_github_token_here              # Optional (for private repos)
```

**Get API Keys:**
- Gemini: https://makersuite.google.com/app/apikey
- LlamaParse: https://cloud.llamaindex.ai/parse (optional)
- GitHub: https://github.com/settings/tokens (optional)

### 3. That's It!

✅ **No manual initialization needed** - workspace auto-creates on first command
✅ **Each project gets its own isolated workspace** - named `.smartdoc_{project_name}/`
✅ **Git-ignored by default** - pattern `.smartdoc_*/` automatically excluded

## Usage

### Quick Start

```bash
# Index sources
smartdoc index-pdf .smartdoc_yourproject/pdfs/datasheet.pdf
smartdoc fetch-repo https://github.com/username/library
smartdoc web https://docs.example.com/api

# Query with natural language
smartdoc query "What are the SPI pins?"

# Manage database
smartdoc list-sources
smartdoc stats
smartdoc web-manager
```

### Cursor Integration

Copy `.cursorrules` to your project for natural language commands:

```bash
cp /path/to/SmartDoc2/.cursorrules /path/to/your/project/
```

Now ask Cursor directly:
- "Index this datasheet into SmartDoc"
- "What are the I2C pins according to SmartDoc?"
- "Show me SmartDoc sources"

The AI automatically checks SmartDoc, cites sources, and handles schematic reprocessing.

### 📖 Complete Usage Guide

**See [USAGE.md](USAGE.md) for comprehensive documentation:**
- Detailed CLI commands with examples
- Advanced Cursor integration workflows
- Batch operations and automation
- Query filtering and optimization
- Common workflows and best practices

## How It Works

### PDF Ingestion with Schematic Analysis

1. **Text Extraction**: LlamaParse extracts text, tables, and structure
2. **Image Extraction**: All diagrams and schematics are extracted
3. **Initial Analysis**: Gemini Vision provides basic description of each schematic
4. **Caching**: Results cached in SQLite for fast retrieval
5. **Smart Reprocessing**: If query has low confidence (<0.6) and mentions schematic-related terms, triggers context-aware vision analysis

### Query with Confidence-Based Reprocessing

```
User: "What are the SPI pins on Nano R4?"
  ↓
1. Semantic search in ChromaDB
2. Calculate confidence score
3. If score < 0.6 AND query mentions "SPI":
   - Retrieve relevant schematic images
   - Send to Gemini with query-specific prompt
   - Cache result for future queries
4. Return: "[nano_r4.pdf, p.23] SPI: MOSI=D11, MISO=D12..."
```

### GitHub Repository Ingestion

1. Clone repo to temp directory
2. Filter by extensions: `.cpp`, `.h`, `.ino`, `.md`
3. Check file sizes (warn at 5MB)
4. Smart chunking: keep functions/classes together
5. Index with metadata: file path, language, commit SHA
6. Clean up temp clone

## Configuration

Edit `smartdoc/config.py` to customize:

- File size limits
- Chunking parameters
- Confidence thresholds
- Supported file extensions
- Vision model settings

## Database Management

```bash
# View registry stats
smartdoc stats

# List all indexed sources
smartdoc list-sources

# View detailed processing logs for a source
smartdoc logs .smartdoc_yourproject/pdfs/your_file.pdf

# Remove a source
smartdoc remove .smartdoc_yourproject/pdfs/old_file.pdf

# Manage multiple workspaces via web UI
smartdoc web-manager
```

**Each project has its own isolated workspace:**
- Database: `.smartdoc_{project_name}/chroma_db/`
- Registry: `.smartdoc_{project_name}/registry.db`
- To backup: Just copy the entire `.smartdoc_{project_name}/` folder
- To reset: Delete the `.smartdoc_{project_name}/` folder

## File Size Handling

- **< 5MB**: Process automatically
- **5-50MB**: Warning displayed, continues processing
- **> 50MB**: Prompts for confirmation before processing

## Development

### Project Structure

- `core/`: Database managers (Registry + ChromaDB)
- `ingestion/`: Source-specific ingestors
- `vision/`: Gemini Vision integration
- `query/`: Retrieval and ranking
- `cli.py`: Command-line interface

### Adding New Ingestors

Extend `BaseIngestor` class:

```python
from smartdoc.ingestion.base_ingestor import BaseIngestor

class CustomIngestor(BaseIngestor):
    def ingest(self, source: str, **kwargs):
        # Your ingestion logic
        pass
    
    def validate_source(self, source: str):
        # Validation logic
        pass
```

## Troubleshooting

**ChromaDB not persisting:**
- Check `.smartdoc_{project_name}/chroma_db/` directory exists
- Verify write permissions in workspace folder

**API errors:**
- Verify API keys in `.smartdoc_{project_name}/.env`
- Check API rate limits
- Ensure `.env` file has actual keys (not placeholders)

**Database schema errors:**
- Delete `.smartdoc_{project_name}/chroma_db/` and reindex sources

**Processing failures:**
- Use `smartdoc logs <source_path>` to see detailed error logs
- Check that PDFs are not corrupted
- Verify Gemini API key for schematic analysis

**Large file warnings:**
- Adjust `MAX_FILE_SIZE_WARNING` in `config.py`
- Use selective indexing for huge repos

## Roadmap

- [ ] PDF ingestion with LlamaParse ✓
- [ ] Gemini Vision integration ✓
- [ ] GitHub repository ingestion
- [ ] Web scraping
- [ ] Query engine with confidence scoring
- [ ] CLI interface
- [ ] Cursor rules integration
- [ ] Auto-monitoring of PDF folder
- [ ] Incremental updates for GitHub repos

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

