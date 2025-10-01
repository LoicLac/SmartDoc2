"""
ChromaDB persistent client manager.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging

from ..config import CHROMA_PERSIST_DIR, COLLECTION_NAME, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class ChromaManager:
    """Manages persistent ChromaDB client and operations."""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self._init_client()
    
    def _init_client(self):
        """Initialize persistent ChromaDB client."""
        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "SmartDoc workspace knowledge base"}
            )
            
            logger.info(f"ChromaDB initialized at {CHROMA_PERSIST_DIR}")
            logger.info(f"Collection '{COLLECTION_NAME}' ready with {self.collection.count()} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents to the collection.
        
        Args:
            documents: List of text content
            metadatas: List of metadata dicts
            ids: List of unique IDs
        """
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to collection")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the collection.
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter
        
        Returns:
            Query results with documents, metadatas, distances
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                where_document=where_document
            )
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def get_by_source(self, source_path: str) -> Dict[str, Any]:
        """Get all documents from a specific source."""
        try:
            results = self.collection.get(
                where={"source": source_path}
            )
            return results
        except Exception as e:
            logger.error(f"Failed to get documents by source: {e}")
            raise
    
    def delete_source(self, source_path: str):
        """Delete all documents from a specific source."""
        try:
            # Get all IDs for this source
            results = self.collection.get(
                where={"source": source_path}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} documents from source: {source_path}")
            else:
                logger.info(f"No documents found for source: {source_path}")
                
        except Exception as e:
            logger.error(f"Failed to delete source documents: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            total_docs = self.collection.count()
            
            # Get all metadata to calculate stats
            all_data = self.collection.get()
            
            # Count by source type
            source_types = {}
            sources = set()
            
            for metadata in all_data['metadatas']:
                source_type = metadata.get('source_type', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
                sources.add(metadata.get('source', 'unknown'))
            
            return {
                'total_documents': total_docs,
                'total_sources': len(sources),
                'documents_by_type': source_types,
                'collection_name': COLLECTION_NAME,
                'persist_directory': CHROMA_PERSIST_DIR
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}
    
    def reset_collection(self):
        """Delete all documents from the collection (use with caution!)."""
        try:
            self.client.delete_collection(name=COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "SmartDoc workspace knowledge base"}
            )
            logger.warning(f"Collection '{COLLECTION_NAME}' has been reset")
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            raise

