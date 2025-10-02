# SmartDoc2 User Manual

Complete reference for advanced features, troubleshooting, and web-based management.

## Table of Contents

- [Web Manager UI](#web-manager-ui)
- [Processing Logs](#processing-logs)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

---

## Web Manager UI

### Overview

The Web Manager is a browser-based UI for managing multiple SmartDoc databases across your project workspaces. It scans a root directory (e.g., `~/Code`) to find all SmartDoc instances and lets you view, delete, and transfer data between them.

### Launch the Web Manager

```bash
# Scan parent directory of current workspace (default)
smartdoc web-manager

# Specify a custom root directory
smartdoc web-manager --root ~/Code

# Run on a different port
smartdoc web-manager --port 8080

# Create a public share link (for remote access)
smartdoc web-manager --share
```

The UI will open in your default browser at `http://localhost:7860`.

### Features

#### 📊 Dashboard Tab

**Database List (Top)**
- Auto-discovers all SmartDoc databases in your root directory
- Shows: workspace name, path, sources count, documents count, total size
- Refresh button to re-scan directory

**Asset Details (Bottom)**
- Select a database (enter row #)
- Click "Load Database" to view all assets
- Shows: source name, type, status, pages/size, indexed date
- Actions available:
  - 🗑️ Delete selected assets
  - 📋 View processing logs

**How to Use:**
1. View database list at top
2. Enter row number (e.g., `0` for first database)
3. Click "Load Database"
4. View all assets in that database
5. Select rows to delete: `0,1,2` or `0-5`
6. Click "Delete Selected" or "View Logs"

#### 🔄 Transfer & Copy Tab

**Split View:**
- Left: Source database
- Right: Destination database

**Operations:**
- **Copy**: Duplicate assets to another database (keeps original)
- **Move**: Transfer assets and remove from source

**How to Use:**
1. Select source database
2. Select destination database
3. Load assets from source
4. Select asset rows: `0,1,2`
5. Click "Copy" or "Move"

**Use Cases:**
- Merge multiple project databases
- Backup specific sources
- Organize assets by project
- Share knowledge between teams

### Tips

- Use row numbers for selection: `0,1,2` or `0-5` (range)
- Refresh if databases don't appear
- Changes are immediate (no undo!)
- Close duplicates before transferring

---

## Processing Logs

### Overview

SmartDoc2 tracks detailed processing logs for every indexed source, making it easy to diagnose why Gemini Vision or LlamaParse might have failed during ingestion.

### What's Logged

For each PDF ingestion:

1. **Text Extraction Step**
   - Number of chunks extracted
   - Method used (LlamaParse or fallback)
   - Success/failure status

2. **Schematic Analysis Step**
   - Images found in PDF
   - Schematics detected (after filtering)
   - Analysis results (successful/failed/cached)
   - Detailed error messages for failures
   - Gemini Vision API errors

3. **Database Storage Step**
   - Chunks stored
   - Storage status

### Viewing Processing Logs

#### CLI Command

```bash
smartdoc logs "path/to/your/file.pdf"
```

**Example:**
```bash
smartdoc logs ".smartdoc_workspace/pdfs/Arduino Nano R4.pdf"
```

**Output:**
```
╭─────────────── Source Information ───────────────╮
│ PDF: .smartdoc_workspace/pdfs/nano_r4.pdf       │
│ Status: success | Indexed: 2025-10-02 18:11:39  │
╰─────────────────────────────────────────────────╯

                     Processing Log                      
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Step        ┃ Status  ┃ Message     ┃ Details     ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ text_extra… │ success │ 13 chunks   │ method:     │
│ schematic_… │ success │ 1 analyzed  │ images: 1   │
│ storage     │ success │ Stored 14   │ chunks: 14  │
└─────────────┴─────────┴─────────────┴─────────────┘
```

#### Web UI

1. Navigate to Dashboard tab
2. Load the database
3. Select the asset row
4. Click "📋 Logs" button
5. View detailed processing history

### Common Issues

#### Issue: "Text extraction failed"
**Causes:**
- Corrupted PDF
- Encrypted/protected PDF
- Invalid PDF format

**Solutions:**
- Try re-downloading the PDF
- Use `--no-schematics` flag
- Check file integrity

#### Issue: "Gemini analysis failed"
**Causes:**
- Missing/invalid `GEMINI_API_KEY`
- API rate limits
- Network issues
- Invalid image data

**Solutions:**
- Check `.smartdoc_workspace/.env` has valid `GEMINI_API_KEY`
- Wait a few minutes (rate limit)
- Check network connectivity
- Re-index with `--no-schematics` to skip vision

#### Issue: "0 schematics found"
**Causes:**
- PDF has no images
- Images too small (< 200px)
- Images are photos, not schematics

**Solutions:**
- Verify PDF has technical diagrams
- Check logs: `smartdoc logs [path]`
- This is normal for text-only PDFs

---

## Advanced Features

### Progressive Learning

SmartDoc learns from your queries! When you ask technical questions, the system:

1. **Detects schematic queries** (SPI, I2C, pinout, etc.)
2. **Auto-reprocesses** with focused Gemini Vision analysis
3. **Selectively adds** high-value findings to database
4. **Improves future queries** automatically

**Example:**
```bash
# First query - triggers learning
smartdoc query "Arduino Nano R4 SPI pins"
# Confidence: 0.13 → 0.88
# Database: 70 → 73 documents (+3 focused chunks)

# Second query - benefits from learning
smartdoc query "MOSI pin Arduino Nano R4"
# Confidence: 0.17 (improved!)
# No reprocessing needed
```

**Monitor Growth:**
```bash
smartdoc stats
# Shows document count increasing over time
```

### Schematic Cache

All reprocessed schematic analyses are cached in `registry.db`:

- **First query**: Analyzes with Gemini Vision (slow)
- **Repeat query**: Uses cache (instant!)
- **Different query, same schematic**: New analysis
- **Cache location**: `.smartdoc_workspace/registry.db`

**Clear cache:**
```bash
# Only if needed - cache is beneficial!
rm .smartdoc_workspace/registry.db
# Will recreate on next command
```

### Multi-Workspace Setup

Use multiple workspaces for different projects:

```bash
# Project 1
cd ~/Code/Project1
smartdoc index-pdf .smartdoc_workspace/pdfs/datasheet1.pdf

# Project 2
cd ~/Code/Project2
smartdoc index-pdf .smartdoc_workspace/pdfs/datasheet2.pdf

# View all from web manager
smartdoc web-manager --root ~/Code
```

**Benefits:**
- Isolated knowledge bases per project
- Easy to backup/delete per project
- Web UI shows all at once
- Transfer knowledge between projects

---

## Troubleshooting

### Database Issues

#### ChromaDB Schema Error
```
Error: no such column: collections.topic
```

**Solution:**
```bash
# Backup current database
cp -r .smartdoc_workspace/chroma_db .smartdoc_workspace/chroma_db.backup

# Delete and recreate
rm -rf .smartdoc_workspace/chroma_db

# Re-index sources
smartdoc list-sources  # Will auto-recreate
```

#### Database Locked
```
Error: database is locked
```

**Solution:**
```bash
# Close all SmartDoc processes
pkill -f smartdoc

# Remove lock files
rm .smartdoc_workspace/registry.db-journal

# Retry command
```

### API Key Issues

#### Gemini Vision Not Working
**Check `.smartdoc_workspace/.env`:**
```bash
cat .smartdoc_workspace/.env
# Verify GEMINI_API_KEY is set
```

**Test API key:**
```bash
python3 -c "
from smartdoc.config import GEMINI_API_KEY
print('OK' if GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here' else 'MISSING')
"
```

#### LlamaParse Optional
If `LLAMAPARSE_API_KEY` is not set, SmartDoc uses PyPDF2 fallback (still works!):
- No error
- Slightly less accurate text extraction
- Schematic analysis still works

### Performance Issues

#### Slow Queries
**Causes:**
- Large database (> 1000 documents)
- Complex queries
- First-time schematic reprocessing

**Solutions:**
- Use `--source` filter to narrow search
- Cache warms up after first query
- Consider splitting into multiple workspaces

#### Large Memory Usage
**Causes:**
- Many large PDFs indexed
- ChromaDB in-memory cache

**Solutions:**
- Close unused SmartDoc processes
- Restart if memory grows too large
- Split large PDFs if possible

### Indexing Issues

#### Large File Warning
```
⚠️ Large file: datasheet.pdf (5.3MB)
```

**Action:** File will process but may take longer
**Limits:**
- < 5MB: No warning
- 5-50MB: Warning shown
- > 50MB: Prompts for confirmation

#### GitHub Rate Limits
```
Error: API rate limit exceeded
```

**Solution:**
Add GitHub token to `.smartdoc_workspace/.env`:
```bash
GITHUB_TOKEN=your_github_personal_access_token
```
Get token: https://github.com/settings/tokens

---

## Best Practices

### 1. Regular Maintenance
```bash
# Check database health
smartdoc stats

# View indexed sources
smartdoc list-sources

# Clean up failed sources
smartdoc remove [failed_source]
```

### 2. Backup Strategy
```bash
# Backup entire workspace
cp -r .smartdoc_workspace .smartdoc_workspace.backup

# Or just the database
cp -r .smartdoc_workspace/chroma_db backups/chroma_db_$(date +%Y%m%d)
```

### 3. Version Control
Add to `.gitignore`:
```
.smartdoc_workspace/
```
**Don't commit:**
- API keys (.env)
- Databases (large)
- PDFs (copyrighted)

### 4. Team Sharing
**Option A: Shared Database**
- Use network drive
- Point to shared `.smartdoc_workspace/`

**Option B: Individual Databases + Web UI**
- Each member has own workspace
- Use web manager to view all
- Transfer knowledge as needed

---

## FAQ

**Q: Can I have multiple workspaces?**
A: Yes! Each project can have its own `.smartdoc_workspace/`. Use web manager to view all.

**Q: How much disk space does SmartDoc use?**
A: Typically 2-3x the size of indexed PDFs (includes embeddings).

**Q: Can I use SmartDoc offline?**
A: Partially. Querying works offline, but Gemini Vision requires internet.

**Q: How do I update API keys?**
A: Edit `.smartdoc_workspace/.env` and restart any running commands.

**Q: Can I index private GitHub repos?**
A: Yes! Add `GITHUB_TOKEN` to `.smartdoc_workspace/.env`.

**Q: What happens if I delete `.smartdoc_workspace/`?**
A: All data is lost. You'll need to re-index everything. Backup first!

**Q: Can I move `.smartdoc_workspace/` to another location?**
A: Yes, but update paths or re-index. Easier to keep it in project root.

**Q: How do I reset everything?**
A: `rm -rf .smartdoc_workspace/` then re-index sources.

---

## Support

For issues, feature requests, or questions:
- Check logs: `smartdoc logs [source]`
- View stats: `smartdoc stats`
- Check this manual
- Review QUICKSTART.md for basics

