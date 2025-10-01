"""
Extract images from PDF documents.
"""

import PyPDF2
from pdf2image import convert_from_path
from PIL import Image
import io
from typing import List, Dict, Any
from pathlib import Path
import logging

from ..config import PDF_DPI

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Extract images from PDF documents."""
    
    def extract_images_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        Extract all images from a PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            List of dicts with image data and metadata
        """
        images = []
        
        try:
            # Try to extract embedded images first
            embedded = self._extract_embedded_images(pdf_path)
            if embedded:
                images.extend(embedded)
                logger.info(f"Extracted {len(embedded)} embedded images from {pdf_path.name}")
            
            # Also render pages as images (for diagrams that are vector graphics)
            rendered = self._render_pages_as_images(pdf_path)
            if rendered:
                images.extend(rendered)
                logger.info(f"Rendered {len(rendered)} pages as images from {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Image extraction failed for {pdf_path}: {e}")
        
        return images
    
    def _extract_embedded_images(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract embedded images from PDF."""
        images = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    # PyPDF2 doesn't directly extract images well
                    # This is a placeholder - in production, use pdfplumber or pymupdf
                    if '/XObject' in page['/Resources']:
                        xobject = page['/Resources']['/XObject'].get_object()
                        
                        for obj in xobject:
                            if xobject[obj]['/Subtype'] == '/Image':
                                try:
                                    # Extract image data
                                    size = (xobject[obj]['/Width'], xobject[obj]['/Height'])
                                    data = xobject[obj].get_data()
                                    
                                    images.append({
                                        'data': data,
                                        'page': page_num + 1,
                                        'type': 'embedded',
                                        'size': size
                                    })
                                except Exception as e:
                                    logger.warning(f"Failed to extract image from page {page_num + 1}: {e}")
        
        except Exception as e:
            logger.error(f"Embedded image extraction failed: {e}")
        
        return images
    
    def _render_pages_as_images(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Render PDF pages as images (for vector graphics)."""
        images = []
        
        try:
            # Convert PDF pages to images
            pil_images = convert_from_path(
                str(pdf_path),
                dpi=PDF_DPI,
                fmt='png'
            )
            
            for page_num, pil_image in enumerate(pil_images):
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                images.append({
                    'data': img_byte_arr.read(),
                    'page': page_num + 1,
                    'type': 'rendered',
                    'size': pil_image.size
                })
        
        except Exception as e:
            logger.error(f"Page rendering failed: {e}")
        
        return images
    
    def filter_schematic_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter images to identify likely schematics/diagrams.
        
        Uses heuristics like image size, aspect ratio, etc.
        """
        filtered = []
        
        for img in images:
            width, height = img['size']
            aspect_ratio = width / height if height > 0 else 0
            
            # Heuristics for schematic detection
            # - Reasonable size (not tiny icons, not full page photos)
            # - Reasonable aspect ratio
            min_dimension = min(width, height)
            
            if min_dimension > 200 and 0.3 < aspect_ratio < 3.0:
                filtered.append(img)
        
        logger.info(f"Filtered {len(filtered)} potential schematics from {len(images)} images")
        return filtered

