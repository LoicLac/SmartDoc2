"""
Web page ingestor using Trafilatura for clean content extraction.
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from .base_ingestor import BaseIngestor
from ..config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


class WebIngestor(BaseIngestor):
    """Ingest web pages with clean content extraction."""
    
    def validate_source(self, source: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def ingest(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Ingest a web page.
        
        Args:
            source: URL to scrape
            **kwargs:
                - headers: Dict (custom HTTP headers)
                - timeout: int (request timeout in seconds)
        
        Returns:
            Dict with ingestion results
        """
        if not self.validate_source(source):
            raise ValueError(f"Invalid URL: {source}")
        
        self.log_ingestion_start(source, 'web')
        
        # Add to registry
        source_id = self.registry.add_source(
            source_type='web',
            source_path=source
        )
        
        try:
            # Fetch content
            logger.info(f"Fetching {source}...")
            html = self._fetch_url(source, **kwargs)
            
            # Extract main content
            logger.info("Extracting content...")
            content, metadata = self._extract_content(html, source)
            
            # Chunk content
            chunks = self._create_chunks(content, source, metadata)
            
            # Store in ChromaDB
            self._store_chunks(chunks, source, metadata)
            
            # Update registry
            registry_metadata = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'date': metadata.get('date', ''),
                'total_chunks': len(chunks),
                'content_length': len(content)
            }
            self.registry.update_status(source, 'success', registry_metadata)
            
            self.log_ingestion_complete(source, len(chunks))
            
            return {
                'status': 'success',
                'source': source,
                'chunks_added': len(chunks),
                'metadata': registry_metadata
            }
            
        except Exception as e:
            self.log_ingestion_error(source, e)
            self.registry.update_status(source, 'failed', {'error': str(e)})
            raise
    
    def _fetch_url(
        self,
        url: str,
        headers: Dict[str, str] = None,
        timeout: int = 30
    ) -> str:
        """Fetch URL content."""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SmartDoc2/0.1; +https://github.com/loic/smartdoc2)'
        }
        
        if headers:
            default_headers.update(headers)
        
        try:
            response = requests.get(url, headers=default_headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    
    def _extract_content(self, html: str, url: str) -> tuple[str, Dict[str, Any]]:
        """Extract main content and metadata from HTML."""
        # Use Trafilatura for clean extraction
        content = trafilatura.extract(
            html,
            include_links=True,
            include_images=False,
            include_tables=True
        )
        
        if not content:
            logger.warning("Trafilatura extraction returned empty, trying fallback")
            content = self._extract_content_fallback(html)
        
        # Extract metadata
        metadata = trafilatura.extract_metadata(html)
        
        metadata_dict = {
            'url': url,
            'title': metadata.title if metadata else '',
            'author': metadata.author if metadata else '',
            'date': metadata.date if metadata else '',
            'description': metadata.description if metadata else ''
        }
        
        return content, metadata_dict
    
    def _extract_content_fallback(self, html: str) -> str:
        """Fallback content extraction using BeautifulSoup."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer']):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)
    
    def _create_chunks(
        self,
        content: str,
        source_url: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create chunks from extracted content."""
        # Chunk the text
        text_chunks = self.chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        
        chunks = []
        for chunk_idx, chunk_text in enumerate(text_chunks):
            chunks.append({
                'content': chunk_text,
                'chunk_index': chunk_idx,
                'url': source_url,
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'date': metadata.get('date', '')
            })
        
        return chunks
    
    def _store_chunks(
        self,
        chunks: List[Dict[str, Any]],
        source_url: str,
        metadata: Dict[str, Any]
    ):
        """Store chunks in ChromaDB."""
        if not chunks:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            # Generate unique ID
            content_hash = self.hash_content(chunk['content'])
            chunk_id = self.generate_chunk_id(source_url, idx, content_hash)
            
            # Prepare metadata
            chunk_metadata = {
                'source': source_url,
                'source_type': 'web',
                'content_type': 'web',
                'chunk_index': chunk['chunk_index'],
                'title': chunk.get('title', ''),
                'author': chunk.get('author', ''),
                'indexed_at': datetime.now().isoformat()
            }
            
            documents.append(chunk['content'])
            metadatas.append(chunk_metadata)
            ids.append(chunk_id)
        
        # Add to ChromaDB
        self.chroma.add_documents(documents, metadatas, ids)

