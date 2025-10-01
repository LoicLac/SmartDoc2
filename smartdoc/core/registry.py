"""
SQLite-based registry for tracking indexed sources and schematic cache.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from ..config import REGISTRY_DB


class Registry:
    """Manages the SQLite registry for tracking sources and schematic analysis cache."""
    
    def __init__(self, db_path: str = REGISTRY_DB):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sources table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_path TEXT NOT NULL UNIQUE,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    status TEXT DEFAULT 'pending',
                    metadata TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Schematic cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schematic_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    image_hash TEXT NOT NULL,
                    page_number INTEGER,
                    last_query TEXT,
                    vision_result TEXT,
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE,
                    UNIQUE(image_hash, last_query)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_type ON sources(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_path ON sources(source_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_hash ON schematic_cache(image_hash)")
    
    def add_source(
        self, 
        source_type: str, 
        source_path: str, 
        file_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a new source to the registry.
        
        Returns:
            Source ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sources 
                (source_type, source_path, file_size, metadata, status, last_updated)
                VALUES (?, ?, ?, ?, 'processing', CURRENT_TIMESTAMP)
            """, (source_type, source_path, file_size, json.dumps(metadata or {})))
            return cursor.lastrowid
    
    def get_source(self, source_path: str) -> Optional[Dict[str, Any]]:
        """Get source information by path."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sources WHERE source_path = ?", (source_path,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['metadata'] = json.loads(result['metadata']) if result['metadata'] else {}
                return result
            return None
    
    def get_source_by_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Get source information by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['metadata'] = json.loads(result['metadata']) if result['metadata'] else {}
                return result
            return None
    
    def update_status(
        self, 
        source_path: str, 
        status: str, 
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update source status and optionally metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if metadata:
                cursor.execute("""
                    UPDATE sources 
                    SET status = ?, metadata = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE source_path = ?
                """, (status, json.dumps(metadata), source_path))
            else:
                cursor.execute("""
                    UPDATE sources 
                    SET status = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE source_path = ?
                """, (status, source_path))
    
    def list_sources(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sources, optionally filtered by type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if source_type:
                cursor.execute("SELECT * FROM sources WHERE source_type = ? ORDER BY indexed_at DESC", (source_type,))
            else:
                cursor.execute("SELECT * FROM sources ORDER BY indexed_at DESC")
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['metadata'] = json.loads(result['metadata']) if result['metadata'] else {}
                results.append(result)
            return results
    
    def delete_source(self, source_path: str):
        """Delete a source from the registry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sources WHERE source_path = ?", (source_path,))
    
    # Schematic cache methods
    
    def cache_vision_result(
        self,
        source_id: int,
        image_hash: str,
        query_context: str,
        vision_result: str,
        page_number: Optional[int] = None
    ):
        """Cache a vision analysis result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO schematic_cache
                (source_id, image_hash, page_number, last_query, vision_result, analyzed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (source_id, image_hash, page_number, query_context, vision_result))
    
    def get_schematic_cache(
        self, 
        image_hash: str, 
        query_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached vision result for a schematic.
        If query_context is provided, tries to find exact match first, then any result.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if query_context:
                # Try exact match first
                cursor.execute("""
                    SELECT * FROM schematic_cache 
                    WHERE image_hash = ? AND last_query = ?
                    ORDER BY analyzed_at DESC LIMIT 1
                """, (image_hash, query_context))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            
            # Fall back to any cached result for this image
            cursor.execute("""
                SELECT * FROM schematic_cache 
                WHERE image_hash = ?
                ORDER BY analyzed_at DESC LIMIT 1
            """, (image_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_source_schematics(self, source_id: int) -> List[Dict[str, Any]]:
        """Get all schematic cache entries for a source."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM schematic_cache 
                WHERE source_id = ?
                ORDER BY page_number, analyzed_at DESC
            """, (source_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Source counts by type
            cursor.execute("""
                SELECT source_type, COUNT(*) as count, SUM(file_size) as total_size
                FROM sources
                GROUP BY source_type
            """)
            sources_by_type = [dict(row) for row in cursor.fetchall()]
            
            # Total sources
            cursor.execute("SELECT COUNT(*) as total FROM sources")
            total_sources = cursor.fetchone()['total']
            
            # Cached schematics
            cursor.execute("SELECT COUNT(*) as total FROM schematic_cache")
            total_schematics = cursor.fetchone()['total']
            
            return {
                'total_sources': total_sources,
                'sources_by_type': sources_by_type,
                'cached_schematics': total_schematics
            }

