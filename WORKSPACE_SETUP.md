# Adding SmartDoc2 to New Workspaces

## 🚀 Quick Methods (Choose One)

### Method 1: One Command (Easiest) ⭐
```bash
cd ~/your-new-workspace
smartdoc-add
```

This will:
1. Copy `.cursorrules` to workspace
2. Ask if you want to link global data (shared database) or create local data
3. Ready to use!

---

### Method 2: Manual Copy
```bash
cd ~/your-new-workspace

# Copy rules
cp /Users/loic/Code/SmartDoc2/.cursorrules .

# Option A: Link to shared global database
ln -s ~/.smartdoc/data data

# Option B: Create local database for this workspace only
mkdir -p data/pdfs data/chroma_db data/temp
```

---

### Method 3: One-Liner
```bash
cd ~/your-new-workspace && cp /Users/loic/Code/SmartDoc2/.cursorrules . && ln -s ~/.smartdoc/data data && echo "✅ SmartDoc2 added!"
```

---

## 🔍 What Gets Added

### .cursorrules File
Contains instructions for Claude/Cursor on how to use SmartDoc2:
- Natural language command mapping
- When to use SmartDoc vs general knowledge
- Citation formatting
- Confidence-based suggestions

### data Directory (Optional)
- **Linked** (`ln -s`): Shares database across all workspaces
- **Local** (`mkdir`): Each workspace has its own database

---

## 🎯 Recommended Setup by Use Case

### Single Project Focus
```bash
cd ~/my-arduino-project
smartdoc-add
# Choose: Link to global data (y)
```

**Result**: All workspaces share same documentation database.

### Multiple Separate Projects
```bash
cd ~/project-a
smartdoc-add
# Choose: Link to global data (n)

cd ~/project-b
smartdoc-add
# Choose: Link to global data (n)
```

**Result**: Each project has isolated documentation.

### Team/Shared Projects
```bash
cd ~/team-project

# Only add rules (no data folder)
cp /Users/loic/Code/SmartDoc2/.cursorrules .

# Let team members use their own SmartDoc setup
```

---

## 🧪 Test After Setup

### Test 1: Check Files
```bash
cd ~/your-workspace

# Should exist
ls -la .cursorrules
ls -la data/

# If linked, should show symlink
ls -la data
# lrwxr-xr-x ... data -> /Users/loic/.smartdoc/data
```

### Test 2: CLI
```bash
cd ~/your-workspace
smartdoc stats
# Should show database (global or local)
```

### Test 3: Cursor Integration
Open workspace in Cursor and ask Claude:
```
"Show me SmartDoc database statistics"
```

Claude should use the `smartdoc_stats` tool automatically.

---

## 📂 Workspace Structure

### With Global Data (Linked)
```
your-workspace/
├── .cursorrules          ← SmartDoc instructions for Claude
├── data/                 ← Symlink to ~/.smartdoc/data
│   ├── pdfs/            ← Shared across all workspaces
│   ├── chroma_db/       ← Shared vector database
│   └── temp/
└── your-code/
```

### With Local Data
```
your-workspace/
├── .cursorrules          ← SmartDoc instructions for Claude
├── data/                 ← Local to this workspace
│   ├── pdfs/            ← Workspace-specific PDFs
│   ├── chroma_db/       ← Workspace-specific database
│   └── temp/
└── your-code/
```

---

## 🔄 Updating Rules

If SmartDoc2 `.cursorrules` get updated:

```bash
cd ~/your-workspace

# Backup current rules (optional)
cp .cursorrules .cursorrules.backup

# Update to latest
cp /Users/loic/Code/SmartDoc2/.cursorrules .

echo "✅ Rules updated"
```

Or use `smartdoc-add` and overwrite when prompted.

---

## 🎨 Customizing for Workspace

You can customize `.cursorrules` per workspace:

```bash
cd ~/your-workspace
nano .cursorrules

# Add workspace-specific instructions, like:
# "This workspace uses Arduino Nano R4 - prioritize nano_r4.pdf"
# "Always use --reprocess for schematic queries"
```

---

## 🗑️ Removing SmartDoc from Workspace

### Keep Data
```bash
cd ~/your-workspace
rm .cursorrules
# Keep data/ folder
```

### Remove Everything
```bash
cd ~/your-workspace
rm .cursorrules
rm -rf data/  # or unlink data if symlink
```

**Note**: If using global shared data, removing workspace doesn't delete the database.

---

## 💡 Pro Tips

### 1. Template Workspace
Create a template with SmartDoc pre-configured:
```bash
mkdir ~/workspace-template
cd ~/workspace-template
smartdoc-add
# Choose: Link to global data (y)

# When starting new project:
cp -r ~/workspace-template ~/new-project
```

### 2. Git Integration
Add to `.gitignore`:
```bash
echo "data/" >> .gitignore
```

**Why**: Don't commit database to git. Team members should use their own SmartDoc.

**Do commit**:
```bash
git add .cursorrules
git commit -m "Add SmartDoc2 integration"
```

### 3. Batch Setup
Setup multiple workspaces at once:
```bash
for workspace in ~/projects/*; do
    cd "$workspace"
    cp /Users/loic/Code/SmartDoc2/.cursorrules .
    ln -s ~/.smartdoc/data data
    echo "✓ Added to $workspace"
done
```

---

## 🔧 Troubleshooting

### "Command smartdoc-add not found"
```bash
# Reload shell
source ~/.zshrc

# Or use direct path
bash ~/.smartdoc/add-to-workspace.sh
```

### ".cursorrules not copied"
```bash
# Check if source exists
ls -la /Users/loic/Code/SmartDoc2/.cursorrules

# Copy manually
cp /Users/loic/Code/SmartDoc2/.cursorrules .
```

### "Symlink failed"
```bash
# Remove existing data folder first
rm -rf data

# Create symlink
ln -s ~/.smartdoc/data data

# Verify
ls -la data
```

### "Claude not using SmartDoc"
1. **Check .cursorrules exists**:
   ```bash
   cat .cursorrules | head -5
   ```

2. **Restart Cursor**: Quit completely (Cmd+Q) and reopen

3. **Check MCP**: Ask Claude:
   ```
   "What tools do you have available?"
   ```
   Should list SmartDoc tools.

---

## 🎯 Quick Reference

| Action | Command |
|--------|---------|
| Add to workspace | `smartdoc-add` |
| Copy rules only | `cp /Users/loic/Code/SmartDoc2/.cursorrules .` |
| Link global data | `ln -s ~/.smartdoc/data data` |
| Create local data | `mkdir -p data/pdfs data/chroma_db data/temp` |
| Update rules | `smartdoc-add` (overwrite when asked) |
| Test setup | `smartdoc stats` |

---

## ✅ Success Checklist

After adding SmartDoc to a workspace:

- [ ] `.cursorrules` file exists in workspace root
- [ ] `data/` directory exists (linked or local)
- [ ] `smartdoc stats` works from workspace
- [ ] Claude in Cursor responds to "Show SmartDoc stats"
- [ ] Can ask Claude to index PDFs naturally

---

**You're ready!** Start by running:
```bash
cd ~/your-workspace
smartdoc-add
```

