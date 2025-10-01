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
SmartDoc2/
├── smartdoc/              # Core application
│   ├── core/              # Registry & ChromaDB manager
│   ├── ingestion/         # PDF, GitHub, Web ingestors
│   ├── vision/            # Gemini Vision integration
│   └── query/             # Query engine & citation formatting
├── data/
│   ├── pdfs/              # Drop PDFs here
│   ├── chroma_db/         # Persistent vector database
│   └── temp/              # Temporary files
└── .cursorrules           # Cursor AI integration
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

Create a `.env` file (copy from `.env.example`):

```bash
# API Keys
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: GitHub Personal Access Token
GITHUB_TOKEN=your_github_token_here
```

**Get API Keys:**
- LlamaParse: https://cloud.llamaindex.ai/parse
- Gemini: https://makersuite.google.com/app/apikey
- GitHub: https://github.com/settings/tokens (optional, for higher rate limits)

### 3. Initialize Database

```bash
python -c "from smartdoc.core.registry import Registry; Registry()"
python -c "from smartdoc.core.chroma_client import ChromaManager; ChromaManager()"
```

## Usage

### Command-Line Interface

```bash
# Index a PDF
smartdoc index pdf data/pdfs/arduino_nano_r4.pdf

# Fetch GitHub repository
smartdoc fetch repo https://github.com/FortySevenEffects/arduino_midi_library

# Scrape web documentation
smartdoc web https://docs.arduino.cc/hardware/nano-r4-wifi

# Query the database
smartdoc query "What are the SPI pins on Arduino Nano R4?"

# List all sources
smartdoc list sources

# Get statistics
smartdoc stats

# Launch web-based database manager (view/manage multiple workspaces)
smartdoc web-manager --root ~/Code

# Reprocess schematic with new query context
smartdoc reprocess schematic data/pdfs/nano_r4.pdf --page 24
```

### Cursor Integration

Add to your `.cursorrules`:

```markdown
# SmartDoc Integration

User can request documentation indexing with natural language:
- "Index this PDF: [path]"
- "Fetch the Arduino MIDI library from GitHub"
- "Look up SPI configuration in the docs"

When answering technical questions, always check SmartDoc database first.
Cite sources: [nano_r4.pdf, p.23] or [github:arduino/MIDI/src/MIDI.cpp]
```

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
smartdoc list sources

# Remove a source
smartdoc remove source data/pdfs/old_file.pdf

# Reset entire database (⚠️ destructive!)
smartdoc reset --confirm
```

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
- Check `data/chroma_db/` directory exists
- Verify write permissions

**API errors:**
- Verify API keys in `.env`
- Check API rate limits

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

