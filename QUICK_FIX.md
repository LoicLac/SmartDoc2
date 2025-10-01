# ✅ PATH Issue Fixed!

## What Happened
The installer placed `smartdoc` in `/Users/loic/Library/Python/3.9/bin` which wasn't in your PATH.

## Already Fixed For You ✓
I've added this to your `~/.zshrc`:
```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

## Apply the Fix Now

**Option 1: Reload Shell (Recommended)**
```bash
source ~/.zshrc
smartdoc --help  # Should work now!
```

**Option 2: New Terminal**
Open a new terminal tab/window - PATH will be set automatically.

## Test Installation

```bash
# Should show help
smartdoc --help

# Should show empty database
smartdoc stats
```

## Next Steps

### 1. Add API Keys
```bash
nano ~/.smartdoc/.env
```

Add:
```
LLAMAPARSE_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

Get keys:
- LlamaParse: https://cloud.llamaindex.ai/parse
- Gemini: https://makersuite.google.com/app/apikey

### 2. Restart Cursor
Quit Cursor completely and reopen to load the MCP server.

### 3. Test with a PDF

```bash
# Create test directory
mkdir -p ~/.smartdoc/data/pdfs

# Copy a PDF there or use an existing one
smartdoc index-pdf ~/path/to/your/datasheet.pdf
```

### 4. Try Natural Language in Cursor

Open Cursor and ask Claude:
```
"Show me the SmartDoc database statistics"
"What documentation do I have indexed?"
```

If MCP is working, Claude will use SmartDoc tools automatically!

## Troubleshooting

### Still "command not found"?
```bash
# Check if smartdoc exists
ls -la ~/Library/Python/3.9/bin/smartdoc

# Manually add to current session
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

# Verify
which smartdoc
```

### SSL Warning (Safe to Ignore)
You might see:
```
urllib3 v2 only supports OpenSSL 1.1.1+, currently 'ssl' module is compiled with 'LibreSSL 2.8.3'
```

This is harmless - SmartDoc will work fine. It's just a compatibility notice.

### MCP Not Working in Cursor?

Check config exists:
```bash
cat ~/Library/Application\ Support/Cursor/User/globalStorage/mcp_settings.json
```

Should contain SmartDoc server. If missing, manually add:
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

## You're Ready! 🚀

```bash
# Reload shell
source ~/.zshrc

# Test
smartdoc stats

# Add API keys
nano ~/.smartdoc/.env

# Restart Cursor

# Start using it!
```

