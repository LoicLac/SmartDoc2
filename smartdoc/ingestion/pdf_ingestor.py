"""
PDF ingestor using LlamaParse and Gemini Vision.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, track
import time

try:
    from llama_parse import LlamaParse
except ImportError:
    LlamaParse = None

from .base_ingestor import BaseIngestor
from ..vision.gemini_analyzer import GeminiAnalyzer
from ..vision.image_extractor import ImageExtractor
from ..config import (
    LLAMAPARSE_API_KEY,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_FILE_SIZE_WARNING,
    MAX_FILE_SIZE_HARD
)

logger = logging.getLogger(__name__)
console = Console()


class PDFIngestor(BaseIngestor):
    """Ingest PDF documents with text, tables, and schematic analysis."""
    
    def __init__(self, registry, chroma_manager):
        super().__init__(registry, chroma_manager)
        self.console = Console()
        
        # Initialize components
        if LLAMAPARSE_API_KEY and LlamaParse:
            self.parser = LlamaParse(api_key=LLAMAPARSE_API_KEY)
            logger.info("LlamaParse initialized")
        else:
            self.parser = None
            logger.warning("LlamaParse not available - text extraction will be limited")
        
        self.vision_analyzer = GeminiAnalyzer()
        self.image_extractor = ImageExtractor()
    
    def validate_source(self, source: str) -> bool:
        """Validate PDF file exists and is readable."""
        path = Path(source)
        return path.exists() and path.suffix.lower() == '.pdf'
    
    def ingest(self, source: str, **kwargs) -> Dict[str, Any]:
        """
        Ingest a PDF document.
        
        Args:
            source: Path to PDF file
            **kwargs:
                - analyze_schematics: bool (default True)
                - initial_query: str (optional context for schematic analysis)
        
        Returns:
            Dict with ingestion results
        """
        pdf_path = Path(source)
        
        # Validate
        if not self.validate_source(source):
            raise ValueError(f"Invalid PDF source: {source}")
        
        # Check file size
        if not self.check_file_size(pdf_path, MAX_FILE_SIZE_WARNING, MAX_FILE_SIZE_HARD):
            return {'status': 'skipped', 'reason': 'File too large'}
        
        self.log_ingestion_start(source, 'pdf')
        
        # Add to registry
        file_size = pdf_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        # Show file info
        self.console.print(f"\n[bold cyan]📄 PDF Information:[/bold cyan]")
        self.console.print(f"  File: [white]{pdf_path.name}[/white]")
        self.console.print(f"  Size: [yellow]{file_size_mb:.1f} MB[/yellow]")
        self.console.print(f"  Analyze schematics: [{'green' if kwargs.get('analyze_schematics', True) else 'red'}]{kwargs.get('analyze_schematics', True)}[/]")
        
        # Estimate processing time
        estimated_time = self._estimate_processing_time(file_size_mb, kwargs.get('analyze_schematics', True))
        self.console.print(f"  Estimated time: [dim]~{estimated_time}[/dim]\n")
        
        source_id = self.registry.add_source(
            source_type='pdf',
            source_path=str(pdf_path),
            file_size=file_size
        )
        
        try:
            # Step 1: Extract text and tables with LlamaParse
            self.console.print("[bold blue]Step 1/3:[/bold blue] Extracting text and tables...")
            text_chunks = self._extract_text(pdf_path)
            self.console.print(f"[green]✓ Extracted {len(text_chunks)} text chunks[/green]\n")
            
            # Step 2: Extract and analyze images/schematics
            schematic_chunks = []
            if kwargs.get('analyze_schematics', True):
                self.console.print("[bold blue]Step 2/3:[/bold blue] Analyzing schematics with Gemini Vision...")
                schematic_chunks = self._extract_and_analyze_schematics(
                    pdf_path,
                    source_id,
                    initial_query=kwargs.get('initial_query')
                )
                self.console.print(f"[green]✓ Analyzed {len(schematic_chunks)} schematics[/green]\n")
            else:
                self.console.print("[dim]Step 2/3: Skipped (--no-schematics)[/dim]\n")
            
            # Step 3: Store all chunks in ChromaDB
            self.console.print("[bold blue]Step 3/3:[/bold blue] Storing in database...")
            all_chunks = text_chunks + schematic_chunks
            self._store_chunks(all_chunks, pdf_path)
            self.console.print(f"[green]✓ Stored {len(all_chunks)} chunks in ChromaDB[/green]\n")
            
            # Update registry
            metadata = {
                'pages': self._get_page_count(pdf_path),
                'text_chunks': len(text_chunks),
                'schematic_chunks': len(schematic_chunks),
                'total_chunks': len(all_chunks)
            }
            self.registry.update_status(str(pdf_path), 'success', metadata)
            
            self.log_ingestion_complete(source, len(all_chunks))
            
            return {
                'status': 'success',
                'source': str(pdf_path),
                'chunks_added': len(all_chunks),
                'metadata': metadata
            }
            
        except Exception as e:
            self.log_ingestion_error(source, e)
            self.registry.update_status(str(pdf_path), 'failed', {'error': str(e)})
            raise
    
    def _extract_text(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text and tables from PDF."""
        chunks = []
        
        if self.parser:
            try:
                # Use LlamaParse for high-quality extraction
                self.console.print(f"  [yellow]📤 Uploading to LlamaParse (server-side processing)...[/yellow]")
                self.console.print(f"  [dim]⏱️  This may take 1-5 minutes for complex datasheets[/dim]")
                self.console.print(f"  [dim]💡 The repeated HTTP requests are normal - LlamaParse is processing[/dim]\n")
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=self.console,
                    transient=True
                ) as progress:
                    task = progress.add_task("  Processing PDF with LlamaParse...", total=100)
                    
                    # Simulate progress for visual feedback
                    # (LlamaParse doesn't provide real progress, so we estimate)
                    start_time = time.time()
                    documents = None
                    
                    # Start parsing in background
                    import threading
                    def parse_pdf():
                        nonlocal documents
                        documents = self.parser.load_data(str(pdf_path))
                    
                    parse_thread = threading.Thread(target=parse_pdf)
                    parse_thread.start()
                    
                    # Update progress bar while parsing
                    while parse_thread.is_alive():
                        elapsed = time.time() - start_time
                        # Estimate progress based on time (slows down as it progresses)
                        estimated_progress = min(95, (elapsed / 120) * 100)  # Cap at 95% until done
                        progress.update(task, completed=estimated_progress)
                        time.sleep(0.5)
                    
                    parse_thread.join()
                    progress.update(task, completed=100)
                
                elapsed_time = int(time.time() - start_time)
                self.console.print(f"  [green]✓ LlamaParse completed in {elapsed_time}s[/green]")
                
                # Process documents
                self.console.print(f"  [dim]Processing {len(documents)} pages...[/dim]")
                for doc_idx, doc in enumerate(documents):
                    # Chunk the text
                    text_chunks = self.chunk_text(doc.text, CHUNK_SIZE, CHUNK_OVERLAP)
                    
                    for chunk_idx, chunk_text in enumerate(text_chunks):
                        chunks.append({
                            'content': chunk_text,
                            'type': 'text',
                            'page': doc_idx + 1,  # Approximate page number
                            'chunk_index': chunk_idx
                        })
                
                logger.info(f"Extracted {len(chunks)} text chunks")
                
            except Exception as e:
                logger.error(f"LlamaParse extraction failed: {e}")
                # Fallback to basic extraction
                chunks = self._extract_text_fallback(pdf_path)
        else:
            chunks = self._extract_text_fallback(pdf_path)
        
        return chunks
    
    def _extract_text_fallback(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Fallback text extraction using PyPDF2."""
        import PyPDF2
        
        chunks = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    
                    if text.strip():
                        # Chunk the page text
                        text_chunks = self.chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
                        
                        for chunk_idx, chunk_text in enumerate(text_chunks):
                            chunks.append({
                                'content': chunk_text,
                                'type': 'text',
                                'page': page_num + 1,
                                'chunk_index': chunk_idx
                            })
            
            logger.info(f"Extracted {len(chunks)} text chunks (fallback)")
            
        except Exception as e:
            logger.error(f"Fallback text extraction failed: {e}")
        
        return chunks
    
    def _extract_and_analyze_schematics(
        self,
        pdf_path: Path,
        source_id: int,
        initial_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract images and analyze schematics."""
        chunks = []
        
        try:
            # Extract images
            self.console.print(f"  [dim]Extracting images from PDF...[/dim]")
            images = self.image_extractor.extract_images_from_pdf(pdf_path)
            
            # Filter for likely schematics
            schematics = self.image_extractor.filter_schematic_images(images)
            
            if not schematics:
                self.console.print(f"  [yellow]⚠ No schematics detected in PDF[/yellow]")
                return chunks
            
            self.console.print(f"  [cyan]Found {len(schematics)} potential schematics[/cyan]")
            if initial_query:
                self.console.print(f"  [dim]Query context: \"{initial_query}\"[/dim]")
            
            # Analyze each schematic with progress bar
            for img_data in track(schematics, description="  Analyzing with Gemini Vision", console=self.console):
                image_bytes = img_data['data']
                page_num = img_data['page']
                
                # Generate image hash
                img_hash = self.hash_image(image_bytes)
                
                # Check cache first
                cached = self.registry.get_schematic_cache(img_hash, initial_query)
                
                if cached:
                    # Using cached result
                    analysis = {
                        'description': cached['vision_result'],
                        'cached': True
                    }
                else:
                    # Analyze with Gemini Vision (can take 5-10 seconds per image)
                    analysis = self.vision_analyzer.analyze_schematic(
                        image_bytes,
                        query_context=initial_query,
                        page_number=page_num
                    )
                    
                    # Cache result
                    if analysis['success']:
                        self.registry.cache_vision_result(
                            source_id=source_id,
                            image_hash=img_hash,
                            query_context=initial_query or "general",
                            vision_result=analysis['description'],
                            page_number=page_num
                        )
                
                # Create chunk for schematic
                if analysis.get('description'):
                    chunks.append({
                        'content': analysis['description'],
                        'type': 'schematic',
                        'page': page_num,
                        'image_hash': img_hash,
                        'confidence': analysis.get('confidence', 0.7),
                        'pin_mappings': analysis.get('pin_mappings', {}),
                        'chunk_index': 0
                    })
            
        except Exception as e:
            logger.error(f"Schematic analysis failed: {e}")
        
        return chunks
    
    def _store_chunks(self, chunks: List[Dict[str, Any]], pdf_path: Path):
        """Store chunks in ChromaDB."""
        if not chunks:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            # Generate unique ID
            content_hash = self.hash_content(chunk['content'])
            chunk_id = self.generate_chunk_id(str(pdf_path), idx, content_hash)
            
            # Prepare metadata
            metadata = {
                'source': str(pdf_path),
                'source_type': 'pdf',
                'content_type': chunk['type'],
                'page': chunk['page'],
                'chunk_index': chunk['chunk_index'],
                'indexed_at': datetime.now().isoformat()
            }
            
            # Add schematic-specific metadata
            if chunk['type'] == 'schematic':
                metadata['image_hash'] = chunk['image_hash']
                metadata['confidence'] = chunk.get('confidence', 0.7)
                if chunk.get('pin_mappings'):
                    metadata['pin_mappings'] = str(chunk['pin_mappings'])
            
            documents.append(chunk['content'])
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Add to ChromaDB
        self.chroma.add_documents(documents, metadatas, ids)
    
    def _get_page_count(self, pdf_path: Path) -> int:
        """Get total page count of PDF."""
        import PyPDF2
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except:
            return 0
    
    def reprocess_schematic(
        self,
        pdf_path: Path,
        page_number: int,
        query_context: str
    ) -> Dict[str, Any]:
        """
        Reprocess a specific schematic with new query context.
        
        Args:
            pdf_path: Path to PDF
            page_number: Page number to reprocess
            query_context: New query context
        
        Returns:
            Updated analysis results
        """
        source = self.registry.get_source(str(pdf_path))
        if not source:
            raise ValueError(f"Source not found: {pdf_path}")
        
        # Extract images from specific page
        images = self.image_extractor.extract_images_from_pdf(pdf_path)
        page_images = [img for img in images if img['page'] == page_number]
        
        if not page_images:
            raise ValueError(f"No images found on page {page_number}")
        
        # Analyze with new context
        image_data = page_images[0]['data']
        img_hash = self.hash_image(image_data)
        
        analysis = self.vision_analyzer.analyze_schematic(
            image_data,
            query_context=query_context,
            page_number=page_number
        )
        
        # Update cache
        if analysis['success']:
            self.registry.cache_vision_result(
                source_id=source['id'],
                image_hash=img_hash,
                query_context=query_context,
                vision_result=analysis['description'],
                page_number=page_number
            )
        
        return analysis
    
    def _estimate_processing_time(self, file_size_mb: float, analyze_schematics: bool) -> str:
        """Estimate processing time based on file size and options."""
        # Base time for text extraction
        base_time = max(30, file_size_mb * 5)  # ~5 seconds per MB
        
        # Add time for schematic analysis if enabled
        if analyze_schematics:
            # Rough estimate: +30 seconds per schematic (usually 2-5 schematics)
            base_time += 60
        
        if base_time < 60:
            return f"{int(base_time)} seconds"
        else:
            minutes = int(base_time / 60)
            return f"{minutes}-{minutes + 2} minutes"

