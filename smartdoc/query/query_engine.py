"""
Query engine with confidence-based schematic reprocessing.
"""

from typing import Dict, Any, List, Optional
import logging

from ..core.registry import Registry
from ..core.chroma_client import ChromaManager
from ..vision.gemini_analyzer import GeminiAnalyzer
from ..config import CONFIDENCE_THRESHOLD, TOP_K_RESULTS, RERANK_TOP_N

logger = logging.getLogger(__name__)


class QueryEngine:
    """Query engine with smart schematic reprocessing."""
    
    def __init__(self, registry: Registry, chroma_manager: ChromaManager):
        self.registry = registry
        self.chroma = chroma_manager
        self.vision_analyzer = GeminiAnalyzer()
    
    def query(
        self,
        query_text: str,
        source_filter: Optional[str] = None,
        source_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query the knowledge base.
        
        Args:
            query_text: User query
            source_filter: Optional filter by source path/URL
            source_type_filter: Optional filter by type ('pdf', 'github', 'web')
        
        Returns:
            Query results with confidence score and source citations
        """
        logger.info(f"Query: {query_text}")
        
        # Build where clause for filtering
        where_clause = {}
        if source_filter:
            where_clause['source'] = source_filter
        if source_type_filter:
            where_clause['source_type'] = source_type_filter
        
        # Query ChromaDB
        results = self.chroma.query(
            query_text=query_text,
            n_results=TOP_K_RESULTS,
            where=where_clause if where_clause else None
        )
        
        # Process results
        processed_results = self._process_results(results, query_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(processed_results)
        
        logger.info(f"Query returned {len(processed_results)} results with confidence {confidence:.2f}")
        
        # Check if we should trigger schematic reprocessing
        should_reprocess = (
            confidence < CONFIDENCE_THRESHOLD and
            self._is_schematic_query(query_text) and
            self._has_schematic_sources(processed_results)
        )
        
        response = {
            'query': query_text,
            'results': processed_results[:RERANK_TOP_N],
            'confidence': confidence,
            'total_results': len(processed_results),
            'should_reprocess': should_reprocess
        }
        
        if should_reprocess:
            logger.info("Low confidence + schematic query detected - suggesting reprocessing")
            response['reprocess_suggestion'] = (
                f"Low confidence answer ({confidence:.2f}). "
                "Would you like me to analyze relevant schematics with your specific query?"
            )
        
        return response
    
    def query_with_reprocess(self, query_text: str) -> Dict[str, Any]:
        """
        Query with automatic schematic reprocessing if needed.
        
        Args:
            query_text: User query
        
        Returns:
            Enhanced query results with vision analysis
        """
        # Initial query
        initial_results = self.query(query_text)
        
        # Check if reprocessing is needed
        if not initial_results['should_reprocess']:
            return initial_results
        
        logger.info("Triggering automatic schematic reprocessing...")
        
        # Find relevant schematics
        schematic_results = self._find_schematic_results(initial_results['results'])
        
        if not schematic_results:
            logger.info("No schematics found for reprocessing")
            return initial_results
        
        # Reprocess schematics with query context
        vision_results = self._reprocess_schematics(schematic_results, query_text)
        
        # Merge vision results with original results
        enhanced_results = self._merge_results(initial_results, vision_results)
        
        # Recalculate confidence
        enhanced_results['confidence'] = self._calculate_confidence(
            enhanced_results['results']
        )
        enhanced_results['reprocessed'] = True
        
        logger.info(f"Enhanced confidence: {enhanced_results['confidence']:.2f}")
        
        return enhanced_results
    
    def _process_results(
        self,
        raw_results: Dict[str, Any],
        query_text: str
    ) -> List[Dict[str, Any]]:
        """Process raw ChromaDB results into structured format."""
        processed = []
        
        if not raw_results['ids'] or not raw_results['ids'][0]:
            return processed
        
        for idx in range(len(raw_results['ids'][0])):
            result = {
                'content': raw_results['documents'][0][idx],
                'metadata': raw_results['metadatas'][0][idx],
                'distance': raw_results['distances'][0][idx] if 'distances' in raw_results else 0,
                'score': 1 - (raw_results['distances'][0][idx] if 'distances' in raw_results else 0)
            }
            
            # Add citation
            result['citation'] = self._format_citation(result['metadata'])
            
            processed.append(result)
        
        return processed
    
    def _format_citation(self, metadata: Dict[str, Any]) -> str:
        """Format source citation."""
        source = metadata.get('source', 'Unknown')
        source_type = metadata.get('source_type', 'unknown')
        
        if source_type == 'pdf':
            page = metadata.get('page', '?')
            return f"[{source}, p.{page}]"
        
        elif source_type == 'github':
            file_path = metadata.get('file_path', '')
            return f"[github:{source}/{file_path}]"
        
        elif source_type == 'web':
            title = metadata.get('title', '')
            if title:
                return f"[{title} - {source}]"
            return f"[{source}]"
        
        return f"[{source}]"
    
    def _calculate_confidence(self, results: List[Dict[str, Any]]) -> float:
        """
        Calculate overall confidence score for results.
        
        Higher weight for top results.
        """
        if not results:
            return 0.0
        
        # Weighted average with exponential decay
        total_weight = 0
        weighted_score = 0
        
        for idx, result in enumerate(results[:5]):  # Top 5 results
            weight = 0.5 ** idx  # Exponential decay: 0.5, 0.25, 0.125, ...
            score = result.get('score', 0.5)
            
            # Boost confidence for schematic results
            if result['metadata'].get('content_type') == 'schematic':
                cached_confidence = result['metadata'].get('confidence', 0.7)
                score = (score + cached_confidence) / 2
            
            weighted_score += score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _is_schematic_query(self, query_text: str) -> bool:
        """Check if query is related to schematics or technical diagrams."""
        query_lower = query_text.lower()
        
        schematic_keywords = [
            'pin', 'pinout', 'schematic', 'diagram', 'circuit',
            'spi', 'i2c', 'uart', 'gpio', 'bus',
            'mosi', 'miso', 'sck', 'scl', 'sda', 'tx', 'rx',
            'voltage', 'power', 'vcc', 'gnd',
            'connection', 'wiring', 'interface'
        ]
        
        return any(keyword in query_lower for keyword in schematic_keywords)
    
    def _has_schematic_sources(self, results: List[Dict[str, Any]]) -> bool:
        """Check if any results are from sources with schematics."""
        for result in results:
            source_type = result['metadata'].get('source_type')
            if source_type == 'pdf':
                # Check if this PDF has schematics in registry
                source_path = result['metadata'].get('source')
                source_info = self.registry.get_source(source_path)
                if source_info:
                    metadata = source_info.get('metadata', {})
                    if isinstance(metadata, str):
                        import json
                        metadata = json.loads(metadata)
                    if metadata.get('schematic_chunks', 0) > 0:
                        return True
        
        return False
    
    def _find_schematic_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find results that reference schematics."""
        schematic_results = []
        
        for result in results:
            if result['metadata'].get('content_type') == 'schematic':
                schematic_results.append(result)
        
        return schematic_results
    
    def _reprocess_schematics(
        self,
        schematic_results: List[Dict[str, Any]],
        query_text: str
    ) -> List[Dict[str, Any]]:
        """Reprocess schematics with query-specific analysis."""
        vision_results = []
        
        for result in schematic_results:
            metadata = result['metadata']
            source = metadata.get('source')
            image_hash = metadata.get('image_hash')
            page = metadata.get('page')
            
            if not image_hash:
                continue
            
            # Check if we already have cached analysis for this query
            cached = self.registry.get_schematic_cache(image_hash, query_text)
            
            if cached:
                logger.info(f"Using cached reprocessed analysis for {source} page {page}")
                vision_results.append({
                    'content': cached['vision_result'],
                    'metadata': metadata,
                    'score': 0.9,  # High confidence for targeted analysis
                    'citation': self._format_citation(metadata),
                    'reprocessed': True
                })
            else:
                logger.info(f"Reprocessing schematic: {source} page {page}")
                # Note: In a full implementation, we'd fetch the image and reanalyze
                # For now, we'll just note that reprocessing would happen here
                vision_results.append({
                    'content': result['content'],
                    'metadata': metadata,
                    'score': result['score'],
                    'citation': result['citation'],
                    'reprocessed': False,
                    'note': 'Reprocessing would occur here with actual image data'
                })
        
        return vision_results
    
    def _merge_results(
        self,
        original_results: Dict[str, Any],
        vision_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge original results with vision-enhanced results."""
        # Start with vision results (higher priority)
        merged_results = vision_results.copy()
        
        # Add original results that aren't schematics
        for result in original_results['results']:
            if result['metadata'].get('content_type') != 'schematic':
                merged_results.append(result)
        
        # Sort by score
        merged_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Update original results dict
        enhanced = original_results.copy()
        enhanced['results'] = merged_results[:RERANK_TOP_N]
        
        return enhanced
    
    def format_response(self, query_results: Dict[str, Any]) -> str:
        """Format query results as human-readable text."""
        output = []
        
        output.append(f"Query: {query_results['query']}")
        output.append(f"Confidence: {query_results['confidence']:.2f}")
        output.append(f"Found {query_results['total_results']} results\n")
        
        if query_results.get('should_reprocess'):
            output.append(f"⚠️  {query_results['reprocess_suggestion']}\n")
        
        output.append("Results:")
        output.append("-" * 80)
        
        for idx, result in enumerate(query_results['results'], 1):
            output.append(f"\n{idx}. {result['citation']}")
            output.append(f"   Score: {result['score']:.2f}")
            
            # Truncate content for display
            content = result['content']
            if len(content) > 300:
                content = content[:300] + "..."
            output.append(f"   {content}")
            
            if result.get('reprocessed'):
                output.append("   🔄 [Reprocessed with query context]")
        
        return '\n'.join(output)

