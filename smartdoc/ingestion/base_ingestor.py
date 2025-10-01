"""
Abstract base class for all data ingestors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import hashlib
import logging
from pathlib import Path

from ..core.registry import Registry
from ..core.chroma_client import ChromaManager

logger = logging.getLogger(__name__)


class BaseIngestor(ABC):
    """Abstract base class for data ingestion."""
    
    def __init__(self, registry: Registry, chroma_manager: ChromaManager):
        self.registry = registry
        self.chroma = chroma_manager
    
    @abstractmethod
    def ingest(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Ingest data from a source.
        
        Args:
            source: Source path, URL, or identifier
            **kwargs: Additional source-specific parameters
        
        Returns:
            Dictionary with ingestion results
        """
        pass
    
    @abstractmethod
    def validate_source(self, source: str) -> bool:
        """
        Validate that the source is accessible and processable.
        
        Args:
            source: Source to validate
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def generate_chunk_id(self, source: str, chunk_index: int, content_hash: Optional[str] = None) -> str:
        """
        Generate a unique ID for a document chunk.
        
        Args:
            source: Source identifier
            chunk_index: Index of the chunk
            content_hash: Optional content hash for uniqueness
        
        Returns:
            Unique chunk ID
        """
        if content_hash:
            return f"{self._sanitize_source(source)}_chunk_{chunk_index}_{content_hash[:8]}"
        return f"{self._sanitize_source(source)}_chunk_{chunk_index}"
    
    def hash_content(self, content: str) -> str:
        """
        Generate MD5 hash of content.
        
        Args:
            content: Content to hash
        
        Returns:
            MD5 hash string
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def hash_image(self, image_bytes: bytes) -> str:
        """
        Generate MD5 hash of image bytes.
        
        Args:
            image_bytes: Image bytes
        
        Returns:
            MD5 hash string
        """
        return hashlib.md5(image_bytes).hexdigest()
    
    def _sanitize_source(self, source: str) -> str:
        """Sanitize source string for use in IDs."""
        # Replace special characters with underscores
        sanitized = source.replace('/', '_').replace(':', '_').replace('.', '_')
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized
    
    def check_file_size(self, file_path: Path, warning_size: int, max_size: int) -> bool:
        """
        Check file size and warn if necessary.
        
        Args:
            file_path: Path to file
            warning_size: Size in bytes to trigger warning
            max_size: Maximum size in bytes (prompt user)
        
        Returns:
            True if should proceed, False if should skip
        """
        size = file_path.stat().st_size
        size_mb = size / (1024 * 1024)
        
        if size > max_size:
            response = input(f"⚠️  {file_path.name} is {size_mb:.1f}MB. Process anyway? (y/n): ")
            return response.lower() == 'y'
        elif size > warning_size:
            logger.warning(f"⚠️  Large file: {file_path.name} ({size_mb:.1f}MB)")
        
        return True
    
    def chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Chunk text with overlap.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
        
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary if possible
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.7:  # Only break if we're past 70% of chunk
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    def prepare_metadata(self, base_metadata: Dict[str, Any], chunk_index: int) -> Dict[str, Any]:
        """
        Prepare metadata for a chunk.
        
        Args:
            base_metadata: Base metadata common to all chunks
            chunk_index: Index of this chunk
        
        Returns:
            Complete metadata dictionary
        """
        metadata = base_metadata.copy()
        metadata['chunk_index'] = chunk_index
        
        # Ensure all values are simple types for ChromaDB
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                metadata[key] = str(value)
        
        return metadata
    
    def log_ingestion_start(self, source: str, source_type: str):
        """Log the start of ingestion."""
        logger.info(f"Starting ingestion: {source_type} - {source}")
    
    def log_ingestion_complete(self, source: str, chunks_added: int):
        """Log successful completion of ingestion."""
        logger.info(f"✓ Ingestion complete: {source} ({chunks_added} chunks)")
    
    def log_ingestion_error(self, source: str, error: Exception):
        """Log ingestion error."""
        logger.error(f"✗ Ingestion failed: {source} - {str(error)}")

