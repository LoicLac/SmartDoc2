"""
Database discovery and management across multiple workspaces.
"""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import shutil

import chromadb  # pyright: ignore[reportMissingImports]
from chromadb.config import Settings  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages multiple SmartDoc databases across workspaces."""
    
    def __init__(self, root_path: str):
        """
        Initialize the database manager.
        
        Args:
            root_path: Root directory to scan for SmartDoc databases (e.g., ~/Code)
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.databases: Dict[str, Dict[str, Any]] = {}
    
    def discover_databases(self) -> List[Dict[str, Any]]:
        """
        Scan root directory for SmartDoc databases.
        
        Returns:
            List of database info dicts
        """
        self.databases = {}
        logger.info(f"Scanning for databases in: {self.root_path}")
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            root_path = Path(root)
            
            # Look for data/registry.db pattern
            if root_path.name == 'data' and (root_path / 'registry.db').exists():
                chroma_path = root_path / 'chroma_db'
                if chroma_path.exists():
                    workspace_path = root_path.parent
                    workspace_name = workspace_path.name
                    
                    db_info = self._get_database_info(workspace_path, workspace_name)
                    self.databases[str(workspace_path)] = db_info
        
        logger.info(f"Found {len(self.databases)} SmartDoc databases")
        return list(self.databases.values())
    
    def _get_database_info(self, workspace_path: Path, workspace_name: str) -> Dict[str, Any]:
        """Get detailed information about a database."""
        data_path = workspace_path / 'data'
        registry_path = data_path / 'registry.db'
        chroma_path = data_path / 'chroma_db'
        
        info = {
            'workspace_name': workspace_name,
            'workspace_path': str(workspace_path),
            'data_path': str(data_path),
            'registry_path': str(registry_path),
            'chroma_path': str(chroma_path),
            'sources_count': 0,
            'documents_count': 0,
            'size_mb': 0,
            'status': 'unknown',
            'sources': []
        }
        
        try:
            # Get registry info
            conn = sqlite3.connect(registry_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM sources")
            info['sources_count'] = cursor.fetchone()['count']
            
            # Get all sources
            cursor.execute("SELECT * FROM sources ORDER BY indexed_at DESC")
            sources = []
            for row in cursor.fetchall():
                sources.append({
                    'id': row['id'],
                    'source_type': row['source_type'],
                    'source_path': row['source_path'],
                    'indexed_at': row['indexed_at'],
                    'status': row['status'],
                    'file_size': row['file_size']
                })
            info['sources'] = sources
            
            conn.close()
            
            # Get ChromaDB info
            try:
                client = chromadb.PersistentClient(
                    path=str(chroma_path),
                    settings=Settings(anonymized_telemetry=False, allow_reset=False)
                )
                collection = client.get_collection(name="smartdoc_workspace")
                info['documents_count'] = collection.count()
            except Exception as e:
                logger.warning(f"Could not read ChromaDB for {workspace_name}: {e}")
                info['documents_count'] = 0
            
            # Calculate size
            total_size = 0
            for root, dirs, files in os.walk(data_path):
                for f in files:
                    fp = Path(root) / f
                    if fp.exists():
                        total_size += fp.stat().st_size
            info['size_mb'] = round(total_size / (1024 * 1024), 2)
            
            info['status'] = 'healthy'
            
        except Exception as e:
            logger.error(f"Error reading database {workspace_name}: {e}")
            info['status'] = f'error: {str(e)}'
        
        return info
    
    def get_database_sources(self, workspace_path: str) -> List[Dict[str, Any]]:
        """Get all sources from a specific database."""
        if workspace_path not in self.databases:
            self.discover_databases()
        
        if workspace_path in self.databases:
            return self.databases[workspace_path]['sources']
        return []
    
    def get_enhanced_assets(self, workspace_path: str) -> List[Dict[str, Any]]:
        """Get enhanced asset information with processing status."""
        try:
            db_info = self.databases.get(workspace_path)
            if not db_info:
                return []
            
            registry_path = db_info['registry_path']
            conn = sqlite3.connect(registry_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get sources with metadata
            cursor.execute("""
                SELECT s.id, s.source_type, s.source_path, s.indexed_at, 
                       s.status, s.file_size, s.metadata
                FROM sources s
                ORDER BY s.indexed_at DESC
            """)
            
            assets = []
            for row in cursor.fetchall():
                asset = dict(row)
                
                # Parse metadata
                metadata = {}
                if asset.get('metadata'):
                    import json
                    try:
                        metadata = json.loads(asset['metadata'])
                    except:
                        pass
                
                # Get processing stats from logs
                cursor.execute("""
                    SELECT step, status, details
                    FROM processing_logs
                    WHERE source_id = ?
                    ORDER BY timestamp DESC
                """, (asset['id'],))
                
                logs = cursor.fetchall()
                
                # Analyze logs for status badges
                text_chunks = metadata.get('text_chunks', 0)
                schematic_chunks = metadata.get('schematic_chunks', 0)
                
                vision_success = False
                vision_failed = False
                has_schematics = schematic_chunks > 0
                
                for log in logs:
                    if log['step'] == 'schematic_analysis':
                        if log['status'] == 'success':
                            vision_success = True
                        elif log['status'] in ['failed', 'warning']:
                            if log['details']:
                                import json
                                try:
                                    details = json.loads(log['details'])
                                    if details.get('analysis_failed', 0) > 0:
                                        vision_failed = True
                                except:
                                    pass
                
                asset['text_chunks'] = text_chunks
                asset['schematic_chunks'] = schematic_chunks
                asset['vision_success'] = vision_success
                asset['vision_failed'] = vision_failed
                asset['has_schematics'] = has_schematics
                assets.append(asset)
            
            conn.close()
            return assets
            
        except Exception as e:
            logger.error(f"Error getting enhanced assets: {e}")
            return []
    
    def get_database_summary(self, workspace_path: str) -> Dict[str, Any]:
        """Get compact database summary for list view."""
        if workspace_path not in self.databases:
            return {}
        
        db_info = self.databases[workspace_path]
        return {
            'name': db_info['workspace_name'],
            'path': workspace_path,
            'sources': db_info['sources_count'],
            'documents': db_info['documents_count'],
            'size_mb': db_info['size_mb'],
            'status': db_info['status']
        }
    
    def delete_source(self, workspace_path: str, source_path: str) -> bool:
        """
        Delete a source from a database.
        
        Args:
            workspace_path: Path to workspace
            source_path: Source path to delete
            
        Returns:
            True if successful
        """
        try:
            db_info = self.databases.get(workspace_path)
            if not db_info:
                raise ValueError(f"Database not found: {workspace_path}")
            
            registry_path = db_info['registry_path']
            chroma_path = db_info['chroma_path']
            
            # Delete from registry
            conn = sqlite3.connect(registry_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sources WHERE source_path = ?", (source_path,))
            conn.commit()
            conn.close()
            
            # Delete from ChromaDB
            client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=False)
            )
            collection = client.get_collection(name="smartdoc_workspace")
            
            # Get all documents from this source
            results = collection.get(where={"source": source_path})
            if results['ids']:
                collection.delete(ids=results['ids'])
            
            logger.info(f"Deleted source {source_path} from {workspace_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete source: {e}")
            return False
    
    def transfer_source(
        self,
        source_workspace: str,
        dest_workspace: str,
        source_path: str,
        move: bool = False
    ) -> bool:
        """
        Transfer a source from one database to another.
        
        Args:
            source_workspace: Source workspace path
            dest_workspace: Destination workspace path
            source_path: Source path to transfer
            move: If True, delete from source after copying
            
        Returns:
            True if successful
        """
        try:
            src_db = self.databases.get(source_workspace)
            dest_db = self.databases.get(dest_workspace)
            
            if not src_db or not dest_db:
                raise ValueError("Source or destination database not found")
            
            # Get source info from source registry
            src_conn = sqlite3.connect(src_db['registry_path'])
            src_conn.row_factory = sqlite3.Row
            src_cursor = src_conn.cursor()
            src_cursor.execute("SELECT * FROM sources WHERE source_path = ?", (source_path,))
            source_row = src_cursor.fetchone()
            
            if not source_row:
                raise ValueError(f"Source not found: {source_path}")
            
            # Get all documents from source ChromaDB
            src_client = chromadb.PersistentClient(
                path=src_db['chroma_path'],
                settings=Settings(anonymized_telemetry=False, allow_reset=False)
            )
            src_collection = src_client.get_collection(name="smartdoc_workspace")
            results = src_collection.get(where={"source": source_path})
            
            if not results['ids']:
                logger.warning(f"No documents found for source: {source_path}")
                src_conn.close()
                return False
            
            # Add to destination registry
            dest_conn = sqlite3.connect(dest_db['registry_path'])
            dest_cursor = dest_conn.cursor()
            dest_cursor.execute("""
                INSERT OR REPLACE INTO sources 
                (source_type, source_path, file_size, metadata, status, indexed_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source_row['source_type'],
                source_row['source_path'],
                source_row['file_size'],
                source_row['metadata'],
                source_row['status'],
                source_row['indexed_at'],
                source_row['last_updated']
            ))
            dest_conn.commit()
            
            # Copy schematic cache if exists
            src_cursor.execute("SELECT * FROM schematic_cache WHERE source_id = ?", (source_row['id'],))
            schematics = src_cursor.fetchall()
            
            if schematics:
                # Get new source_id from destination
                dest_cursor.execute("SELECT id FROM sources WHERE source_path = ?", (source_path,))
                new_source_id = dest_cursor.fetchone()[0]
                
                for schematic in schematics:
                    dest_cursor.execute("""
                        INSERT OR REPLACE INTO schematic_cache
                        (source_id, image_hash, page_number, last_query, vision_result, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        new_source_id,
                        schematic['image_hash'],
                        schematic['page_number'],
                        schematic['last_query'],
                        schematic['vision_result'],
                        schematic['analyzed_at']
                    ))
                dest_conn.commit()
            
            # Add documents to destination ChromaDB
            dest_client = chromadb.PersistentClient(
                path=dest_db['chroma_path'],
                settings=Settings(anonymized_telemetry=False, allow_reset=False)
            )
            dest_collection = dest_client.get_collection(name="smartdoc_workspace")
            
            # ChromaDB add requires documents, metadatas, ids
            dest_collection.add(
                documents=results['documents'],
                metadatas=results['metadatas'],
                ids=results['ids']
            )
            
            logger.info(f"Transferred {len(results['ids'])} documents from {source_workspace} to {dest_workspace}")
            
            # If move, delete from source
            if move:
                src_collection.delete(ids=results['ids'])
                src_cursor.execute("DELETE FROM sources WHERE source_path = ?", (source_path,))
                src_cursor.execute("DELETE FROM schematic_cache WHERE source_id = ?", (source_row['id'],))
                src_conn.commit()
                logger.info(f"Deleted source from {source_workspace}")
            
            src_conn.close()
            dest_conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to transfer source: {e}")
            return False
    
    def get_database_stats(self, workspace_path: str) -> Dict[str, Any]:
        """Get detailed stats for a specific database."""
        if workspace_path not in self.databases:
            self.discover_databases()
        
        db_info = self.databases.get(workspace_path)
        if not db_info:
            return {}
        
        stats = {
            'workspace_name': db_info['workspace_name'],
            'total_sources': db_info['sources_count'],
            'total_documents': db_info['documents_count'],
            'size_mb': db_info['size_mb'],
            'status': db_info['status'],
            'sources_by_type': {}
        }
        
        # Count by type
        for source in db_info['sources']:
            source_type = source['source_type']
            stats['sources_by_type'][source_type] = stats['sources_by_type'].get(source_type, 0) + 1
        
        return stats
    
    def get_source_logs(self, workspace_path: str, source_path: str) -> List[Dict[str, Any]]:
        """Get processing logs for a specific source."""
        try:
            db_info = self.databases.get(workspace_path)
            if not db_info:
                return []
            
            registry_path = db_info['registry_path']
            
            # Get source ID
            conn = sqlite3.connect(registry_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM sources WHERE source_path = ?", (source_path,))
            source_row = cursor.fetchone()
            
            if not source_row:
                conn.close()
                return []
            
            source_id = source_row['id']
            
            # Get processing logs
            cursor.execute("""
                SELECT step, status, message, details, timestamp
                FROM processing_logs
                WHERE source_id = ?
                ORDER BY timestamp ASC
            """, (source_id,))
            
            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                if log.get('details'):
                    import json
                    try:
                        log['details'] = json.loads(log['details'])
                    except:
                        pass
                logs.append(log)
            
            conn.close()
            return logs
            
        except Exception as e:
            logger.error(f"Error getting source logs: {e}")
            return []


