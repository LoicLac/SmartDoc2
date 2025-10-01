"""
Gradio-based web UI for multi-workspace database management.
"""

import gradio as gr  # pyright: ignore[reportMissingImports]
import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SmartDocUI:
    """Web UI for SmartDoc database management."""
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.manager = DatabaseManager(root_path)
        self.current_databases = []
    
    def refresh_databases(self) -> Tuple[List[List], str]:
        """Refresh and return database list."""
        try:
            self.current_databases = self.manager.discover_databases()
            
            # Format for new compact table: #, Name, Sources, Documents, Size, Status
            table_data = []
            for idx, db in enumerate(self.current_databases):
                status_emoji = "🟢" if db['status'] == 'healthy' else "🔴"
                table_data.append([
                    idx,  # Row index
                    db['workspace_name'],
                    db['sources_count'],
                    db['documents_count'],
                    db['size_mb'],
                    f"{status_emoji} {db['status']}"
                ])
            
            message = f"✓ Found {len(self.current_databases)} database(s)"
            return table_data, message
        except Exception as e:
            logger.error(f"Error refreshing databases: {e}")
            return [], f"✗ Error: {str(e)}"
    
    def get_workspace_names(self):
        """Get list of workspace names for dropdown (returns Dropdown update)."""
        names = [db['workspace_name'] for db in self.current_databases]
        return gr.Dropdown(choices=names)
    
    def get_workspace_names_dual(self):
        """Get workspace names for two dropdowns (returns same list twice)."""
        names = [db['workspace_name'] for db in self.current_databases]
        return gr.Dropdown(choices=names), gr.Dropdown(choices=names)
    
    def initialize_all(self):
        """Initialize everything on page load: refresh DB and populate all dropdowns."""
        # First refresh the database
        table_data, message = self.refresh_databases()
        
        # Then get workspace names
        names = [db['workspace_name'] for db in self.current_databases]
        
        # Return all outputs with proper Dropdown updates
        return (
            table_data, message,  # Overview tab
            gr.Dropdown(choices=names),  # Browse & Delete tab
            gr.Dropdown(choices=names), gr.Dropdown(choices=names),  # Transfer tab (source, dest)
            gr.Dropdown(choices=names)  # Statistics tab
        )
    
    def get_sources_for_workspace(self, workspace_name: str) -> Tuple[List[List], str]:
        """Get sources for a specific workspace."""
        try:
            if not workspace_name:
                return [], "Please select a workspace"
            
            # Find workspace path
            workspace_path = None
            for db in self.current_databases:
                if db['workspace_name'] == workspace_name:
                    workspace_path = db['workspace_path']
                    break
            
            if not workspace_path:
                return [], "Workspace not found"
            
            sources = self.manager.get_database_sources(workspace_path)
            
            # Format for table
            table_data = []
            for source in sources:
                size_str = f"{source['file_size'] / 1024 / 1024:.1f} MB" if source.get('file_size') else "N/A"
                table_data.append([
                    source['source_type'],
                    source['source_path'],
                    source['status'],
                    source['indexed_at'],
                    size_str
                ])
            
            return table_data, f"Found {len(sources)} source(s)"
        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return [], f"✗ Error: {str(e)}"
    
    def get_source_processing_logs(self, workspace_name: str, row_index: str) -> str:
        """Get processing logs for a selected source."""
        try:
            if not workspace_name:
                return "Please select a workspace"
            
            if not row_index or not row_index.strip().isdigit():
                return "Please enter a row index (e.g., 0 for first row)"
            
            row_idx = int(row_index.strip())
            
            # Find workspace path
            workspace_path = None
            for db in self.current_databases:
                if db['workspace_name'] == workspace_name:
                    workspace_path = db['workspace_path']
                    break
            
            if not workspace_path:
                return "Workspace not found"
            
            # Get sources
            sources = self.manager.get_database_sources(workspace_path)
            
            if row_idx < 0 or row_idx >= len(sources):
                return f"Invalid row index. Please enter a number between 0 and {len(sources)-1}"
            
            source = sources[row_idx]
            source_path = source['source_path']
            
            # Get logs
            logs = self.manager.get_source_logs(workspace_path, source_path)
            
            if not logs:
                return f"**No processing logs found for:** `{source_path}`\n\n" \
                       f"*Note: Logs are only available for sources indexed after the logging feature was added.*\n\n" \
                       f"To get logs, re-index this source:\n" \
                       f"1. Delete it using the delete button\n" \
                       f"2. Re-index it using the CLI: `smartdoc index-pdf \"{source_path}\"`"
            
            # Format logs as markdown
            output = f"## Processing Logs\n\n"
            output += f"**Source:** `{source_path}`  \n"
            output += f"**Type:** {source['source_type'].upper()}  \n"
            output += f"**Status:** {source['status']}  \n"
            output += f"**Indexed:** {source['indexed_at']}  \n\n"
            output += "---\n\n"
            
            # Display each log step
            for log in logs:
                # Status emoji
                if log['status'] == 'success':
                    emoji = "✅"
                elif log['status'] == 'failed':
                    emoji = "❌"
                elif log['status'] == 'warning':
                    emoji = "⚠️"
                elif log['status'] == 'skipped':
                    emoji = "⏭️"
                else:
                    emoji = "ℹ️"
                
                output += f"### {emoji} {log['step'].replace('_', ' ').title()}\n\n"
                output += f"**Status:** {log['status']}  \n"
                
                if log.get('message'):
                    output += f"**Message:** {log['message']}  \n"
                
                if log.get('timestamp'):
                    output += f"**Time:** {log['timestamp'].split('.')[0]}  \n"
                
                # Show details
                if log.get('details'):
                    details = log['details']
                    if isinstance(details, dict):
                        output += "\n**Details:**\n"
                        for key, value in details.items():
                            if key == 'errors' and value:
                                output += f"- **{key}:** {len(value)} errors\n"
                                for error in value[:3]:  # Show first 3 errors
                                    output += f"  - `{error}`\n"
                                if len(value) > 3:
                                    output += f"  - *... and {len(value)-3} more*\n"
                            elif not isinstance(value, (dict, list)):
                                output += f"- **{key}:** {value}\n"
                
                output += "\n"
            
            # Summary
            success_count = sum(1 for log in logs if log['status'] == 'success')
            failed_count = sum(1 for log in logs if log['status'] == 'failed')
            warning_count = sum(1 for log in logs if log['status'] == 'warning')
            
            output += "---\n\n"
            output += f"**Summary:** {success_count} successful, {failed_count} failed, {warning_count} warnings\n"
            
            return output
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return f"**Error:** {str(e)}"
    
    def delete_source(
        self,
        workspace_name: str,
        selected_rows: List[int],
        sources_table: List[List]
    ) -> Tuple[List[List], str]:
        """Delete selected sources."""
        try:
            if not workspace_name:
                return sources_table, "Please select a workspace"
            
            if not selected_rows:
                return sources_table, "Please select sources to delete"
            
            # Find workspace path
            workspace_path = None
            for db in self.current_databases:
                if db['workspace_name'] == workspace_name:
                    workspace_path = db['workspace_path']
                    break
            
            if not workspace_path:
                return sources_table, "Workspace not found"
            
            # Delete each selected source
            deleted_count = 0
            for row_idx in selected_rows:
                if row_idx < len(sources_table):
                    source_path = sources_table[row_idx][1]  # source_path is column 1
                    if self.manager.delete_source(workspace_path, source_path):
                        deleted_count += 1
            
            # Refresh sources list
            updated_table, _ = self.get_sources_for_workspace(workspace_name)
            return updated_table, f"✓ Deleted {deleted_count} source(s)"
            
        except Exception as e:
            logger.error(f"Error deleting sources: {e}")
            return sources_table, f"✗ Error: {str(e)}"
    
    def transfer_sources(
        self,
        source_workspace: str,
        dest_workspace: str,
        selected_rows: List[int],
        sources_table: List[List],
        move_mode: bool
    ) -> str:
        """Transfer sources between workspaces."""
        try:
            if not source_workspace or not dest_workspace:
                return "Please select both source and destination workspaces"
            
            if source_workspace == dest_workspace:
                return "Source and destination must be different"
            
            if not selected_rows:
                return "Please select sources to transfer"
            
            # Find workspace paths
            src_path = None
            dest_path = None
            for db in self.current_databases:
                if db['workspace_name'] == source_workspace:
                    src_path = db['workspace_path']
                if db['workspace_name'] == dest_workspace:
                    dest_path = db['workspace_path']
            
            if not src_path or not dest_path:
                return "Workspace not found"
            
            # Transfer each selected source
            transferred_count = 0
            for row_idx in selected_rows:
                if row_idx < len(sources_table):
                    source_path = sources_table[row_idx][1]  # source_path is column 1
                    if self.manager.transfer_source(src_path, dest_path, source_path, move=move_mode):
                        transferred_count += 1
            
            action = "Moved" if move_mode else "Copied"
            return f"✓ {action} {transferred_count} source(s) from {source_workspace} to {dest_workspace}"
            
        except Exception as e:
            logger.error(f"Error transferring sources: {e}")
            return f"✗ Error: {str(e)}"
    
    def get_workspace_stats(self, workspace_name: str) -> str:
        """Get detailed stats for a workspace."""
        try:
            if not workspace_name:
                return "Please select a workspace"
            
            # Find workspace path
            workspace_path = None
            for db in self.current_databases:
                if db['workspace_name'] == workspace_name:
                    workspace_path = db['workspace_path']
                    break
            
            if not workspace_path:
                return "Workspace not found"
            
            stats = self.manager.get_database_stats(workspace_path)
            
            # Format stats
            output = f"""## {stats['workspace_name']}

**Status:** {stats['status']}
**Total Sources:** {stats['total_sources']}
**Total Documents:** {stats['total_documents']}
**Storage Size:** {stats['size_mb']} MB

### Sources by Type
"""
            for source_type, count in stats['sources_by_type'].items():
                output += f"- {source_type}: {count}\n"
            
            return output
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return f"✗ Error: {str(e)}"
    
    def refresh_and_populate(self):
        """Refresh databases and populate dropdowns."""
        table_data, message = self.refresh_databases()
        names = [db['workspace_name'] for db in self.current_databases]
        return table_data, message, gr.Dropdown(choices=names), gr.Dropdown(choices=names)
    
    def load_database_assets(self, row_index: int):
        """Load assets for selected database."""
        try:
            logger.info(f"Loading database at row index: {row_index}")
            
            if row_index < 0 or row_index >= len(self.current_databases):
                logger.warning(f"Invalid row index: {row_index}, have {len(self.current_databases)} databases")
                return [], "**Assets in Selected Database** | *No database selected*", None, f"❌ Invalid index. Choose 0-{len(self.current_databases)-1}"
            
            db = self.current_databases[row_index]
            workspace_path = db['workspace_path']
            workspace_name = db['workspace_name']
            
            logger.info(f"Loading assets from: {workspace_path}")
            
            # Get enhanced assets
            assets = self.manager.get_enhanced_assets(workspace_path)
            
            # Format table data
            table_data = []
            for idx, asset in enumerate(assets):
                # Type icon
                type_icon = {"pdf": "📄", "github": "🐙", "web": "🌐"}.get(asset['source_type'], "📦")
                
                # Name (shortened)
                name = Path(asset['source_path']).name if '/' in asset['source_path'] else asset['source_path']
                
                # Size
                size_mb = f"{asset['file_size'] / 1024 / 1024:.1f} MB" if asset.get('file_size') else "N/A"
                
                # Text status
                text_status = f"✅ {asset['text_chunks']}" if asset['text_chunks'] > 0 else "❌ 0"
                
                # Vision status
                if asset['has_schematics']:
                    vision_status = f"🖼️ {asset['schematic_chunks']}"
                elif asset['vision_failed']:
                    vision_status = "❌ Failed"
                else:
                    vision_status = "⊘ N/A"
                
                # Overall status
                status_badge = asset['status']
                
                # Date
                date = asset['indexed_at'].split()[0] if asset.get('indexed_at') else "N/A"
                
                table_data.append([
                    idx,  # Row index
                    type_icon,
                    name,
                    size_mb,
                    text_status,
                    vision_status,
                    status_badge,
                    date
                ])
            
            db_info = f"**Assets in Selected Database** | {workspace_name} - {len(assets)} assets | {db['documents_count']} documents | {db['size_mb']} MB"
            
            logger.info(f"Successfully loaded {len(assets)} assets from {workspace_name}")
            return table_data, db_info, workspace_path, f"✓ Loaded {len(assets)} assets from {workspace_name}"
            
        except Exception as e:
            logger.error(f"Error loading assets: {e}", exc_info=True)
            return [], "**Assets in Selected Database** | *Error loading database*", None, f"❌ Error: {str(e)}"
    
    def delete_assets(self, workspace_path: str, selected_rows: str):
        """Delete selected assets."""
        try:
            if not workspace_path:
                return [], "❌ No database selected"
            
            if not selected_rows or not selected_rows.strip():
                return [], "❌ No assets selected"
            
            # Parse row indices
            try:
                indices = [int(r.strip()) for r in selected_rows.split(',') if r.strip().isdigit()]
            except:
                return [], "❌ Invalid row indices"
            
            if not indices:
                return [], "❌ No valid indices"
            
            # Get assets
            assets = self.manager.get_enhanced_assets(workspace_path)
            
            # Delete each selected
            deleted_count = 0
            for idx in indices:
                if 0 <= idx < len(assets):
                    source_path = assets[idx]['source_path']
                    if self.manager.delete_source(workspace_path, source_path):
                        deleted_count += 1
            
            # Reload assets
            updated_assets = self.manager.get_enhanced_assets(workspace_path)
            table_data = self._format_assets_table(updated_assets)
            
            return table_data, f"✓ Deleted {deleted_count} asset(s)"
            
        except Exception as e:
            logger.error(f"Error deleting assets: {e}")
            return [], f"❌ Error: {str(e)}"
    
    def view_asset_logs(self, workspace_path: str, selected_row: str):
        """View processing logs for selected asset."""
        try:
            if not workspace_path:
                return "", "❌ No database selected"
            
            if not selected_row or not selected_row.strip().isdigit():
                return "", "❌ Enter a single row index"
            
            row_idx = int(selected_row.strip())
            assets = self.manager.get_enhanced_assets(workspace_path)
            
            if row_idx < 0 or row_idx >= len(assets):
                return "", f"❌ Invalid index. Choose 0-{len(assets)-1}"
            
            asset = assets[row_idx]
            source_path = asset['source_path']
            
            # Use existing method
            logs_md = self.get_source_processing_logs(workspace_path, source_path)
            
            return logs_md, "✓ Logs displayed below"
            
        except Exception as e:
            logger.error(f"Error viewing logs: {e}")
            return "", f"❌ Error: {str(e)}"
    
    def load_transfer_assets(self, workspace_name: str):
        """Load assets for transfer view."""
        try:
            if not workspace_name:
                return [], "*Select a database*"
            
            # Find workspace path
            workspace_path = None
            for db in self.current_databases:
                if db['workspace_name'] == workspace_name:
                    workspace_path = db['workspace_path']
                    break
            
            if not workspace_path:
                return [], "*Database not found*"
            
            assets = self.manager.get_enhanced_assets(workspace_path)
            
            # Simplified table for transfer
            table_data = []
            for idx, asset in enumerate(assets):
                type_icon = {"pdf": "📄", "github": "🐙", "web": "🌐"}.get(asset['source_type'], "📦")
                name = Path(asset['source_path']).name if '/' in asset['source_path'] else asset['source_path']
                size_mb = f"{asset['file_size'] / 1024 / 1024:.1f} MB" if asset.get('file_size') else "N/A"
                
                table_data.append([idx, type_icon, name, size_mb])
            
            info = f"*{len(assets)} assets, {sum(a['text_chunks'] for a in assets)} chunks*"
            return table_data, info
            
        except Exception as e:
            logger.error(f"Error loading transfer assets: {e}")
            return [], f"*Error: {str(e)}*"
    
    def copy_assets(self, source_ws: str, dest_ws: str, selected_rows: str):
        """Copy assets from source to destination."""
        return self._transfer_assets(source_ws, dest_ws, selected_rows, move=False)
    
    def move_assets(self, source_ws: str, dest_ws: str, selected_rows: str):
        """Move assets from source to destination."""
        result = self._transfer_assets(source_ws, dest_ws, selected_rows, move=True)
        # Return updated tables for both source and dest
        status, dest_table, dest_info = result
        
        # Reload source table too
        source_table, source_info = self.load_transfer_assets(source_ws)
        
        return status, source_table, dest_table, source_info, dest_info
    
    def _transfer_assets(self, source_ws: str, dest_ws: str, selected_rows: str, move: bool):
        """Internal method to transfer assets."""
        try:
            if not source_ws or not dest_ws:
                return "❌ Select both source and destination", [], "*Error*"
            
            if source_ws == dest_ws:
                return "❌ Source and destination must be different", [], "*Error*"
            
            if not selected_rows or not selected_rows.strip():
                return "❌ No assets selected", [], "*Error*"
            
            # Parse indices
            try:
                indices = [int(r.strip()) for r in selected_rows.split(',') if r.strip().isdigit()]
            except:
                return "❌ Invalid row indices", [], "*Error*"
            
            # Find workspace paths
            src_path = None
            dest_path = None
            for db in self.current_databases:
                if db['workspace_name'] == source_ws:
                    src_path = db['workspace_path']
                if db['workspace_name'] == dest_ws:
                    dest_path = db['workspace_path']
            
            if not src_path or not dest_path:
                return "❌ Workspace not found", [], "*Error*"
            
            # Get source assets
            assets = self.manager.get_enhanced_assets(src_path)
            
            # Transfer each
            transferred = 0
            for idx in indices:
                if 0 <= idx < len(assets):
                    source_path = assets[idx]['source_path']
                    if self.manager.transfer_source(src_path, dest_path, source_path, move=move):
                        transferred += 1
            
            # Reload destination
            dest_table, dest_info = self.load_transfer_assets(dest_ws)
            
            action = "Moved" if move else "Copied"
            return f"✓ {action} {transferred} asset(s)", dest_table, dest_info
            
        except Exception as e:
            logger.error(f"Error transferring assets: {e}")
            return f"❌ Error: {str(e)}", [], "*Error*"
    
    def _format_assets_table(self, assets: List[Dict]):
        """Helper to format assets for table display."""
        table_data = []
        for idx, asset in enumerate(assets):
            type_icon = {"pdf": "📄", "github": "🐙", "web": "🌐"}.get(asset['source_type'], "📦")
            name = Path(asset['source_path']).name if '/' in asset['source_path'] else asset['source_path']
            size_mb = f"{asset['file_size'] / 1024 / 1024:.1f} MB" if asset.get('file_size') else "N/A"
            text_status = f"✅ {asset['text_chunks']}" if asset['text_chunks'] > 0 else "❌ 0"
            
            if asset['has_schematics']:
                vision_status = f"🖼️ {asset['schematic_chunks']}"
            elif asset['vision_failed']:
                vision_status = "❌ Failed"
            else:
                vision_status = "⊘ N/A"
            
            status_badge = asset['status']
            date = asset['indexed_at'].split()[0] if asset.get('indexed_at') else "N/A"
            
            table_data.append([idx, type_icon, name, size_mb, text_status, vision_status, status_badge, date])
        
        return table_data
    
    def get_source_processing_logs(self, workspace_path: str, source_path: str) -> str:
        """Get processing logs for a source (reuse existing method but with workspace_path)."""
        try:
            logs = self.manager.get_source_logs(workspace_path, source_path)
            
            if not logs:
                return f"**No processing logs found**\n\n*Logs are only available for sources indexed after this feature was added.*"
            
            # Format logs as markdown (reusing similar logic from before)
            output = f"## Processing Logs\n\n"
            output += f"**Source:** `{source_path}`\n\n---\n\n"
            
            for log in logs:
                emoji = {"success": "✅", "failed": "❌", "warning": "⚠️", "skipped": "⏭️"}.get(log['status'], "ℹ️")
                output += f"### {emoji} {log['step'].replace('_', ' ').title()}\n\n"
                output += f"**Status:** {log['status']}  \n"
                
                if log.get('message'):
                    output += f"**Message:** {log['message']}  \n"
                
                if log.get('details'):
                    details = log['details']
                    if isinstance(details, dict):
                        output += "\n**Details:**\n"
                        for k, v in details.items():
                            if k == 'errors' and v:
                                output += f"- **{k}:** {len(v)} errors\n"
                                for error in v[:3]:
                                    output += f"  - `{error}`\n"
                            elif not isinstance(v, (dict, list)):
                                output += f"- **{k}:** {v}\n"
                
                output += "\n"
            
            return output
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return f"**Error:** {str(e)}"
    
    def build_interface(self):
        """Build the Gradio interface with modern design."""
        
        with gr.Blocks(title="SmartDoc Database Manager", theme=gr.themes.Soft(), css="""
            .database-row {cursor: pointer; transition: background 0.2s;}
            .database-row:hover {background: #f0f0f0;}
            .status-badge {padding: 2px 8px; border-radius: 12px; font-size: 0.9em;}
            .compact-selector input {width: 60px !important; min-width: 60px !important;}
            .dataframe {margin-top: 0px !important; margin-bottom: 0px !important;}
            .markdown {margin-top: 8px !important; margin-bottom: 8px !important; padding: 4px 0 !important;}
        """) as demo:
            with gr.Row():
                gr.Markdown(f"# 🗂️ SmartDoc Database Manager  &nbsp;&nbsp;&nbsp; **Root:** `{self.root_path}`")
                refresh_btn = gr.Button("🔄 Refresh", variant="primary", scale=0)
            
            # Store selected database path in state
            selected_db_state = gr.State(value=None)
            
            # Tab 1: Main Dashboard (Master-Detail)
            with gr.Tab("📊 Dashboard"):
                # Compact database selector
                with gr.Row():
                    gr.Markdown("### Available Databases  &nbsp;&nbsp;|&nbsp;&nbsp;  Select Row:")
                    db_selector = gr.Number(
                        label="",
                        value=0,
                        minimum=0,
                        step=1,
                        scale=0,
                        container=False,
                        elem_classes="compact-selector"
                    )
                    load_db_btn = gr.Button("📂 Load Database", variant="primary", scale=0)
                
                # Master list: All databases
                databases_table = gr.Dataframe(
                    headers=["#", "Name", "Sources", "Documents", "Size (MB)", "Status"],
                    label="",
                    interactive=False,
                    wrap=True,
                    height=150
                )
                
                overview_status = gr.Textbox(label="Status", interactive=False, visible=False)
                
                # Compact separator with database info
                selected_db_name = gr.Markdown("**Assets in Selected Database** | *No database selected*")
                
                # Detail view: Assets in selected database
                assets_table = gr.Dataframe(
                    headers=["#", "Type", "Name", "Size", "Text", "Vision", "Status", "Date"],
                    label="",
                    interactive=False,
                    wrap=True,
                    height=350
                )
                
                # Actions
                with gr.Row():
                    selected_assets = gr.Textbox(
                        label="Selected Rows",
                        placeholder="0,1,2",
                        scale=1
                    )
                    delete_btn = gr.Button("🗑️ Delete", variant="stop", scale=0)
                    view_logs_btn = gr.Button("📋 Logs", variant="secondary", scale=0)
                
                action_status = gr.Textbox(label="Status", interactive=False, container=False)
                logs_output = gr.Markdown(label="Processing Logs", value="", visible=True)
            
            # Tab 2: Transfer & Copy (Split View)
            with gr.Tab("🔄 Transfer & Copy"):
                with gr.Row(equal_height=True):
                    # Left column: Source
                    with gr.Column(scale=1):
                        gr.Markdown("**📤 SOURCE**")
                        source_db_dropdown = gr.Dropdown(
                            label="",
                            choices=[],
                            interactive=True,
                            container=False
                        )
                        
                        source_assets_table = gr.Dataframe(
                            headers=["#", "Type", "Name", "Size"],
                            label="",
                            interactive=False,
                            wrap=True,
                            height=400
                        )
                        
                        source_selection = gr.Textbox(
                            label="Select Rows",
                            placeholder="0,1,2"
                        )
                        
                        source_info = gr.Markdown("*Select source database*")
                    
                    # Center: Actions
                    with gr.Column(scale=0, min_width=120):
                        gr.Markdown("<br><br>")
                        copy_btn = gr.Button("📋 Copy →", variant="primary", size="lg")
                        move_btn = gr.Button("➡️ Move →", variant="stop", size="lg")
                        gr.Markdown("<small>Copy: Keep<br>Move: Delete</small>")
                    
                    # Right column: Destination
                    with gr.Column(scale=1):
                        gr.Markdown("**📥 DESTINATION**")
                        dest_db_dropdown = gr.Dropdown(
                            label="",
                            choices=[],
                            interactive=True,
                            container=False
                        )
                
                        dest_assets_table = gr.Dataframe(
                            headers=["#", "Type", "Name", "Size"],
                            label="",
                            interactive=False,
                            wrap=True,
                            height=400
                        )
                        
                        dest_info = gr.Markdown("*Select destination database*")
                
                transfer_status = gr.Textbox(label="Status", interactive=False, container=False)
            
            # Event Handlers
            
            # Refresh button
            refresh_btn.click(
                fn=self.refresh_and_populate,
                outputs=[databases_table, overview_status, source_db_dropdown, dest_db_dropdown]
            )
            
            # Tab 1: Dashboard - Load database assets
            load_db_btn.click(
                fn=self.load_database_assets,
                inputs=[db_selector],
                outputs=[assets_table, selected_db_name, selected_db_state, action_status],
                show_progress=True
            )
            
            # Tab 1: Dashboard - Delete assets
            delete_btn.click(
                fn=self.delete_assets,
                inputs=[selected_db_state, selected_assets],
                outputs=[assets_table, action_status],
                show_progress=True
            )
            
            # Tab 1: Dashboard - View logs
            view_logs_btn.click(
                fn=self.view_asset_logs,
                inputs=[selected_db_state, selected_assets],
                outputs=[logs_output, action_status]
            )
            
            # Tab 2: Transfer - Load source assets
            source_db_dropdown.change(
                fn=self.load_transfer_assets,
                inputs=[source_db_dropdown],
                outputs=[source_assets_table, source_info]
            )
            
            # Tab 2: Transfer - Load dest assets
            dest_db_dropdown.change(
                fn=self.load_transfer_assets,
                inputs=[dest_db_dropdown],
                outputs=[dest_assets_table, dest_info]
            )
            
            # Tab 2: Transfer - Copy button
            copy_btn.click(
                fn=self.copy_assets,
                inputs=[source_db_dropdown, dest_db_dropdown, source_selection],
                outputs=[transfer_status, dest_assets_table, dest_info]
            )
            
            # Tab 2: Transfer - Move button
            move_btn.click(
                fn=self.move_assets,
                inputs=[source_db_dropdown, dest_db_dropdown, source_selection],
                outputs=[transfer_status, source_assets_table, dest_assets_table, source_info, dest_info]
            )
            
            # Initialize on load
            demo.load(
                fn=self.refresh_and_populate,
                outputs=[databases_table, overview_status, source_db_dropdown, dest_db_dropdown]
            )
        
        return demo


def launch_ui(root_path: str, share: bool = False, server_port: int = 7860):
    """
    Launch the Gradio UI.
    
    Args:
        root_path: Root directory to scan for databases
        share: Create public share link
        server_port: Port to run server on
    """
    ui = SmartDocUI(root_path)
    demo = ui.build_interface()
    demo.launch(share=share, server_port=server_port, show_error=True)


