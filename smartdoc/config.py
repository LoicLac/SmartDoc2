"""
Configuration settings for SmartDoc2.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

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

# Ensure workspace directory exists
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Ensure directories exist
PDFS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# Auto-create .env file in workspace if it doesn't exist
ENV_FILE = WORKSPACE_DIR / ".env"
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
    print(f"✓ Created .env file at {ENV_FILE}")
    print("  Please edit .smartdoc_workspace/.env and add your API keys")

# Auto-create .cursorrules in project root if it doesn't exist
CURSORRULES_FILE = WORKSPACE_ROOT / ".cursorrules"
if not CURSORRULES_FILE.exists():
    cursorrules_template = """# SmartDoc2 Integration Rules

## Overview
SmartDoc2: LlamaIndex-powered docs system with ChromaDB, Gemini Vision schematic analysis, automatic reprocessing, and selective knowledge addition.

## Command Mappings

### Indexing
- "Index PDF [path]" → `smartdoc index-pdf [path]`
- "Fetch [github_url]" → `smartdoc fetch-repo [github_url]`
- "Scrape [url]" → `smartdoc web [url]`

### Query
- "What/Find [question]" → `smartdoc query "[question]"`
- "Search in [source]" → `smartdoc query "[q]" --source [path]`
- "Find code" → `smartdoc query "[q]" --type github`
- Force reprocess → `smartdoc query "[q]" --reprocess`

### Management
- "List sources" → `smartdoc list-sources`
- "Show stats" → `smartdoc stats`
- "Remove [source]" → `smartdoc remove [source]`
- "View logs [source]" → `smartdoc logs [source]`
- "Launch web UI" → `smartdoc web-manager`

## Core Behavior

### Query Strategy
1. **Always check SmartDoc first** before using general knowledge
2. **Use simple query**: `smartdoc query "[question]"` (no flags needed)
3. **System auto-reprocesses** when:
   - Confidence < 0.6
   - Schematic terms detected (pin, SPI, I2C, UART, pinout, diagram, GPIO)
   - Query about hardware/connections
4. **Always cite sources** from SmartDoc results

### Automatic Reprocessing
- Expands to 10 results for schematic queries
- Checks cache first (instant if cached)
- Applies focused Gemini Vision analysis
- Selectively adds high-value findings to database
- Visual: `🔄 [Reprocessed]` or `💾 [Added to DB]`

### Response Format
```
According to [source.pdf, p.X]:
[Technical answer with specifics]

Source: [Full citation]
```

### Confidence Handling
- **> 0.8**: Answer directly with citations
- **0.6-0.8**: Answer with "Medium confidence - verify"
- **< 0.6**: System auto-reprocesses; check improved answer

### Progressive Learning
- Database learns from queries (adds focused chunks)
- Related queries benefit from previous analysis
- Monitor with `smartdoc stats` (document count increases)

## Critical Rules

1. **Source Management**: Check `smartdoc list-sources` before re-indexing
2. **Schematic Queries**: Trust automatic reprocessing (no `--reprocess` needed)
3. **Debugging**: Use `smartdoc logs [source]` for indexing issues
4. **Web UI**: Use for multi-workspace management (`smartdoc web-manager`)
5. **Database Growth**: Expect intelligent growth (selective, not bloated)

## Interface Selection

**CLI**: Indexing, quick queries, automation, single workspace
**Web UI**: Multi-workspace, bulk ops, visual logs, team collaboration

## Essential Notes

- **Workspace**: `.smartdoc_{project_name}/` (dynamically named, git-ignored)
  - Example: In "MyProject" → `.smartdoc_myproject/`
- PDF folder: `.smartdoc_{project_name}/pdfs/`
- Database: `.smartdoc_{project_name}/chroma_db/` (persistent, grows intelligently)
- Registry: `.smartdoc_{project_name}/registry.db` (tracks sources + cached analysis)
- API keys: `.smartdoc_{project_name}/.env` (auto-created with placeholders)
- File limits: 5MB warning, 50MB prompt

## Examples (Key Patterns)

**Technical Query:**
```bash
smartdoc query "SPI pins Arduino Nano R4"
# Auto-reprocesses → confidence 0.13 → 0.88
# Adds focused chunks → future queries benefit
```

**Follow-up Query:**
```bash
smartdoc query "MOSI pin Arduino Nano R4"  
# Uses focused chunks from previous → no reprocessing
```

## Error Handling

1. Failed indexing → `smartdoc logs [source]`
2. Low confidence → System auto-reprocesses
3. ChromaDB schema error → Backup DB, recreate (auto-init on next index)
4. No API key → Check .env file
5. Reprocessing not adding → Check confidence boost > 0.3, query has technical terms

## Integration Status
Active. Database persists across sessions. Auto-learns from technical queries.

# ============================================================================
# HARDWARE-SPECIFIC DEVELOPMENT RULES (Arduino/Embedded)
# Delete this entire section if you don't need hardware/embedded development assistance
# ============================================================================

## Hardware-Specific Development (Arduino/Embedded)

### Recognition Triggers
Board-specific coding when detecting:
- **Peripherals**: SPI, I2C, UART, CAN, DMA, ADC, DAC, PWM, timers
- **Low-level**: interrupts, registers, HAL, BSP, GPIO, pin configuration
- **Missing support**: "no library", "not supported", "custom implementation", "driver missing"
- **Board-specific requests**: Any mention of specific board name + peripheral (e.g., "SPI on [board]")

### Mandatory Response: Request Files First

**Before attempting code**, provide specific paths:

**Arduino IDE (macOS)**:
```
Board definitions: ~/.arduino15/packages/[vendor]/hardware/[arch]/[version]/variants/[board]/
Core drivers: ~/.arduino15/packages/[vendor]/hardware/[arch]/[version]/cores/arduino/

Files needed: pins_arduino.h, SPI.h, Wire.h, [peripheral].h

Locate commands:
find ~/.arduino15 -name "pins_arduino.h" -path "*[board]*"
find ~/.arduino15 -name "SPI.h" -path "*[vendor]*"
ls ~/.arduino15/packages/*/hardware/*/
```

**PlatformIO (macOS)**:
```
Framework: ~/.platformio/packages/framework-arduino[platform]/
Board config: ~/.platformio/platforms/[platform]/boards/[board].json

Locate commands:
find ~/.platformio -name "pins_arduino.h"
find ~/.platformio -name "SPI.h"
```

### Platform Examples

**Arduino Nano R4 / UNO R4 (Renesas)**:
```bash
# Expected location
~/.arduino15/packages/arduino/hardware/renesas_uno/1.x.x/

# Find files
find ~/.arduino15 -path "*renesas_uno*" -name "SPI.h"
find ~/.arduino15 -path "*renesas_uno*/variants/*" -name "pins_arduino.h"

# Key files
- variants/MINIMA/pins_arduino.h (or UNOWIFIR4)
- cores/arduino/SPI.h
- cores/arduino/api/HardwareSerial.h
```

**ESP32 (Arduino/PlatformIO)**:
```bash
# Arduino IDE
~/.arduino15/packages/esp32/hardware/esp32/2.x.x/

# PlatformIO
~/.platformio/packages/framework-arduinoespressif32/

# Find files
find ~/.arduino15 -path "*esp32*" -name "esp32-hal-spi.c"
find ~/.platformio -path "*esp32*" -name "pins_arduino.h"

# Key files
- variants/[board]/pins_arduino.h
- cores/esp32/esp32-hal-spi.c
- tools/sdk/esp32/include/driver/include/driver/spi_master.h
```

**STM32 (Arduino)**:
```bash
# Location
~/.arduino15/packages/STMicroelectronics/hardware/stm32/2.x.x/

# Find files
find ~/.arduino15 -path "*stm32*" -name "variant.h"

# Key files
- variants/[board]/variant.h
- system/Drivers/STM32[family]xx_HAL_Driver/Inc/stm32[family]xx_hal_spi.h
```

### Response Template

When user requests board-specific code:

```
[Board name] uses [chip]. I need board-specific files for accurate implementation:

**Expected locations**:
1. Pin definitions: [path]/pins_arduino.h
2. [Peripheral] driver: [path]/[peripheral].h
3. HAL layer: [path]/api/ or cores/

**Quick check**:
```bash
find ~/.arduino15 -path "*[arch]*" -name "[peripheral].*"
ls ~/.arduino15/packages/[vendor]/hardware/[arch]/
```

**Options**:
1. Share the files → I'll provide exact code using your board's API
2. Index with SmartDoc for persistent access:
   ```bash
   smartdoc index-pdf ~/.arduino15/packages/[vendor]/hardware/[arch]/
   smartdoc query "[peripheral] API for [board]"
   ```
3. Verify [peripheral] feature is supported in HAL (e.g., slave mode)

Note: If HAL lacks support, we may need vendor SDK directly (e.g., Renesas FSP, ESP-IDF).
```

### SmartDoc Integration for Hardware

Index board packages for persistent access:

```bash
# Index Arduino board core
smartdoc index-pdf ~/.arduino15/packages/arduino/hardware/renesas_uno/

# Index PlatformIO framework
smartdoc index-pdf ~/.platformio/packages/framework-arduinoespressif32/

# Query indexed hardware
smartdoc query "SPI slave mode API for Arduino Nano R4"
smartdoc query "ESP32 I2C pins and Wire library usage"
```

### Critical Behavior Rules

1. **Request files before code**: Predict paths based on board/platform mentioned
2. **Provide locate commands**: Help user find files with `find` commands
3. **Know common vendors**: arduino, esp32, STMicroelectronics, adafruit, sparkfun
4. **Offer SmartDoc indexing**: For persistent access to board definitions
5. **Acknowledge limitations**: If driver lacks feature, suggest vendor SDK
6. **Generic code only if**: Files unavailable after request, then add `⚠️ Verify against actual HAL`

### When Generic Code is Acceptable

Only provide without board files if:
- User explicitly says "example" or "pseudocode"
- Files confirmed unavailable
- Algorithm-only (no hardware register access)

Always add: `⚠️ Generic code - verify against your board's actual HAL API`

# ============================================================================
# END OF HARDWARE-SPECIFIC RULES
# ============================================================================
"""
    CURSORRULES_FILE.write_text(cursorrules_template)
    print(f"✓ Created .cursorrules at {CURSORRULES_FILE}")
    print("  Cursor AI will now use SmartDoc integration + hardware file discovery")

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

# Registry Database
REGISTRY_DB = str(WORKSPACE_DIR / "registry.db")

# Vision Settings
GEMINI_MODEL = "gemini-2.5-pro"  # Gemini 2.5 Pro (stable, released June 2025)
GEMINI_TEMPERATURE = 0.1  # Low temperature for technical accuracy
VISION_MAX_RETRIES = 3
VISION_CACHE_ENABLED = True

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

