# SmartDoc2 Quick Start Guide

## Installation (5 minutes)

### 1. Setup Environment
```bash
cd /Users/loic/Code/SmartDoc2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install SmartDoc CLI
pip install -e .
```

### 2. Configure API Keys

**SmartDoc automatically creates workspace on first run!**

```bash
# Run any SmartDoc command (creates workspace automatically)
smartdoc --help

# This creates: .smartdoc_{project_name}/
# Example: In "MyProject" folder → .smartdoc_myproject/
#   ├── .env           # Your API keys (auto-generated with placeholders)
#   ├── pdfs/          # PDF storage
#   ├── temp/          # Temporary files
#   ├── chroma_db/     # Vector database
#   └── registry.db    # SQLite database

# Edit the auto-generated .env file (replace {project_name} with your actual folder name)
nano .smartdoc_myproject/.env  # or use your preferred editor

# Add your API keys:
# - GEMINI_API_KEY: Get from https://makersuite.google.com/app/apikey
# - LLAMAPARSE_API_KEY: Get from https://cloud.llamaindex.ai/parse (optional)
# - GITHUB_TOKEN: Get from https://github.com/settings/tokens (optional)
```

**The `.smartdoc_{project_name}/.env` file will contain:**
```bash
GEMINI_API_KEY=your_gemini_api_key_here          # Required for vision
LLAMAPARSE_API_KEY=your_llamaparse_api_key_here  # Optional (uses fallback)
GITHUB_TOKEN=your_github_token_here              # Optional (for private repos)
```

### 3. That's It!

✅ **You're ready to go!**

**Everything auto-initializes in `.smartdoc_{project_name}/` on first command:**
- Workspace named after your project folder (e.g., "MyProject" → `.smartdoc_myproject/`)
- `.env` file with API key placeholders
- `pdfs/` directory for PDF storage
- `temp/` directory for temporary files
- `chroma_db/` vector database
- `registry.db` SQLite database

**All workspace data is in one folder:**
- ✅ Easy to backup (just copy `.smartdoc_{project_name}/`)
- ✅ Easy to delete (remove folder to start fresh)
- ✅ Git-ignored by pattern `.smartdoc_*/`
- ✅ Each project automatically gets its own isolated workspace

---

## Basic Usage

### Index a PDF Datasheet
```bash
# Place your PDF in the pdfs folder (replace {project_name} with your actual folder)
smartdoc index-pdf .smartdoc_{project_name}/pdfs/arduino_nano_r4.pdf

# With initial query context for better schematic analysis
smartdoc index-pdf .smartdoc_{project_name}/pdfs/nano_r4.pdf --query "SPI and I2C pinout"
```

### Fetch GitHub Repository
```bash
smartdoc fetch-repo https://github.com/FortySevenEffects/arduino_midi_library

# Specific branch
smartdoc fetch-repo https://github.com/arduino/MIDI --branch develop
```

### Scrape Web Documentation
```bash
smartdoc web https://docs.arduino.cc/hardware/nano-r4-wifi
```

### Query Your Knowledge Base
```bash
# Basic query
smartdoc query "What are the SPI pins on Arduino Nano R4?"

# With automatic schematic reprocessing
smartdoc query "SPI pinout Arduino Nano" --reprocess

# Filter by source type
smartdoc query "MIDI send note" --type github
```

### View Your Data
```bash
# List all sources
smartdoc list-sources

# Show statistics
smartdoc stats

# List only PDFs
smartdoc list-sources --type pdf
```

---

## Example Workflow: Arduino Nano R4 Development

```bash
# 1. Index the datasheet
smartdoc index-pdf data/pdfs/arduino_nano_r4_datasheet.pdf

# 2. Index Arduino MIDI library
smartdoc fetch-repo https://github.com/FortySevenEffects/arduino_midi_library

# 3. Index online documentation
smartdoc web https://docs.arduino.cc/hardware/nano-r4-wifi

# 4. Query about SPI pins (will analyze schematic if confidence is low)
smartdoc query "What are the SPI pins and their alternate functions?" --reprocess

# 5. Query MIDI code examples
smartdoc query "How to send MIDI note on message?" --type github

# 6. Check what you've indexed
smartdoc stats
```

---

## Cursor Integration

The `.cursorrules` file is already configured! Just ask Cursor naturally:

```
"Index the Arduino Nano R4 datasheet at data/pdfs/nano_r4.pdf"
"What are the SPI pins on the Nano R4?"
"Fetch the Arduino MIDI library"
"Show me code examples for sending MIDI messages"
```

Cursor will automatically:
1. Run the appropriate SmartDoc commands
2. Retrieve results from your database
3. Provide answers with source citations
4. Suggest reprocessing if confidence is low

---

## Understanding Confidence Scores

- **> 0.8**: High confidence - answer is very likely correct
- **0.6 - 0.8**: Medium confidence - answer is probably correct but verify
- **< 0.6**: Low confidence - system suggests reprocessing with vision model

For schematic/pinout queries with low confidence, SmartDoc automatically:
1. Finds relevant schematic images in indexed PDFs
2. Sends them to Gemini Vision with your specific query
3. Caches the result for future queries
4. Returns enhanced answer with higher confidence

---

## File Sizes

- Files < 5MB: Processed automatically
- Files 5-50MB: Warning shown, continues
- Files > 50MB: Prompts for confirmation

---

## Pro Tips

1. **Initial Query Context**: When indexing complex datasheets, provide a query:
   ```bash
   smartdoc index-pdf datasheet.pdf --query "I2C and SPI configuration"
   ```
   This improves initial schematic analysis.

2. **Reprocessing**: For pinout/schematic questions, always use `--reprocess`:
   ```bash
   smartdoc query "I2C pins" --reprocess
   ```

3. **Source Management**: Remove outdated versions before indexing new ones:
   ```bash
   smartdoc remove data/pdfs/old_datasheet.pdf
   smartdoc index-pdf data/pdfs/new_datasheet.pdf
   ```

4. **GitHub Filtering**: The system automatically:
   - Filters by relevant extensions (.cpp, .h, .ino, .md)
   - Skips build directories and node_modules
   - Preserves function/class boundaries when chunking

5. **Batch Indexing**: Create a script:
   ```bash
   #!/bin/bash
   for pdf in data/pdfs/*.pdf; do
       smartdoc index-pdf "$pdf"
   done
   ```

---

## Troubleshooting

### API Key Errors
```bash
# Verify .env file exists and has keys
cat .env

# Check if keys are loaded
python -c "from smartdoc.config import GEMINI_API_KEY; print('OK' if GEMINI_API_KEY else 'Missing')"
```

### ChromaDB Issues
```bash
# Check database location
ls -lh data/chroma_db/

# View stats
smartdoc stats

# Reset if needed (⚠️ destroys all data)
smartdoc reset --confirm
```

### GitHub Rate Limits
```bash
# Add GitHub token to .env
GITHUB_TOKEN=your_personal_access_token

# Check current limits: https://github.com/settings/tokens
```

### Large File Warnings
```bash
# Adjust limits in smartdoc/config.py:
# MAX_FILE_SIZE_WARNING = 10 * 1024 * 1024  # 10MB
# MAX_FILE_SIZE_HARD = 100 * 1024 * 1024    # 100MB
```

---

## What's Next?

- Index your first datasheet
- Try a schematic query with `--reprocess`
- Fetch a GitHub repo you're working with
- Ask Cursor to use SmartDoc for your questions

---

## Understanding How SmartDoc Works

### Knowledge Layers

SmartDoc uses a three-tier knowledge system:

#### 1. Original Chunks (Base Layer)
- Created during initial indexing (`smartdoc index-pdf`)
- General text extraction and schematic analysis
- Static unless source is re-indexed
- Forms the foundation of your knowledge base

#### 2. Cached Analysis (Speed Layer)
- Stored in `data/registry.db`
- Query-specific schematic reanalysis results
- Instant retrieval for repeated queries
- Cleared only on database reset

#### 3. Focused Chunks (Learning Layer)
- **New feature**: Selectively added to ChromaDB
- High-value, query-specific analysis
- Permanently improves vector database
- Makes future related queries better

### Progressive Learning System

**SmartDoc learns from your queries!**

#### First Query (Low Confidence)
```bash
smartdoc query "Arduino Nano R4 SPI pins"

Results:
- Initial confidence: 0.13 (low)
- Auto-triggers reprocessing
- Applies focused Gemini Vision analysis
- Adds 3 focused chunks to database
- Enhanced confidence: 0.88 (high!)
- Database: 70 → 73 documents
```

#### Second Query (Benefits from Learning)
```bash
smartdoc query "MOSI pin Arduino Nano R4"

Results:
- Initial confidence: 0.17 (improved!)
- Uses focused chunks from previous query
- No reprocessing needed
- Database: Unchanged (already has knowledge)
```

#### Third Query (Same as First)
```bash
smartdoc query "Arduino Nano R4 SPI pins"

Results:
- Uses cached analysis (instant!)
- Confidence: 0.88 (maintained)
- No new database additions
```

**Key Benefits:**
- Database gets smarter with each technical query
- Related queries benefit from previous analysis
- No reprocessing for similar questions
- Faster responses over time

### Automatic Reprocessing Explained

#### When It Triggers
SmartDoc automatically reprocesses when it detects:

1. **Low Confidence** (< 0.6)
   - Initial results aren't good enough
   - System knows it can do better

2. **Schematic Keywords**
   - pin, pinout, SPI, I2C, UART, GPIO
   - diagram, schematic, wiring
   - connection, power, voltage

3. **Hardware Queries**
   - MCU pin mappings
   - Communication protocols
   - Power configurations

#### What Happens Automatically

```
1. Expand Results
   Normal: 5 results
   Schematic query: 10 results (more data to analyze)

2. Find Schematics
   Searches for chunks with content_type: 'schematic'
   Logs: "Found 3 schematic results out of 10"

3. Check Cache
   If cached: Use instantly
   If not: Proceed to analysis

4. Focused Analysis
   Sends schematic to Gemini Vision
   With your specific query as context
   Example: "Find SPI pins (MOSI, MISO, SCK, CS)"

5. Evaluate Quality
   Confidence improvement > 0.3? ✅ Add to DB
   Contains structured data? ✅ Add to DB
   Important topic? ✅ Add to DB
   High confidence (>0.8)? ✅ Add to DB

6. Selective Addition
   Creates focused chunk with:
   - Enhanced content (analysis + pin mappings)
   - Rich metadata (query context, confidence)
   - Unique ID (prevents duplicates)
   
7. Return Results
   Shows: 🔄 [Reprocessed] or 💾 [Added to DB]
   Enhanced confidence score
   Better technical answers
```

#### Visual Indicators

- `🔄 [Reprocessed with query context]`
  - Used cached focused analysis
  - Instant retrieval

- `💾 [Added focused analysis to database]`
  - New knowledge added permanently
  - Database grew intelligently

### Selective Addition Criteria

**Not every reprocessing adds to the database!**

Focused chunks are added only when:

1. **High Confidence Improvement**
   - Boost > 0.3 (e.g., 0.13 → 0.88)
   - Significant quality improvement

2. **Structured Data Present**
   - Pin mappings: `{MOSI: D11, MISO: D12}`
   - Component lists: `[RA4M1, MP2322GQH]`
   - Tables and specifications

3. **Important Topics**
   - Pinout, connections, SPI, I2C, UART
   - Power, voltage, GPIO
   - Schematic, diagram, wiring

4. **High Confidence Result**
   - Analysis confidence > 0.8
   - System is very sure about findings

**Result**: Database grows intelligently (not bloated)
- 70 docs → 73 docs (+3 focused chunks)
- Only high-value additions
- Relevant for future queries

### Best Practices

1. **Trust Automatic Reprocessing**
   ```bash
   # Do this (simple):
   smartdoc query "SPI pins"
   
   # Not this (unnecessary):
   smartdoc query "SPI pins" --reprocess
   ```

2. **Monitor Database Growth**
   ```bash
   smartdoc stats
   # Check total documents - should increase over time
   ```

3. **Use Specific Technical Terms**
   ```bash
   # Good:
   smartdoc query "SPI MOSI pin Arduino Nano R4"
   
   # Less effective:
   smartdoc query "pins on Arduino"
   ```

4. **Check Logs for Issues**
   ```bash
   smartdoc logs "data/pdfs/datasheet.pdf"
   # Shows: text extraction, vision analysis, errors
   ```

5. **Leverage Progressive Learning**
   ```bash
   # First query adds knowledge
   smartdoc query "I2C pins Arduino"
   
   # Future I2C queries benefit automatically
   smartdoc query "SDA pin location"  # Better results!
   ```

6. **Version Awareness**
   - Note which datasheet version is indexed
   - Update when new versions release
   - Remove old before adding new

7. **Organize with Web UI**
   ```bash
   smartdoc web-manager
   # For: multiple projects, bulk operations, visual logs
   ```

### Key Insights

- **Automatic > Manual**: System knows when to reprocess
- **Progressive Learning**: Each query can improve future ones
- **Smart Growth**: Database grows selectively, not bloated
- **Cache-First**: Repeated queries are instant
- **Confidence Tracking**: Watch scores to understand behavior
- **Trust the System**: Designed to be intelligent by default

### Troubleshooting Progressive Learning

#### Reprocessing Not Adding Knowledge?

1. **Check Confidence Improvement**
   ```bash
   # Look for: "Enhanced confidence: 0.88"
   # If improvement < 0.3, won't add
   ```

2. **Verify Technical Terms**
   ```bash
   # Query must contain schematic terms
   # Example: pin, SPI, I2C, pinout, diagram
   ```

3. **Ensure Schematic Chunks Exist**
   ```bash
   smartdoc query "schematic" --source "data/pdfs/your.pdf"
   # Should find chunks with content_type: 'schematic'
   ```

4. **Check Database Stats**
   ```bash
   smartdoc stats
   # Before: 70 documents
   # After successful addition: 73 documents
   ```

### Example Workflow: First-Time Use

```bash
# Step 1: Index datasheet (creates base layer)
smartdoc index-pdf data/pdfs/arduino_nano_r4.pdf
# Result: 70 documents (13 text + 20 schematics + more)

# Step 2: Technical query (triggers learning)
smartdoc query "What are the SPI pins on Arduino Nano R4?"
# Auto-reprocesses → adds focused chunks
# Result: 73 documents, confidence 0.88

# Step 3: Related query (benefits from learning)
smartdoc query "MOSI pin Arduino Nano R4"
# Uses focused chunks → higher confidence
# No reprocessing needed

# Step 4: Different topic (new learning opportunity)
smartdoc query "I2C pins Arduino Nano R4"
# Auto-reprocesses → adds I2C focused chunks
# Result: 76 documents

# Step 5: Check growth
smartdoc stats
# Shows progressive improvement in document count
```

### Understanding Database Growth

**Healthy Growth Pattern:**
```
Day 1: Index datasheet → 70 documents
Day 1: 5 technical queries → 73 documents (+3)
Day 2: 3 related queries → 73 documents (no change, using cache)
Day 2: 2 new topics → 76 documents (+3)
Week 1: 50 queries → 85 documents (+15 high-value)
```

**Not Bloated:**
- Only significant improvements added
- Duplicates prevented
- Structured data prioritized
- Related queries share focused chunks

**Result**: Smarter database that learns from usage!

---

Enjoy! 🚀

