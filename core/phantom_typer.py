"""
Phantom Typer — Ghost Keyboard & High-Speed Input Injection.
Ported from IRIS-AI Phantom Typer architecture.
Injects code, multiline text, and commands directly into the active IDE,
browser, or terminal with sub-millisecond clipboard stream injection.
"""

import time
import logging
from typing import Dict, Any, Optional
import pyautogui
import pyperclip

logger = logging.getLogger(__name__)


class PhantomTyper:
    """Simulates high-speed typing and instant clipboard paste injection."""

    def __init__(self):
        pyautogui.FAILSAFE = True

    def ghost_paste(self, text: str, restore_clipboard: bool = True) -> Dict[str, Any]:
        """
        Instant injection: Copies text to Windows clipboard and simulates Ctrl+V.
        Restores previous clipboard contents after paste if requested.
        """
        if not text:
            return {'success': False, 'message': 'Empty text'}

        old_clip = ""
        if restore_clipboard:
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = ""

        try:
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.05)

            if restore_clipboard and old_clip:
                # Restore previous clipboard content after 200ms
                time.sleep(0.15)
                pyperclip.copy(old_clip)

            return {'success': True, 'message': 'Ghost injection complete!'}
        except Exception as e:
            logger.error(f"[PhantomTyper] Ghost paste error: {e}")
            return {'success': False, 'message': str(e)}

    def stream_type(self, text: str, delay: float = 0.01) -> Dict[str, Any]:
        """Simulate real human keyboard typing at specified speed."""
        try:
            for char in text:
                if char == '\n':
                    pyautogui.press('enter')
                else:
                    pyautogui.write(char)
                if delay > 0:
                    time.sleep(delay)
            return {'success': True, 'message': 'Stream typing complete!'}
        except Exception as e:
            logger.error(f"[PhantomTyper] Stream type error: {e}")
            return {'success': False, 'message': str(e)}
