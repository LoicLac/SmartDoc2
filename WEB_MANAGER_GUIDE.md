# SmartDoc Web Manager Guide

## Overview

The Web Manager is a browser-based UI for managing multiple SmartDoc databases across your project workspaces. It scans a root directory (e.g., `~/Code`) to find all SmartDoc instances and lets you view, delete, and transfer data between them.

## Installation

First, install the new dependency:

```bash
pip install -r requirements.txt
```

Or install just Gradio:

```bash
pip install gradio==4.12.0
```

## Usage

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

## Features

### 📊 Database Overview

- **Auto-discovery**: Automatically finds all SmartDoc databases in your root directory
- **Summary table**: Shows workspace name, path, sources count, documents count, size, and status
- **Refresh**: Re-scan the directory to find new databases

### 🗃️ Browse & Delete

- **Select workspace**: Choose a database to explore
- **View sources**: See all indexed sources (PDFs, GitHub repos, web pages)
- **Delete sources**: Select sources by row index and delete them
  - Example: Enter `0,1,2` to delete the first three sources
- **Bulk operations**: Delete multiple sources at once

### 🔄 Transfer Data

- **Copy between workspaces**: Transfer sources from one database to another
- **Move option**: Check "Move" to delete from source after copying
- **Preserve metadata**: All metadata, schematic cache, and documents are transferred
- **Multi-select**: Transfer multiple sources in one operation

### 📈 Statistics

- **Detailed stats**: Per-database statistics
- **Source breakdown**: See sources by type (PDF, GitHub, Web)
- **Storage info**: Monitor database sizes

## Use Cases

### 1. Consolidate Documentation

You have Arduino documentation in multiple project workspaces and want to merge them:

1. Launch web manager: `smartdoc web-manager --root ~/Code`
2. Go to **Transfer Data** tab
3. Select source workspace (e.g., `ProjectA`)
4. Select destination workspace (e.g., `MasterDocs`)
5. Select sources to transfer
6. Click **Transfer**

### 2. Clean Up Old Projects

Remove outdated documentation from inactive projects:

1. Go to **Browse & Delete** tab
2. Select workspace from dropdown
3. Review sources
4. Enter row indices of sources to delete (e.g., `0,2,4`)
5. Click **Delete Selected**

### 3. Move Data Between Projects

Transfer specific datasheets from one project to another:

1. Go to **Transfer Data** tab
2. Select source and destination workspaces
3. Enter row indices to transfer
4. Check **Move** if you want to delete from source
5. Click **Transfer**

### 4. Monitor All Databases

Get an overview of all your SmartDoc instances:

1. Go to **Database Overview** tab
2. See all workspaces at a glance
3. Check status and sizes
4. Identify which projects have documentation indexed

## Row Selection

In the **Browse & Delete** and **Transfer Data** tabs, you need to specify row indices:

- Rows are zero-indexed (first row = 0)
- Use comma-separated values: `0,1,2`
- Example: `0` = first source, `1` = second source, etc.

## Technical Details

### Database Discovery

The manager scans recursively for directories containing:
- `data/registry.db` (SQLite database)
- `data/chroma_db/` (ChromaDB vector database)

### Transfer Process

When transferring sources:
1. Source metadata copied to destination registry
2. Schematic cache copied (if exists)
3. All document chunks copied to destination ChromaDB
4. If "move" mode: source data deleted after successful copy

### Database Structure

Each workspace maintains:
- **Registry DB** (`data/registry.db`): SQLite database tracking sources and schematic cache
- **ChromaDB** (`data/chroma_db/`): Vector database storing document embeddings
- **PDFs** (`data/pdfs/`): Optional local PDF storage

## Safety Notes

- **Backups**: The transfer operation doesn't create backups. Back up important databases before large operations.
- **Move vs Copy**: "Move" deletes from source after copying. Use carefully.
- **Concurrent access**: Avoid running `smartdoc` CLI commands on a database while managing it in the UI.
- **Database locks**: SQLite may lock briefly during operations. Wait for completion.

## Troubleshooting

### "Database not found" error
- Click **Refresh Databases** to re-scan
- Ensure the workspace has `data/registry.db` and `data/chroma_db/`

### Empty sources list
- The database may be empty (no indexed sources)
- Try indexing some documentation first

### Transfer fails
- Check that both source and destination databases exist
- Ensure no other processes are accessing the databases
- Check disk space

### Port already in use
- Change port: `smartdoc web-manager --port 8080`
- Or kill the process using port 7860

## Command Reference

```bash
# Basic usage
smartdoc web-manager

# Custom root directory
smartdoc web-manager --root /path/to/projects

# Custom port
smartdoc web-manager --port 8080

# Public share link
smartdoc web-manager --share

# Combine options
smartdoc web-manager --root ~/Code --port 8000
```

## Integration with Existing Commands

The web manager works alongside existing CLI commands:

```bash
# CLI: List sources in current workspace
smartdoc list-sources

# Web Manager: View sources across ALL workspaces
smartdoc web-manager
```

Both operate on the same database files, so changes are reflected immediately.


