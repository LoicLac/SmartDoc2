"""
Gradio-based web UI for multi-workspace database management.
"""

import gradio as gr
import logging
from typing import List, Tuple, Optional
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
            
            # Format for table display
            table_data = []
            for db in self.current_databases:
                table_data.append([
                    db['workspace_name'],
                    db['workspace_path'],
                    db['sources_count'],
                    db['documents_count'],
                    f"{db['size_mb']} MB",
                    db['status']
                ])
            
            message = f"✓ Found {len(self.current_databases)} database(s)"
            return table_data, message
        except Exception as e:
            logger.error(f"Error refreshing databases: {e}")
            return [], f"✗ Error: {str(e)}"
    
    def get_workspace_names(self) -> List[str]:
        """Get list of workspace names for dropdowns."""
        return [db['workspace_name'] for db in self.current_databases]
    
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
    
    def build_interface(self):
        """Build the Gradio interface."""
        
        with gr.Blocks(title="SmartDoc Database Manager", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🗂️ SmartDoc Database Manager")
            gr.Markdown(f"**Root Directory:** `{self.root_path}`")
            
            # Tab 1: Overview
            with gr.Tab("📊 Database Overview"):
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh Databases", variant="primary")
                
                overview_status = gr.Textbox(label="Status", interactive=False)
                
                databases_table = gr.Dataframe(
                    headers=["Workspace", "Path", "Sources", "Documents", "Size", "Status"],
                    label="Databases",
                    interactive=False,
                    wrap=True
                )
                
                # Auto-refresh on load
                demo.load(
                    fn=self.refresh_databases,
                    outputs=[databases_table, overview_status]
                )
                
                refresh_btn.click(
                    fn=self.refresh_databases,
                    outputs=[databases_table, overview_status]
                )
            
            # Tab 2: Browse & Delete
            with gr.Tab("🗃️ Browse & Delete"):
                gr.Markdown("### Select a workspace to view and manage its sources")
                
                workspace_selector = gr.Dropdown(
                    label="Select Workspace",
                    choices=[],
                    interactive=True
                )
                
                browse_status = gr.Textbox(label="Status", interactive=False)
                
                sources_table = gr.Dataframe(
                    headers=["Type", "Source Path", "Status", "Indexed", "Size"],
                    label="Sources",
                    interactive=False,
                    wrap=True
                )
                
                with gr.Row():
                    selected_rows = gr.Textbox(
                        label="Selected Row Indices (comma-separated, e.g., 0,1,2)",
                        placeholder="0,1,2"
                    )
                    delete_btn = gr.Button("🗑️ Delete Selected", variant="stop")
                
                # Update workspace dropdown when databases refresh
                refresh_btn.click(
                    fn=self.get_workspace_names,
                    outputs=workspace_selector
                )
                
                # Load sources when workspace selected
                workspace_selector.change(
                    fn=self.get_sources_for_workspace,
                    inputs=workspace_selector,
                    outputs=[sources_table, browse_status]
                )
                
                # Delete sources
                def delete_wrapper(ws, rows_str, table):
                    if rows_str:
                        selected = [int(r.strip()) for r in rows_str.split(',') if r.strip().isdigit()]
                        return self.delete_source(ws, selected, table)
                    return table, "No rows selected"
                
                delete_btn.click(
                    fn=delete_wrapper,
                    inputs=[workspace_selector, selected_rows, sources_table],
                    outputs=[sources_table, browse_status]
                )
            
            # Tab 3: Transfer
            with gr.Tab("🔄 Transfer Data"):
                gr.Markdown("### Transfer sources between workspaces")
                
                with gr.Row():
                    source_ws = gr.Dropdown(
                        label="Source Workspace",
                        choices=[],
                        interactive=True
                    )
                    dest_ws = gr.Dropdown(
                        label="Destination Workspace",
                        choices=[],
                        interactive=True
                    )
                
                transfer_sources_table = gr.Dataframe(
                    headers=["Type", "Source Path", "Status", "Indexed", "Size"],
                    label="Sources in Source Workspace",
                    interactive=False,
                    wrap=True
                )
                
                with gr.Row():
                    transfer_rows = gr.Textbox(
                        label="Selected Row Indices (comma-separated)",
                        placeholder="0,1,2"
                    )
                    move_checkbox = gr.Checkbox(label="Move (delete from source)", value=False)
                
                transfer_btn = gr.Button("➡️ Transfer", variant="primary")
                transfer_status = gr.Textbox(label="Status", interactive=False)
                
                # Update dropdowns
                refresh_btn.click(
                    fn=self.get_workspace_names,
                    outputs=[source_ws, dest_ws]
                )
                
                # Load sources when source workspace selected
                source_ws.change(
                    fn=self.get_sources_for_workspace,
                    inputs=source_ws,
                    outputs=[transfer_sources_table, transfer_status]
                )
                
                # Transfer
                def transfer_wrapper(src_ws, dst_ws, rows_str, table, move):
                    if rows_str:
                        selected = [int(r.strip()) for r in rows_str.split(',') if r.strip().isdigit()]
                        return self.transfer_sources(src_ws, dst_ws, selected, table, move)
                    return "No rows selected"
                
                transfer_btn.click(
                    fn=transfer_wrapper,
                    inputs=[source_ws, dest_ws, transfer_rows, transfer_sources_table, move_checkbox],
                    outputs=transfer_status
                )
            
            # Tab 4: Stats
            with gr.Tab("📈 Statistics"):
                gr.Markdown("### Detailed statistics per database")
                
                stats_workspace = gr.Dropdown(
                    label="Select Workspace",
                    choices=[],
                    interactive=True
                )
                
                stats_output = gr.Markdown()
                
                # Update dropdown
                refresh_btn.click(
                    fn=self.get_workspace_names,
                    outputs=stats_workspace
                )
                
                # Show stats
                stats_workspace.change(
                    fn=self.get_workspace_stats,
                    inputs=stats_workspace,
                    outputs=stats_output
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


