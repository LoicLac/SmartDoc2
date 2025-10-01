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
```bash
# Copy environment template
cp env_example.txt .env

# Edit .env and add your API keys:
# - LLAMAPARSE_API_KEY: Get from https://cloud.llamaindex.ai/parse
# - GEMINI_API_KEY: Get from https://makersuite.google.com/app/apikey
```

### 3. Initialize Database
```bash
python -c "from smartdoc.core.registry import Registry; Registry()"
python -c "from smartdoc.core.chroma_client import ChromaManager; ChromaManager()"
```

✅ **You're ready to go!**

---

## Basic Usage

### Index a PDF Datasheet
```bash
# Place your PDF in data/pdfs/
smartdoc index-pdf data/pdfs/arduino_nano_r4.pdf

# With initial query context for better schematic analysis
smartdoc index-pdf data/pdfs/nano_r4.pdf --query "SPI and I2C pinout"
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

Enjoy! 🚀

