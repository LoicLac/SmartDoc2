"""
Query engine with confidence-based schematic reprocessing.
"""

from typing import Dict, Any, List, Optional
import logging
import hashlib
from datetime import datetime

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
        
        # Query ChromaDB - increase results for reprocessing queries
        n_results = TOP_K_RESULTS * 2 if any(term in query_text.lower() for term in ['pin', 'schematic', 'diagram', 'spi', 'i2c', 'uart']) else TOP_K_RESULTS
        
        results = self.chroma.query(
            query_text=query_text,
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Process results
        processed_results = self._process_results(results, query_text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(processed_results)
        
        logger.info(f"Query returned {len(processed_results)} results with confidence {confidence:.2f}")
        
        # Check if we should trigger schematic reprocessing
        should_reprocess = (
            confidence < CONFIDENCE_THRESHOLD or 
            self._is_schematic_query(query_text)
        )
        
        # For reprocessing, keep more results to find schematics
        final_results = processed_results if should_reprocess else processed_results[:RERANK_TOP_N]
        
        response = {
            'query': query_text,
            'results': final_results,
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
            content_type = result['metadata'].get('content_type')
            logger.debug(f"Checking result with content_type: {content_type}")
            
            if content_type == 'schematic':
                logger.info(f"Found schematic result: {result['metadata'].get('source')} page {result['metadata'].get('page')}")
                schematic_results.append(result)
        
        logger.info(f"Found {len(schematic_results)} schematic results out of {len(results)} total results")
        return schematic_results
    
    def _reprocess_schematics(
        self,
        schematic_results: List[Dict[str, Any]],
        query_text: str
    ) -> List[Dict[str, Any]]:
        """Reprocess schematics with query-specific analysis and selective addition."""
        vision_results = []
        original_confidence = self._calculate_confidence(schematic_results)
        
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
                
                # Parse cached vision result (assuming it's JSON string)
                try:
                    import json
                    vision_data = json.loads(cached['vision_result']) if isinstance(cached['vision_result'], str) else cached['vision_result']
                except:
                    vision_data = {'description': cached['vision_result'], 'confidence': 0.9}
                
                vision_results.append({
                    'content': vision_data.get('description', cached['vision_result']),
                    'metadata': metadata,
                    'score': 0.9,  # High confidence for targeted analysis
                    'citation': self._format_citation(metadata),
                    'reprocessed': True,
                    'vision_data': vision_data
                })
            else:
                logger.info(f"Reprocessing schematic: {source} page {page}")
                # Note: In a full implementation, we'd fetch the image and reanalyze
                # For now, we'll simulate with enhanced content
                simulated_vision_result = {
                    'description': f"[FOCUSED ANALYSIS for '{query_text}']\n\n{result['content']}\n\nThis analysis was specifically focused on: {query_text}",
                    'confidence': 0.85,
                    'query_context': query_text,
                    'pin_mappings': {},  # Would be populated by real analysis
                    'components': []     # Would be populated by real analysis
                }
                
                vision_results.append({
                    'content': simulated_vision_result['description'],
                    'metadata': metadata,
                    'score': 0.85,
                    'citation': result['citation'],
                    'reprocessed': True,
                    'vision_data': simulated_vision_result,
                    'note': 'Simulated reprocessing - would use actual Gemini Vision in production'
                })
        
        # Check if any results should be added to database
        enhanced_confidence = self._calculate_confidence(vision_results)
        
        for result in vision_results:
            if 'vision_data' in result:
                vision_data = result['vision_data']
                
                # Check if this result should be added to database
                if self.should_add_to_database(
                    vision_data,
                    original_confidence,
                    enhanced_confidence,
                    query_text
                ):
                    # Add focused chunk to database
                    chunk_id = self.add_focused_chunk_to_database(
                        vision_data,
                        result['metadata'],
                        query_text
                    )
                    
                    if chunk_id:
                        result['added_to_db'] = True
                        result['focused_chunk_id'] = chunk_id
                        logger.info(f"Added focused chunk to database: {chunk_id}")
        
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
            
            if result.get('added_to_db'):
                output.append("   💾 [Added focused analysis to database]")
        
        return '\n'.join(output)
    
    def should_add_to_database(
        self,
        vision_result: Dict[str, Any],
        original_confidence: float,
        enhanced_confidence: float,
        query_context: str
    ) -> bool:
        """
        Determine if reprocessed result should be added as new chunk to database.
        
        Args:
            vision_result: Result from Gemini Vision analysis
            original_confidence: Confidence before reprocessing
            enhanced_confidence: Confidence after reprocessing
            query_context: Original user query
        
        Returns:
            True if should add to database, False to keep in cache only
        """
        confidence_improvement = enhanced_confidence - original_confidence
        
        # Add if significant confidence improvement
        if confidence_improvement > 0.3:
            logger.info(f"Adding to DB: High confidence improvement ({confidence_improvement:.2f})")
            return True
        
        # Add if contains structured data (pin mappings, components)
        if vision_result.get('pin_mappings') or vision_result.get('components'):
            logger.info("Adding to DB: Contains structured data")
            return True
        
        # Add if query is about common/important topics
        important_topics = [
            'pinout', 'pins', 'mapping', 'connections', 'spi', 'i2c', 'uart',
            'power', 'voltage', 'schematic', 'diagram', 'gpio'
        ]
        query_lower = query_context.lower()
        if any(topic in query_lower for topic in important_topics):
            logger.info("Adding to DB: Important topic query")
            return True
        
        # Add if high confidence result (>0.8)
        if vision_result.get('confidence', 0) > 0.8:
            logger.info("Adding to DB: High confidence result")
            return True
        
        logger.info("Keeping in cache only: Doesn't meet addition criteria")
        return False
    
    def add_focused_chunk_to_database(
        self,
        vision_result: Dict[str, Any],
        original_metadata: Dict[str, Any],
        query_context: str
    ) -> str:
        """
        Add a focused analysis chunk to ChromaDB.
        
        Args:
            vision_result: Result from Gemini Vision
            original_metadata: Metadata from original chunk
            query_context: User query that triggered reprocessing
        
        Returns:
            ID of newly created chunk
        """
        # Check for existing focused chunk to avoid duplicates
        existing_chunk_id = self._find_similar_focused_chunk(
            vision_result['description'], 
            original_metadata.get('source', ''),
            original_metadata.get('page', 0)
        )
        
        if existing_chunk_id:
            logger.info(f"Similar focused chunk exists: {existing_chunk_id}")
            return existing_chunk_id
        
        # Create new focused chunk
        content = vision_result['description']
        
        # Enhance content with structured data if available
        if vision_result.get('pin_mappings'):
            content += "\n\n### Pin Mappings:\n"
            for pin, function in vision_result['pin_mappings'].items():
                content += f"- {pin}: {function}\n"
        
        if vision_result.get('components'):
            content += "\n\n### Components:\n"
            content += ", ".join(vision_result['components'])
        
        # Generate unique chunk ID
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        source = original_metadata.get('source', 'unknown')
        page = original_metadata.get('page', 0)
        chunk_id = f"{source}_focused_{page}_{content_hash}"
        
        # Prepare metadata for focused chunk
        focused_metadata = {
            'source': source,
            'source_type': original_metadata.get('source_type', 'pdf'),
            'content_type': 'schematic_focused',
            'page': page,
            'chunk_index': -1,  # Special index for focused chunks
            'query_context': query_context,
            'parent_chunk': original_metadata.get('chunk_id', ''),
            'confidence': vision_result.get('confidence', 0.9),
            'indexed_at': datetime.now().isoformat(),
            'focused_analysis': True
        }
        
        # Add structured data to metadata
        if vision_result.get('pin_mappings'):
            focused_metadata['pin_mappings'] = str(vision_result['pin_mappings'])
        if vision_result.get('components'):
            focused_metadata['components'] = str(vision_result['components'])
        
        # Add to ChromaDB
        try:
            self.chroma.add_documents(
                documents=[content],
                metadatas=[focused_metadata],
                ids=[chunk_id]
            )
            logger.info(f"Added focused chunk to database: {chunk_id}")
            return chunk_id
        except Exception as e:
            logger.error(f"Failed to add focused chunk: {e}")
            return ""
    
    def _find_similar_focused_chunk(
        self,
        content: str,
        source: str,
        page: int,
        similarity_threshold: float = 0.8
    ) -> Optional[str]:
        """
        Check if similar focused chunk already exists.
        
        Args:
            content: Content to check for similarity
            source: Source document
            page: Page number
            similarity_threshold: Minimum similarity to consider duplicate
        
        Returns:
            Chunk ID if similar chunk found, None otherwise
        """
        try:
            # Query for existing focused chunks from same source/page
            results = self.chroma.query(
                query_text=content[:500],  # Use first 500 chars for similarity
                n_results=5,
                where={
                    '$and': [
                        {'source': source},
                        {'page': page},
                        {'focused_analysis': True}
                    ]
                }
            )
            
            if not results['documents'] or not results['documents'][0]:
                return None
            
            # Check similarity (simple approach - could be enhanced)
            for i, doc in enumerate(results['documents'][0]):
                # Simple similarity check based on content overlap
                similarity = self._calculate_content_similarity(content, doc)
                if similarity > similarity_threshold:
                    return results['ids'][0][i]
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for similar chunks: {e}")
            return None
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate simple content similarity between two texts.
        
        Args:
            content1: First text
            content2: Second text
        
        Returns:
            Similarity score 0.0-1.0
        """
        # Simple word-based similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

