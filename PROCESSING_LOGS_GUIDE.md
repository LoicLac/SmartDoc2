# Processing Logs Guide

## Overview

SmartDoc2 now tracks detailed processing logs for every indexed source, making it easy to diagnose why Gemini Vision or LlamaParse might have failed during ingestion.

## What's Logged

For each PDF ingestion, the system logs:

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

## Viewing Processing Logs

### CLI Command

```bash
smartdoc logs "path/to/your/file.pdf"
```

**Example:**
```bash
smartdoc logs "data/pdfs/Arduino Nano R4.pdf"
```

This shows:
- ✅ Step-by-step processing log with timestamps
- ⚠️ Warnings and errors with details
- 📊 Summary statistics
- 🔍 Specific error messages (e.g., Gemini API failures)

### Sample Output

```
╭─────────────── Source Information ───────────────╮
│ PDF: data/pdfs/nano_r4.pdf                      │
│ Status: success | Indexed: 2025-10-01 14:23:15  │
╰──────────────────────────────────────────────────╯

                    Processing Log
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Step              ┃ Status  ┃ Message            ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ text_extraction   │ success │ Extracted 15 chunks│
│ schematic_analysis│ warning │ Found 2 schematics │
│                   │         │ 0 successful       │
└───────────────────┴─────────┴────────────────────┘

Errors in schematic_analysis:
  • Page 1: GEMINI_API_KEY not configured
  • Page 2: GEMINI_API_KEY not configured

Summary: 1 successful, 0 failed, 2 errors
```

## Common Issues & Solutions

### Issue 1: `schematic_chunks: 0` in metadata

**Possible causes:**

1. **No images in PDF**
   - Check logs: `images_found: 0`
   - Solution: PDF has no embedded images

2. **Images filtered out**
   - Check logs: `images_found: 5, schematics_found: 0`
   - Solution: Images were too small/large or wrong format
   - Images need to be at least 200x200px and technical-looking

3. **Gemini Vision failed**
   - Check logs: `analysis_failed: 2`
   - Look for error messages in Details column
   - Common errors:
     - `GEMINI_API_KEY not set`
     - API rate limit exceeded
     - Invalid image format

4. **Analysis successful but empty descriptions**
   - Check logs: `analysis_successful: 2` but `schematic_chunks: 0`
   - Gemini returned empty/invalid responses

### Issue 2: LlamaParse Failures

Check logs for `text_extraction` step:
- Status `failed` = LlamaParse error
- Fallback to PyPDF2 is automatic
- Check `method: fallback` in details

### Issue 3: Missing API Keys

**Symptoms:**
```
analysis_failed: 2
Error: GEMINI_API_KEY not configured
```

**Solution:**
1. Create `.env` file in project root
2. Add: `GEMINI_API_KEY=your_key_here`
3. Restart and re-index: `smartdoc index-pdf your-file.pdf`

## Logs for Existing Sources

⚠️ **Note:** Processing logs are only available for sources indexed **after** this feature was added.

To get logs for old sources:
1. Remove the source: `smartdoc remove "path/to/file.pdf"`
2. Re-index it: `smartdoc index-pdf "path/to/file.pdf"`
3. View logs: `smartdoc logs "path/to/file.pdf"`

## Technical Details

### Database Schema

Logs are stored in `data/registry.db` in the `processing_logs` table:

```sql
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    step TEXT,              -- e.g., "text_extraction"
    status TEXT,            -- "success", "failed", "warning", "skipped"
    message TEXT,           -- Human-readable message
    details TEXT,           -- JSON with detailed metrics
    timestamp TIMESTAMP
);
```

### Programmatic Access

```python
from smartdoc.core.registry import Registry

registry = Registry()
logs = registry.get_processing_logs("data/pdfs/your-file.pdf")

for log in logs:
    print(f"{log['step']}: {log['status']}")
    if log['details']:
        print(f"  Details: {log['details']}")
```

## Future Enhancements

Coming soon:
- 🌐 Web UI integration (view logs in SmartDoc Database Manager)
- 📊 Dashboard with processing statistics
- 🔔 Automatic retry for failed analyses
- 📧 Email notifications for failures

## Questions?

See the main [README.md](README.md) or check [QUICKSTART.md](QUICKSTART.md) for general usage.


