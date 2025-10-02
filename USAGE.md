# SmartDoc2 Usage Guide

Complete guide to using SmartDoc2 for documentation management, querying, and Cursor AI integration.

---

## Table of Contents

1. [Command-Line Interface (CLI)](#command-line-interface-cli)
2. [Cursor AI Integration](#cursor-ai-integration)
3. [Common Workflows](#common-workflows)
4. [Advanced Usage](#advanced-usage)

---

## Command-Line Interface (CLI)

### 1. Indexing Commands

#### `smartdoc index-pdf`

Index PDF documents (datasheets, manuals, schematics) into the database.

**Basic Usage:**
```bash
smartdoc index-pdf <path_to_pdf>
```

**Examples:**
```bash
# Index a single PDF
smartdoc index-pdf .smartdoc_myproject/pdfs/arduino_nano_r4.pdf

# Index with query context (improves schematic analysis)
smartdoc index-pdf .smartdoc_myproject/pdfs/esp32_datasheet.pdf --query "GPIO pinout and power requirements"

# Index from any location (SmartDoc will copy to workspace)
smartdoc index-pdf ~/Downloads/stm32_reference.pdf
```

**Options:**
- `--query TEXT`: Provide initial query context for better schematic analysis
- Automatically detects and analyzes schematics using Gemini Vision
- Caches analysis results for faster future queries

**What Happens:**
1. PDF is copied to `.smartdoc_{project_name}/pdfs/`
2. Text, tables, and images are extracted
3. Schematics are analyzed with Gemini Vision
4. Content is chunked and stored in ChromaDB
5. Registry tracks the source with metadata

**Tips:**
- Use `--query` for PDFs with complex schematics
- SmartDoc auto-detects diagrams and circuit schematics
- Large PDFs (>5MB) show warnings but process normally

---

#### `smartdoc fetch-repo`

Clone and index a GitHub repository (code, documentation, README files).

**Basic Usage:**
```bash
smartdoc fetch-repo <github_url>
```

**Examples:**
```bash
# Index entire repository
smartdoc fetch-repo https://github.com/arduino/ArduinoCore-API

# Index Arduino MIDI library
smartdoc fetch-repo https://github.com/FortySevenEffects/arduino_midi_library

# Index ESP32 Arduino core
smartdoc fetch-repo https://github.com/espressif/arduino-esp32
```

**What Gets Indexed:**
- Source code: `.cpp`, `.h`, `.ino`, `.py`, `.js`, `.ts`
- Documentation: `.md`, `.rst`, `.txt`
- Respects `.gitignore` patterns
- Smart chunking keeps functions/classes together

**Options:**
- Requires `GITHUB_TOKEN` in `.env` for private repos
- Automatic rate limit handling
- Skips binary files and large files (>50MB with prompt)

**Tips:**
- Index libraries you frequently reference
- Query for specific functions or API usage
- Great for understanding library internals

---

#### `smartdoc web`

Scrape and index web documentation pages.

**Basic Usage:**
```bash
smartdoc web <url>
```

**Examples:**
```bash
# Index Arduino official docs
smartdoc web https://docs.arduino.cc/hardware/nano-r4-wifi

# Index library documentation
smartdoc web https://www.arduinolibraries.info/libraries/midi-library

# Index API reference
smartdoc web https://api.example.com/docs/getting-started
```

**What Happens:**
1. Page is fetched and cleaned (removes ads, navigation)
2. Main content is extracted using readability algorithms
3. Links are preserved for reference
4. Stored with URL metadata

**Tips:**
- Best for official documentation sites
- May require multiple pages for complete docs
- Use for quick reference without downloading repos

---

### 2. Query Commands

#### `smartdoc query`

Query the database with natural language questions.

**Basic Usage:**
```bash
smartdoc query "your question here"
```

**Examples:**
```bash
# Technical queries
smartdoc query "What are the SPI pins on Arduino Nano R4?"
smartdoc query "How to initialize MIDI library in Arduino?"
smartdoc query "ESP32 I2C clock frequency configuration"

# Schematic queries (automatic reprocessing)
smartdoc query "Arduino Nano R4 MOSI pin number"
smartdoc query "Power supply pins and voltage ratings"
smartdoc query "I2C pullup resistor values schematic"

# Code queries
smartdoc query "MIDI.begin() parameters and usage"
smartdoc query "analogRead() resolution on Nano R4"
```

**Options:**
- `--reprocess`: Force schematic reprocessing with focused analysis
- `--source PATH`: Limit query to specific source
- `--type TYPE`: Filter by source type (pdf, github, web)

**Advanced Examples:**
```bash
# Force reprocessing for better schematic details
smartdoc query "SPI MISO pin connection diagram" --reprocess

# Search only in specific PDF
smartdoc query "operating voltage" --source .smartdoc_myproject/pdfs/nano_r4.pdf

# Search only GitHub sources
smartdoc query "begin() function implementation" --type github
```

**How It Works:**
1. **Semantic Search**: Finds relevant chunks using ChromaDB
2. **Confidence Scoring**: Calculates answer confidence (0-1)
3. **Auto-Reprocessing**: If confidence < 0.6 OR schematic terms detected:
   - Retrieves relevant schematic images
   - Re-analyzes with Gemini Vision using query context
   - Caches result for future queries
4. **Citation**: Returns answer with source references

**Response Format:**
```
Query: "What are the SPI pins on Arduino Nano R4?"

According to nano_r4.pdf, p.23:
The Arduino Nano R4 SPI pins are:
- MOSI: D11 (GPIO 11)
- MISO: D12 (GPIO 12)
- SCK: D13 (GPIO 13)
- SS: D10 (GPIO 10)

Confidence: 0.89 (High)
Source: nano_r4.pdf (page 23)

🔄 [Reprocessed with Gemini Vision]
💾 [Added focused analysis to database]
```

**Confidence Levels:**
- **> 0.8**: High confidence - answer directly
- **0.6-0.8**: Medium confidence - verify if critical
- **< 0.6**: Low confidence - triggers auto-reprocessing

**Automatic Reprocessing Triggers:**
- Confidence score < 0.6
- Query contains: `pin`, `pinout`, `schematic`, `diagram`, `GPIO`, `SPI`, `I2C`, `UART`, `connection`, `wiring`
- Technical terms detected in low-confidence results

---

#### `smartdoc logs`

View detailed processing logs for a specific source.

**Basic Usage:**
```bash
smartdoc logs <source_path>
```

**Examples:**
```bash
# View PDF processing logs
smartdoc logs .smartdoc_myproject/pdfs/nano_r4.pdf

# Check if schematic analysis succeeded
smartdoc logs data/pdfs/esp32_schematic.pdf
```

**Output Shows:**
```
Processing Logs: nano_r4.pdf
================================================================================

[2025-10-02 14:23:45] TEXT EXTRACTION
Status: ✓ success
Message: Extracted 145 pages
Details:
  - Pages: 145
  - Chunks: 238
  - Method: LlamaParse

[2025-10-02 14:24:12] SCHEMATIC ANALYSIS  
Status: ✓ success
Message: Analyzed 12 schematics
Details:
  - Images found: 12
  - Analyzed: 12
  - Failed: 0
  - Processing time: 27.3s

[2025-10-02 14:24:15] STORAGE
Status: ✓ success
Message: Stored 238 chunks
```

**Use Cases:**
- Debug indexing failures
- Verify Gemini Vision API worked
- Check processing statistics
- Troubleshoot missing content

---

### 3. Management Commands

#### `smartdoc list-sources`

List all indexed sources in the current workspace.

**Basic Usage:**
```bash
smartdoc list-sources
```

**Example Output:**
```
Indexed Sources (4 total):
================================================================================

[PDF] nano_r4.pdf
  Path: .smartdoc_myproject/pdfs/nano_r4.pdf
  Indexed: 2025-10-02 14:23:45
  Chunks: 238
  Schematics: 12 analyzed

[PDF] esp32_datasheet.pdf
  Path: .smartdoc_myproject/pdfs/esp32_datasheet.pdf
  Indexed: 2025-10-01 09:15:22
  Chunks: 542
  Schematics: 24 analyzed

[GITHUB] arduino-esp32
  URL: https://github.com/espressif/arduino-esp32
  Indexed: 2025-09-30 16:45:10
  Files: 127
  Chunks: 890

[WEB] Arduino Nano R4 WiFi Documentation
  URL: https://docs.arduino.cc/hardware/nano-r4-wifi
  Indexed: 2025-09-29 11:30:05
  Chunks: 45
```

---

#### `smartdoc stats`

Show detailed statistics about the current workspace.

**Basic Usage:**
```bash
smartdoc stats
```

**Example Output:**
```
SmartDoc Workspace Statistics
================================================================================

Workspace: .smartdoc_myproject/

Registry:
  Total sources: 4
  Cached schematics: 24

  Sources by type:
    pdf: 2
    github: 1
    web: 1

ChromaDB:
  Total documents: 1,715
  Total sources: 4
  Collection: smartdoc_workspace

  Documents by type:
    pdf: 780
    github: 890
    web: 45

Database size: 234.5 MB
```

**Use Cases:**
- Monitor database growth
- Check indexed content
- Verify sources were added
- Track schematic cache size

---

#### `smartdoc remove`

Remove a source and all its chunks from the database.

**Basic Usage:**
```bash
smartdoc remove <source_path_or_url>
```

**Examples:**
```bash
# Remove a PDF
smartdoc remove .smartdoc_myproject/pdfs/old_datasheet.pdf

# Remove a GitHub repo
smartdoc remove https://github.com/user/old-repo

# Remove web page
smartdoc remove https://old-docs.example.com
```

**What Happens:**
1. Removes all chunks from ChromaDB
2. Removes registry entry
3. Removes cached schematic analysis
4. Removes processing logs
5. Keeps the actual PDF file (manual deletion needed)

**Warning**: This operation cannot be undone!

---

#### `smartdoc web-manager`

Launch the web-based UI for managing multiple workspaces.

**Basic Usage:**
```bash
smartdoc web-manager
```

**Features:**
- **Dashboard**: View all databases, assets, and statistics
- **Browse & Delete**: Inspect and remove specific sources
- **Transfer & Copy**: Move/copy assets between workspaces
- **Processing Logs**: View detailed logs in browser
- **Multi-Workspace**: Manage multiple projects simultaneously

**Example Output:**
```
Starting SmartDoc Web Manager...
✓ Discovered 3 workspaces
✓ Server running at http://127.0.0.1:7860
✓ Open in browser to manage databases
```

**Use Cases:**
- Visual overview of all indexed content
- Bulk operations on multiple sources
- Transfer docs between projects
- Team collaboration (share URL on network)

---

## Cursor AI Integration

SmartDoc integrates seamlessly with Cursor IDE through `.cursorrules`, enabling natural language commands for documentation management.

### Setup

1. **Copy `.cursorrules` to your project:**
```bash
cp /path/to/SmartDoc2/.cursorrules /path/to/your/project/
```

2. **SmartDoc is now available to Cursor AI!**

The AI will:
- ✅ Check SmartDoc database before answering technical questions
- ✅ Cite sources with page numbers: `[nano_r4.pdf, p.23]`
- ✅ Use automatic reprocessing for schematic queries
- ✅ Display confidence scores for answers

---

### Natural Language Commands

#### Indexing with Cursor

**PDF Indexing:**
```
You: "Index the Arduino Nano R4 datasheet into SmartDoc"

AI: *runs* smartdoc index-pdf .smartdoc_myproject/pdfs/nano_r4.pdf
✓ Indexed nano_r4.pdf (238 chunks, 12 schematics analyzed)
```

```
You: "Add this ESP32 schematic to SmartDoc with focus on GPIO pins"

AI: *runs* smartdoc index-pdf .smartdoc_myproject/pdfs/esp32.pdf --query "GPIO pinout"
✓ Indexed with query context for better schematic analysis
```

**GitHub Indexing:**
```
You: "Fetch the Arduino MIDI library from GitHub and index it"

AI: *runs* smartdoc fetch-repo https://github.com/FortySevenEffects/arduino_midi_library
✓ Cloned and indexed 47 source files
```

```
You: "Index ESP32 Arduino core from GitHub"

AI: *runs* smartdoc fetch-repo https://github.com/espressif/arduino-esp32
✓ Indexed 890 chunks from 127 files
```

**Web Documentation:**
```
You: "Scrape and index the official Arduino Nano R4 documentation"

AI: *runs* smartdoc web https://docs.arduino.cc/hardware/nano-r4-wifi
✓ Indexed web documentation (45 chunks)
```

---

#### Querying with Cursor

**Technical Questions:**
```
You: "What are the SPI pins on Arduino Nano R4?"

AI: Let me check SmartDoc...
*runs* smartdoc query "Arduino Nano R4 SPI pins"

According to nano_r4.pdf, p.23:
The Arduino Nano R4 SPI pins are:
- MOSI: D11 (GPIO 11)
- MISO: D12 (GPIO 12)
- SCK: D13 (GPIO 13)
- SS: D10 (GPIO 10)

Confidence: 0.89 (High)
Source: nano_r4.pdf (page 23)
```

**Schematic Queries (Auto-Reprocessing):**
```
You: "Show me the I2C pullup resistor values in the schematic"

AI: *runs* smartdoc query "I2C pullup resistor values schematic"

🔄 Auto-reprocessing schematic with Gemini Vision...

According to nano_r4.pdf, p.15 (schematic):
The I2C lines (SDA/SCL) use 4.7kΩ pullup resistors to 3.3V.
- R12: 4.7kΩ (SDA pullup)
- R13: 4.7kΩ (SCL pullup)

Confidence: 0.92 (High)
Source: nano_r4.pdf (page 15)
🔄 [Reprocessed with focused Gemini Vision analysis]
💾 [Added focused analysis to database]
```

**Code Implementation Queries:**
```
You: "How do I initialize the MIDI library?"

AI: *runs* smartdoc query "MIDI library initialization begin()"

According to github:arduino_midi_library/src/MIDI.h:
```cpp
MIDI.begin(MIDI_CHANNEL_OMNI);  // Listen to all channels
// or
MIDI.begin(1);  // Listen to channel 1 only
```

Confidence: 0.85 (High)
Source: github:FortySevenEffects/arduino_midi_library
```

**Hardware Specs:**
```
You: "What's the operating voltage range for ESP32?"

AI: *runs* smartdoc query "ESP32 operating voltage range"

According to esp32_datasheet.pdf, p.9:
Operating voltage: 2.2V to 3.6V
Recommended: 3.0V to 3.6V
Absolute maximum: 3.6V (do not exceed)

Confidence: 0.94 (High)
Source: esp32_datasheet.pdf (page 9)
```

---

#### Management with Cursor

**List Sources:**
```
You: "Show me all sources in SmartDoc"

AI: *runs* smartdoc list-sources

You have 4 indexed sources:
1. nano_r4.pdf (238 chunks, 12 schematics)
2. esp32_datasheet.pdf (542 chunks, 24 schematics)
3. arduino_midi_library (GitHub, 890 chunks)
4. Arduino Nano R4 Docs (Web, 45 chunks)
```

**Check Statistics:**
```
You: "What's the current SmartDoc database size?"

AI: *runs* smartdoc stats

Workspace: .smartdoc_myproject/
- Total sources: 4
- Total documents: 1,715
- Database size: 234.5 MB
- Cached schematics: 24
```

**View Logs:**
```
You: "Did the ESP32 schematic analysis work?"

AI: *runs* smartdoc logs .smartdoc_myproject/pdfs/esp32_datasheet.pdf

✓ SCHEMATIC ANALYSIS: success
  - Images found: 24
  - Analyzed: 24
  - Failed: 0
  All schematics successfully analyzed!
```

**Remove Sources:**
```
You: "Remove the old Arduino library from SmartDoc"

AI: *runs* smartdoc remove https://github.com/user/old-arduino-lib
✓ Removed source and all associated chunks
```

---

### Advanced Cursor Workflows

#### Workflow 1: New Project Setup
```
You: "I'm starting a new ESP32 project. Set up SmartDoc with ESP32 docs."

AI: Sure! Let me set that up:

1. *runs* smartdoc fetch-repo https://github.com/espressif/arduino-esp32
   ✓ Indexed ESP32 Arduino core

2. *runs* smartdoc index-pdf .smartdoc_myproject/pdfs/esp32_datasheet.pdf
   ✓ Indexed ESP32 datasheet

3. *runs* smartdoc web https://docs.espressif.com/projects/arduino-esp32/
   ✓ Indexed official documentation

SmartDoc is ready! You can now ask about ESP32 features, pinouts, or API usage.
```

#### Workflow 2: Debugging Hardware
```
You: "My I2C isn't working on Arduino Nano R4. Check the schematic."

AI: Let me check the I2C configuration...
*runs* smartdoc query "Arduino Nano R4 I2C pins and pullup resistors" --reprocess

According to nano_r4.pdf, p.15 (schematic):
I2C Configuration:
- SDA: A4 (GPIO 18) - 4.7kΩ pullup to 3.3V
- SCL: A5 (GPIO 19) - 4.7kΩ pullup to 3.3V

⚠️ Note: The Nano R4 uses 3.3V logic for I2C, but A4/A5 are 5V tolerant.
Ensure your I2C devices are compatible with 3.3V signaling.

Common issues:
1. Wrong voltage level (5V devices may need level shifter)
2. Missing external pullups (built-in 4.7kΩ should be sufficient)
3. Using wrong pins (some pins don't support I2C)
```

#### Workflow 3: API Reference While Coding
```
You: "I'm writing MIDI code. What parameters does MIDI.read() accept?"

AI: *runs* smartdoc query "MIDI.read() function parameters and return value"

According to github:arduino_midi_library/src/MIDI.h:
```cpp
bool read();  // Check if a MIDI message is available
bool read(byte channel);  // Check specific channel only
```

Returns: `true` if a message is available, `false` otherwise

After `read()` returns true, use:
- `getType()` - Get message type
- `getData1()` - Get first data byte
- `getData2()` - Get second data byte
- `getChannel()` - Get channel number

Example:
```cpp
if (MIDI.read()) {
    byte type = MIDI.getType();
    byte data1 = MIDI.getData1();
    byte channel = MIDI.getChannel();
}
```

Source: github:FortySevenEffects/arduino_midi_library
```

#### Workflow 4: Comparative Analysis
```
You: "Compare I2C clock speeds between Arduino Nano R4 and ESP32"

AI: Let me query both datasheets...

*runs* smartdoc query "Arduino Nano R4 I2C clock speed"
*runs* smartdoc query "ESP32 I2C clock frequency"

**Arduino Nano R4** (nano_r4.pdf, p.34):
- Standard mode: 100 kHz
- Fast mode: 400 kHz
- Fast mode plus: 1 MHz
- Default: 100 kHz

**ESP32** (esp32_datasheet.pdf, p.47):
- Standard mode: 100 kHz
- Fast mode: 400 kHz
- Maximum tested: 800 kHz
- Configurable via Wire.setClock()

**Conclusion**: Both support standard (100 kHz) and fast (400 kHz) modes.
Nano R4 officially supports up to 1 MHz, while ESP32 is tested to 800 kHz.
```

---

## Common Workflows

### Workflow 1: Indexing a New Datasheet

```bash
# 1. Copy PDF to workspace
cp ~/Downloads/component_datasheet.pdf .smartdoc_myproject/pdfs/

# 2. Index with schematic focus
smartdoc index-pdf .smartdoc_myproject/pdfs/component_datasheet.pdf --query "pinout and electrical characteristics"

# 3. Verify indexing
smartdoc list-sources

# 4. Test query
smartdoc query "operating voltage and current consumption"
```

### Workflow 2: Building a Knowledge Base

```bash
# Index multiple sources
smartdoc index-pdf .smartdoc_myproject/pdfs/mcu_datasheet.pdf
smartdoc fetch-repo https://github.com/vendor/official-library
smartdoc web https://vendor.com/docs/getting-started

# Check stats
smartdoc stats

# Query across all sources
smartdoc query "initialization sequence and required pins"
```

### Workflow 3: Troubleshooting with Logs

```bash
# Index failed or incomplete?
smartdoc logs .smartdoc_myproject/pdfs/problematic.pdf

# Check if Gemini API worked
smartdoc stats  # Check "Cached schematics" count

# Force reprocess specific query
smartdoc query "schematic details" --reprocess
```

---

## Advanced Usage

### Query Filtering

```bash
# Search only PDFs
smartdoc query "pinout" --type pdf

# Search only GitHub sources
smartdoc query "function implementation" --type github

# Search specific source
smartdoc query "voltage" --source .smartdoc_myproject/pdfs/datasheet.pdf
```

### Batch Indexing

```bash
# Index all PDFs in a directory
for pdf in .smartdoc_myproject/pdfs/*.pdf; do
    smartdoc index-pdf "$pdf"
done

# Index multiple GitHub repos
repos=(
    "https://github.com/arduino/ArduinoCore-API"
    "https://github.com/adafruit/Adafruit_Sensor"
    "https://github.com/sparkfun/SparkFun_IMU_Library"
)

for repo in "${repos[@]}"; do
    smartdoc fetch-repo "$repo"
done
```

### Workspace Management

```bash
# Backup workspace
cp -r .smartdoc_myproject .smartdoc_myproject_backup

# Reset workspace (fresh start)
rm -rf .smartdoc_myproject
smartdoc --help  # Recreates workspace

# Transfer workspace to another machine
tar -czf smartdoc_backup.tar.gz .smartdoc_myproject
# Copy to new machine, then:
tar -xzf smartdoc_backup.tar.gz
```

### Performance Optimization

**For large PDFs:**
```bash
# Use query context to focus schematic analysis
smartdoc index-pdf large_datasheet.pdf --query "power supply section and GPIO banks"
```

**For frequently queried topics:**
```bash
# Force reprocess to add focused chunks to database
smartdoc query "detailed pinout with alternate functions" --reprocess
# Future queries benefit from cached analysis
```

---

## Tips & Best Practices

1. **Use Query Context**: When indexing PDFs with schematics, use `--query` to focus analysis
2. **Check Logs**: If results seem incomplete, use `smartdoc logs` to verify processing
3. **Leverage Auto-Reprocessing**: Low-confidence answers trigger automatic schematic reanalysis
4. **Organize PDFs**: Keep related datasheets in the workspace for easier management
5. **Monitor Database Size**: Use `smartdoc stats` to track growth
6. **Backup Important Workspaces**: Copy `.smartdoc_{project_name}/` folders regularly
7. **Use Web Manager**: For visual overview and bulk operations
8. **Cite Sources**: SmartDoc provides citations - verify critical information in original docs

---

## Next Steps

- See [QUICKSTART.md](QUICKSTART.md) for installation and basic setup
- See [MANUAL.md](MANUAL.md) for advanced features and troubleshooting
- See [README.md](README.md) for architecture and development info

