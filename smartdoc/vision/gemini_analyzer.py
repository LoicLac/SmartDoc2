"""
Gemini Vision API integration for schematic and diagram analysis.
"""

import google.generativeai as genai
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
from PIL import Image
import io

from ..config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    VISION_MAX_RETRIES
)

logger = logging.getLogger(__name__)


class GeminiAnalyzer:
    """Handles vision analysis using Gemini API."""
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info(f"GeminiAnalyzer initialized with model: {GEMINI_MODEL}")
    
    def analyze_schematic(
        self,
        image_data: bytes,
        query_context: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a schematic or technical diagram.
        
        Args:
            image_data: Image bytes (PNG, JPG, etc.)
            query_context: Optional user query for focused analysis
            page_number: Optional page number for context
        
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Generate prompt based on context
            if query_context:
                prompt = self._generate_focused_prompt(query_context)
            else:
                prompt = self._generate_general_prompt()
            
            # Add page context if available
            if page_number:
                prompt = f"[Page {page_number}] {prompt}"
            
            # Call Gemini Vision API
            response = self._call_api_with_retry(prompt, image)
            
            # Parse response
            result = {
                'description': response.text,
                'query_context': query_context,
                'page_number': page_number,
                'success': True
            }
            
            # Extract structured data if possible
            result.update(self._extract_structured_data(response.text, query_context))
            
            logger.info(f"Schematic analysis complete (page {page_number})")
            return result
            
        except Exception as e:
            logger.error(f"Schematic analysis failed: {e}")
            return {
                'description': '',
                'error': str(e),
                'success': False
            }
    
    def analyze_multiple_images(
        self,
        images: List[bytes],
        query_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple images in batch.
        
        Args:
            images: List of image bytes
            query_context: Optional query context
        
        Returns:
            List of analysis results
        """
        results = []
        for idx, image_data in enumerate(images):
            result = self.analyze_schematic(image_data, query_context, page_number=idx+1)
            results.append(result)
        return results
    
    def _generate_general_prompt(self) -> str:
        """Generate general analysis prompt for schematics."""
        return """You are analyzing a technical diagram or schematic from an electronics datasheet.

Please provide:
1. A clear description of what this diagram shows
2. Any visible component labels, pin numbers, or connections
3. Important technical details (voltage levels, bus types, pin functions)
4. Any text visible in the diagram

Be specific and technical. Focus on information useful for embedded systems development."""
    
    def _generate_focused_prompt(self, query_context: str) -> str:
        """Generate query-focused prompt for targeted analysis."""
        # Extract focus keywords
        focus_terms = self._extract_focus_terms(query_context)
        
        prompt = f"""You are analyzing a technical schematic or pinout diagram.

User is asking: "{query_context}"

Please focus on:
"""
        
        # Add specific instructions based on query
        if any(term in focus_terms for term in ['spi', 'mosi', 'miso', 'sck']):
            prompt += """
- SPI bus pins: MOSI (Master Out Slave In), MISO (Master In Slave Out), SCK (Clock), CS/SS (Chip Select)
- Identify specific pin numbers and labels
- Note any alternate functions or multiplexing"""
        
        if any(term in focus_terms for term in ['i2c', 'scl', 'sda', 'twi']):
            prompt += """
- I2C/TWI bus pins: SDA (Data), SCL (Clock)
- Pull-up resistor locations
- Identify specific pin numbers and labels"""
        
        if any(term in focus_terms for term in ['uart', 'serial', 'tx', 'rx']):
            prompt += """
- UART/Serial pins: TX (Transmit), RX (Receive)
- Any additional flow control pins (RTS, CTS)
- Identify specific pin numbers and labels"""
        
        if any(term in focus_terms for term in ['power', 'vcc', 'gnd', 'voltage']):
            prompt += """
- Power supply pins: VCC, VDD, GND
- Voltage levels and regulators
- Current ratings if visible"""
        
        if any(term in focus_terms for term in ['pin', 'pinout', 'gpio']):
            prompt += """
- Complete pinout information
- Pin numbers, names, and functions
- Any special purpose pins (reset, enable, etc.)"""
        
        prompt += """

Provide specific pin numbers, labels, and connections.
Be precise and technical. Only state what you can clearly see in the diagram."""
        
        return prompt
    
    def _extract_focus_terms(self, query: str) -> List[str]:
        """Extract focus terms from user query."""
        query_lower = query.lower()
        
        terms = []
        keywords = [
            'spi', 'mosi', 'miso', 'sck', 'i2c', 'scl', 'sda', 'twi',
            'uart', 'serial', 'tx', 'rx', 'power', 'vcc', 'gnd', 'voltage',
            'pin', 'pinout', 'gpio', 'adc', 'dac', 'pwm', 'timer'
        ]
        
        for keyword in keywords:
            if keyword in query_lower:
                terms.append(keyword)
        
        return terms
    
    def _extract_structured_data(
        self,
        response_text: str,
        query_context: Optional[str]
    ) -> Dict[str, Any]:
        """
        Attempt to extract structured data from response.
        
        Args:
            response_text: Raw response from Gemini
            query_context: Original query
        
        Returns:
            Dictionary with extracted structured data
        """
        structured = {}
        
        # Try to extract pin mappings
        pins = self._extract_pin_mappings(response_text)
        if pins:
            structured['pin_mappings'] = pins
        
        # Try to extract component list
        components = self._extract_components(response_text)
        if components:
            structured['components'] = components
        
        # Estimate confidence based on specificity
        confidence = self._estimate_confidence(response_text, query_context)
        structured['confidence'] = confidence
        
        return structured
    
    def _extract_pin_mappings(self, text: str) -> Dict[str, str]:
        """Extract pin mappings from response text."""
        import re
        
        pins = {}
        
        # Pattern: PIN_NAME = D11, MOSI: D11, etc.
        patterns = [
            r'([A-Z][A-Z0-9_]+)[:\s=]+([A-Z]?[0-9]+)',
            r'([A-Z]+)[:\s]+Pin\s+([0-9]+)',
            r'Pin\s+([0-9]+)[:\s]+([A-Z][A-Z0-9_/]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                pins[match[0]] = match[1]
        
        return pins
    
    def _extract_components(self, text: str) -> List[str]:
        """Extract component names from response text."""
        import re
        
        components = []
        
        # Pattern: IC names, chip identifiers, etc.
        pattern = r'\b([A-Z]{2,}[0-9]{2,}[A-Z0-9]*)\b'
        matches = re.findall(pattern, text)
        
        return list(set(matches))
    
    def _estimate_confidence(self, text: str, query_context: Optional[str]) -> float:
        """
        Estimate confidence in the analysis.
        
        Higher confidence for:
        - Specific pin numbers
        - Clear technical terms
        - Matching query context
        
        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.5  # Base confidence
        
        # Check for specific technical details
        if any(term in text.lower() for term in ['pin', 'gpio', 'port']):
            confidence += 0.1
        
        # Check for pin numbers
        import re
        if re.search(r'\b[A-Z]?[0-9]{1,2}\b', text):
            confidence += 0.15
        
        # Check for technical protocols
        protocols = ['spi', 'i2c', 'uart', 'pwm', 'adc', 'dac']
        if any(protocol in text.lower() for protocol in protocols):
            confidence += 0.1
        
        # If query context provided, check if response addresses it
        if query_context:
            query_terms = self._extract_focus_terms(query_context)
            if any(term in text.lower() for term in query_terms):
                confidence += 0.15
        
        return min(1.0, confidence)
    
    def _call_api_with_retry(self, prompt: str, image: Image.Image) -> Any:
        """Call Gemini API with retry logic."""
        last_error = None
        
        for attempt in range(VISION_MAX_RETRIES):
            try:
                response = self.model.generate_content(
                    [prompt, image],
                    generation_config=genai.types.GenerationConfig(
                        temperature=GEMINI_TEMPERATURE
                    )
                )
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"API call attempt {attempt + 1} failed: {e}")
                if attempt < VISION_MAX_RETRIES - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise last_error

