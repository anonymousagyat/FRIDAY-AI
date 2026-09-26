"""
ScreenPeeler — Multimodal Visual OCR & Region Selection Engine.
Ported from IRIS-AI ScreenPeeler architecture.
Captures screen regions or active windows, performs high-precision OCR
using Gemini Vision, and copies the extracted text directly to the Windows clipboard.
"""

import os
import io
import time
import logging
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageGrab
import pyperclip

logger = logging.getLogger(__name__)


class ScreenPeeler:
    """Multimodal screen OCR and text extractor."""

    def __init__(self, ai_engine=None):
        self.ai = ai_engine

    def set_ai_engine(self, ai_engine):
        self.ai = ai_engine

    def capture_region(self, bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """Capture screen region (bbox: x1, y1, x2, y2) or full screen."""
        try:
            if bbox:
                return ImageGrab.grab(bbox=bbox)
            return ImageGrab.grab()
        except Exception as e:
            logger.error(f"[ScreenPeeler] Grab error: {e}")
            return None

    def peel_text(self, bbox: Optional[Tuple[int, int, int, int]] = None, copy_to_clipboard: bool = True) -> Dict[str, Any]:
        """
        Extract text from screen region using Gemini Vision.
        Copies the extracted text directly into Windows clipboard.
        """
        img = self.capture_region(bbox)
        if not img:
            return {'success': False, 'message': 'Screen capture failed.'}

        if not self.ai:
            return {'success': False, 'message': 'AI engine not configured for OCR.'}

        prompt = (
            "You are an OCR extraction engine. Extract ALL text visible in this image verbatim. "
            "Preserve code, numbers, punctuation, and layout. "
            "Do NOT summarize. Do NOT add conversational commentary. Return ONLY the raw extracted text."
        )

        try:
            extracted_text = self.ai.chat(prompt, image=img)
            extracted_text = extracted_text.strip() if extracted_text else ""

            if copy_to_clipboard and extracted_text:
                pyperclip.copy(extracted_text)
                preview = extracted_text[:120].replace('\n', ' ')
                msg = f"Screen se text extract karke clipboard par copy kar diya Boss! ('{preview}...')"
            else:
                msg = "Koi text detect nahi hua, Boss."

            return {
                'success': True,
                'text': extracted_text,
                'copied_to_clipboard': copy_to_clipboard,
                'message': msg
            }
        except Exception as e:
            logger.error(f"[ScreenPeeler] OCR error: {e}")
            return {'success': False, 'message': f"OCR extraction error: {str(e)}"}
