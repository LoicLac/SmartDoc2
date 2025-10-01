# SmartDoc2 - Mac Silicon Global Installation Guide

## 🚀 One-Command Installation

```bash
cd /Users/loic/Code/SmartDoc2
./install_global_mac.sh
```

This installs SmartDoc2 globally with MCP integration for natural language use in Cursor.

---

## ✅ What Gets Installed

### 1. Global Python Package
- `smartdoc` CLI available system-wide
- Installed via `python3 -m pip install -e`
- Works in any terminal/workspace

### 2. Global Configuration
```
~/.smartdoc/
├── .env                    # Your API keys (global)
├── data/                   # Shared database across workspaces
│   ├── pdfs/              # Drop PDFs here
│   ├── chroma_db/         # Vector database
│   └── temp/              # Temporary files
└── link_workspace.sh      # Quick workspace setup
```

### 3. MCP Server for Cursor
- Located: `/Users/loic/Code/SmartDoc2/smartdoc_mcp_server.py`
- Auto-configured in Cursor's MCP settings
- Enables natural language queries in Cursor/Claude

### 4. Shell Integration
Added to `~/.zshrc`:
```bash
export SMARTDOC_HOME="$HOME/.smartdoc"
export SMARTDOC_DATA="$HOME/.smartdoc/data"
alias smartdoc-link="~/.smartdoc/link_workspace.sh"
```

---

## 🔑 Step-by-Step Setup

### Step 1: Run Installer
```bash
cd /Users/loic/Code/SmartDoc2
./install_global_mac.sh
```

**What it does:**
- ✅ Checks Python3 (uses Homebrew if needed)
- ✅ Installs SmartDoc globally
- ✅ Creates `~/.smartdoc/` directory
- ✅ Sets up MCP server configuration
- ✅ Initializes databases
- ✅ Adds shell aliases

### Step 2: Add API Keys
```bash
# Edit the config file
nano ~/.smartdoc/.env

# Add your keys:
LLAMAPARSE_API_KEY=your_llamaparse_key_here
GEMINI_API_KEY=your_gemini_key_here
GITHUB_TOKEN=your_github_token_here  # Optional
```

**Get API keys:**
- LlamaParse: https://cloud.llamaindex.ai/parse
- Gemini: https://makersuite.google.com/app/apikey
- GitHub: https://github.com/settings/tokens (optional, for higher rate limits)

### Step 3: Restart Cursor
```bash
# Quit and reopen Cursor completely
# This loads the MCP server
```

### Step 4: Reload Shell
```bash
source ~/.zshrc
```

### Step 5: Test Installation
```bash
# Test CLI
smartdoc stats

# Should output:
# SmartDoc2 Statistics
# Total sources: 0
# Total documents: 0
```

---

## 🎯 Using SmartDoc2

### Option A: Command Line (Any Terminal)

```bash
# Index a PDF
smartdoc index-pdf ~/Downloads/arduino_datasheet.pdf

# Fetch GitHub repo
smartdoc fetch-repo https://github.com/arduino/MIDI

# Query
smartdoc query "What are the SPI pins?" --reprocess

# List sources
smartdoc list-sources

# Get stats
smartdoc stats
```

### Option B: Natural Language in Cursor (via MCP)

Just ask Claude naturally - it will use SmartDoc automatically:

```
You: "Index the Arduino Nano R4 datasheet at ~/Downloads/nano_r4.pdf"
Claude: [Uses smartdoc_index_pdf tool automatically]

You: "What are the SPI pins on the Arduino Nano R4?"
Claude: [Uses smartdoc_query tool with reprocess=true]

You: "Fetch the Arduino MIDI library from GitHub"
Claude: [Uses smartdoc_fetch_repo tool]

You: "Show me what documentation I have indexed"
Claude: [Uses smartdoc_list_sources tool]
```

**No manual commands needed!** Claude understands your intent and calls the right SmartDoc tools.

---

## 📦 Adding SmartDoc to New Workspaces

### Quick Method
```bash
cd ~/your-new-project
smartdoc-link
```

This:
1. Links `~/.smartdoc/data` → `./data` (shared database)
2. Copies `.cursorrules` to workspace
3. Ready to use!

### Manual Method
```bash
cd ~/your-new-project

# Link global data
ln -s ~/.smartdoc/data data

# Copy cursor rules
cp /Users/loic/Code/SmartDoc2/.cursorrules .
```

**Result**: All workspaces share the same SmartDoc database. Index once, use everywhere!

---

## 🔍 Available MCP Tools

When using Cursor/Claude, these tools are automatically available:

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `smartdoc_index_pdf` | Index PDF with schematic analysis | "Index this datasheet" |
| `smartdoc_fetch_repo` | Clone and index GitHub repo | "Fetch the MIDI library" |
| `smartdoc_index_web` | Scrape web documentation | "Index Arduino docs site" |
| `smartdoc_query` | Semantic search with citations | "What are the I2C pins?" |
| `smartdoc_list_sources` | Show indexed sources | "What docs do I have?" |
| `smartdoc_stats` | Database statistics | "Show database stats" |

---

## 🎨 Example Workflow

### 1. Index Your Documentation
```bash
# In any workspace with smartdoc-link
cd ~/my-arduino-project
smartdoc-link

# Drop PDFs in shared folder
cp ~/Downloads/nano_r4.pdf ~/.smartdoc/data/pdfs/

# Index via Cursor
```

In Cursor, just say:
```
"Index the nano_r4.pdf datasheet"
```

### 2. Ask Technical Questions

```
"What are the SPI pins on the Nano R4?"
```

Claude will:
1. Search SmartDoc database
2. Calculate confidence score
3. If low confidence + schematic query → reprocess with Gemini Vision
4. Return answer with citations: `[nano_r4.pdf, p.23]`

### 3. Add Code Examples

```
"Fetch the Arduino MIDI library from GitHub"
```

Claude indexes the entire repo with code-aware chunking.

### 4. Query Code

```
"Show me how to send a MIDI note-on message"
```

Claude searches code and returns examples with file citations.

---

## 🔧 Troubleshooting

### MCP Server Not Working

**Check if MCP is configured:**
```bash
cat ~/Library/Application\ Support/Cursor/User/globalStorage/mcp_settings.json
```

Should contain:
```json
{
  "mcpServers": {
    "smartdoc": {
      "command": "python3",
      "args": ["/Users/loic/Code/SmartDoc2/smartdoc_mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/loic/Code/SmartDoc2"
      }
    }
  }
}
```

**If missing, add manually:**
1. Open Cursor Settings
2. Search for "MCP"
3. Add SmartDoc server configuration

**Test MCP server manually:**
```bash
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 smartdoc_mcp_server.py
```

Should return list of tools.

### API Key Errors

```bash
# Verify keys are set
cat ~/.smartdoc/.env

# Test Gemini key
python3 << EOF
import os
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.smartdoc/.env"))
print("Gemini:", "✓" if os.getenv("GEMINI_API_KEY") else "✗")
print("LlamaParse:", "✓" if os.getenv("LLAMAPARSE_API_KEY") else "✗")
EOF
```

### Command Not Found

```bash
# Find where smartdoc was installed
python3 -m pip show smartdoc2

# Add to PATH if needed
export PATH="$HOME/Library/Python/3.11/bin:$PATH"
```

### Database Issues

```bash
# Check database location
ls -la ~/.smartdoc/data/

# Reset database (⚠️ destroys all data)
smartdoc reset --confirm
```

---

## 🔄 Updating SmartDoc2

```bash
cd /Users/loic/Code/SmartDoc2
git pull  # If tracking from repo

# Reinstall
python3 -m pip install -e . --upgrade

# Restart Cursor
```

---

## 🎓 Advanced Usage

### Custom Data Location

Edit `~/.zshrc`:
```bash
export SMARTDOC_DATA="/path/to/custom/location"
```

### Multiple Databases (Per Project)

```bash
# Don't use smartdoc-link
# Instead, let each workspace have its own data/
cd ~/project1
smartdoc index-pdf datasheet.pdf  # Uses ./data/

cd ~/project2
smartdoc index-pdf other.pdf  # Uses ./data/
```

### Batch Indexing

```bash
# Index all PDFs in a folder
for pdf in ~/.smartdoc/data/pdfs/*.pdf; do
    smartdoc index-pdf "$pdf"
done

# Or create a script
cat > ~/batch_index.sh << 'EOF'
#!/bin/bash
find ~/.smartdoc/data/pdfs -name "*.pdf" -exec smartdoc index-pdf {} \;
EOF
chmod +x ~/batch_index.sh
```

---

## 📊 Performance Tips

1. **Schematic Analysis**: First indexing of PDFs is slow (vision analysis). Subsequent queries are fast (cached).

2. **GitHub Repos**: Clone time depends on repo size. Indexing is smart about skipping large files.

3. **Query Speed**: First query loads models (3-5 seconds). Subsequent queries are instant (<1 second).

4. **Database Size**: Typical setup uses 10-50MB for embedded systems docs.

---

## 🎉 You're All Set!

SmartDoc2 is now globally available:
- ✅ `smartdoc` CLI works everywhere
- ✅ Cursor/Claude can use SmartDoc via MCP
- ✅ Single shared database across workspaces
- ✅ Natural language integration

**Start using it:**
```bash
# Add to new workspace
cd ~/your-project
smartdoc-link

# Ask Claude in Cursor
"Index my datasheet and tell me the I2C pins"
```

Happy documenting! 🚀

