"""
Screen Reader — Live desktop visual capture, Gemini Vision Grounding, and Autonomous Clicking.
Equipped with Win32 thread desktop attachment for 100% fail-safe capture from any context,
multi-backend screen grab (mss, PIL, GDI), and millimeter-accurate visual coordinate localization.
"""

import os
import sys
import time
import json
import ctypes
from ctypes import wintypes
import datetime
from typing import Optional, Tuple, Dict, Any
from PIL import Image

try:
    import mss
except ImportError:
    mss = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.02
except ImportError:
    pyautogui = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class ScreenReader:
    """Captures screenshots, locates UI elements with Gemini Vision Grounding, and clicks coordinates."""

    def __init__(self, ai_engine=None):
        self.ai_engine = ai_engine
        self.user32 = ctypes.windll.user32 if sys.platform == "win32" else None
        self.kernel32 = ctypes.windll.kernel32 if sys.platform == "win32" else None

        # Gemini Client initialization
        self.gemini_api_key = getattr(ai_engine, 'gemini_api_key', '') if ai_engine else ''
        self.genai_client = None
        if self.gemini_api_key and genai:
            try:
                self.genai_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"[ScreenReader GenAI Init Warning] {e}")

        # Models prioritized by lowest latency and vision grounding precision
        self.vision_models = [
            'gemini-flash-lite-latest',
            'gemini-3.8-flash',
            'gemini-3.7-flash',
            'gemini-3.6-flash'
        ]

        self._ensure_desktop_attached()

    def set_ai_engine(self, ai_engine):
        self.ai_engine = ai_engine
        if ai_engine and hasattr(ai_engine, 'gemini_api_key'):
            self.gemini_api_key = ai_engine.gemini_api_key
            if self.gemini_api_key and genai:
                try:
                    self.genai_client = genai.Client(api_key=self.gemini_api_key)
                except Exception:
                    pass

    def _ensure_desktop_attached(self):
        """Ensure thread is attached to the active interactive desktop (WinSta0\\default)."""
        if not self.user32:
            return

        try:
            # 1. Set DPI Awareness
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                self.user32.SetProcessDPIAware()

            # 2. Attach Window Station to WinSta0
            hwinsta0 = self.user32.OpenWindowStationW("winsta0", False, 0x000F037F)
            if hwinsta0:
                self.user32.SetProcessWindowStation(hwinsta0)

            # 3. Attach Thread Desktop to the active user desktop
            hdesk = self.user32.OpenInputDesktop(0, False, 0x000F01FF)
            if not hdesk:
                hdesk = self.user32.OpenDesktopW("default", 0, False, 0x000F01FF)
            if hdesk:
                self.user32.SetThreadDesktop(hdesk)
        except Exception as e:
            print(f"[ScreenReader Desktop Attach] {e}")

    # =========================================================================
    # 1. SCREEN CAPTURE PIPELINE
    # =========================================================================

    def capture(self) -> Optional[Image.Image]:
        """Capture the current screen as a PIL Image across mss, ImageGrab, and Win32 GDI."""
        self._ensure_desktop_attached()

        # Method 1: mss (Ultra-fast direct screen grab, 10-30ms)
        if mss:
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                pass

        # Method 2: PIL ImageGrab
        if ImageGrab:
            try:
                return ImageGrab.grab(all_screens=True)
            except Exception:
                pass

        # Method 3: Direct Win32 GDI BitBlt
        if self.user32:
            try:
                gdi32 = ctypes.windll.gdi32
                w = self.user32.GetSystemMetrics(0)
                h = self.user32.GetSystemMetrics(1)
                hdc = self.user32.GetDC(0)
                memdc = gdi32.CreateCompatibleDC(hdc)
                hbitmap = gdi32.CreateCompatibleBitmap(hdc, w, h)
                old_bmp = gdi32.SelectObject(memdc, hbitmap)

                SRCCOPY = 0x00CC0020 | 0x40000000
                gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, SRCCOPY)
                gdi32.SelectObject(memdc, old_bmp)

                class BITMAPINFOHEADER(ctypes.Structure):
                    _fields_ = [
                        ('biSize', wintypes.DWORD),
                        ('biWidth', wintypes.LONG),
                        ('biHeight', wintypes.LONG),
                        ('biPlanes', wintypes.WORD),
                        ('biBitCount', wintypes.WORD),
                        ('biCompression', wintypes.DWORD),
                        ('biSizeImage', wintypes.DWORD),
                        ('biXPelsPerMeter', wintypes.LONG),
                        ('biYPelsPerMeter', wintypes.LONG),
                        ('biClrUsed', wintypes.DWORD),
                        ('biClrImportant', wintypes.DWORD)
                    ]

                bmi = BITMAPINFOHEADER()
                bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.biWidth = w
                bmi.biHeight = -h
                bmi.biPlanes = 1
                bmi.biBitCount = 32
                bmi.biCompression = 0

                buf = ctypes.create_string_buffer(w * h * 4)
                gdi32.GetDIBits(hdc, hbitmap, 0, h, buf, ctypes.byref(bmi), 0)

                gdi32.DeleteObject(hbitmap)
                gdi32.DeleteDC(memdc)
                self.user32.ReleaseDC(0, hdc)

                return Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
            except Exception as e:
                print(f"[GDI BitBlt Error] {e}")

        return None

    def capture_and_save(self, path: str = None) -> str:
        """Capture and save screenshot to Desktop or custom path."""
        try:
            img = self.capture()
            if not img:
                return ""

            if not path:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                path = os.path.join(desktop, f"JarvisVision_{timestamp}.png")

            img.save(path)
            return path
        except Exception as e:
            print(f"[Save Screenshot Error] {e}")
            return ""

    # =========================================================================
    # 2. GEMINI VISUAL GROUNDING & TARGET LOCALIZATION
    # =========================================================================

    def locate_element(self, query: str, screenshot: Optional[Image.Image] = None) -> Optional[Tuple[int, int]]:
        """
        Locate any UI button, link, search box, card, or icon on screen using Gemini Multimodal Grounding.
        Returns exact Windows screen pixel coordinates (screen_x, screen_y) or None.
        """
        img = screenshot or self.capture()
        if not img:
            print("[Locate Element] Failed to capture screen.")
            return None

        # Refresh genai client if needed
        if not self.genai_client and self.ai_engine and hasattr(self.ai_engine, 'gemini_api_key'):
            self.gemini_api_key = self.ai_engine.gemini_api_key
            if self.gemini_api_key and genai:
                try:
                    self.genai_client = genai.Client(api_key=self.gemini_api_key)
                except Exception:
                    pass

        if not self.genai_client:
            print("[Locate Element] GenAI client not initialized.")
            return None

        orig_w, orig_h = img.size

        # Downsample for fast network transit
        img_prep = img.copy()
        if img_prep.width > 1024 or img_prep.height > 1024:
            img_prep.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

        prompt = f"""You are a precise screen navigation assistant.
Locate the interactable UI element described as: "{query}" on this Windows screen.

Return ONLY a valid JSON object:
{{"point": [y, x], "found": true}}
Coordinates must be normalized integers between 0 and 1000 (y = 0..1000 from top to bottom, x = 0..1000 from left to right).
If the element cannot be found or is not visible, return:
{{"found": false}}
"""

        for model in self.vision_models:
            try:
                cfg = types.GenerateContentConfig(
                    response_mime_type="application/json"
                ) if types else None

                resp = self.genai_client.models.generate_content(
                    model=model,
                    contents=[prompt, img_prep],
                    config=cfg
                )

                if not resp or not resp.text:
                    continue

                raw_text = resp.text.strip()
                data = self._extract_json(raw_text)
                found = data.get("found", True)

                py, px = None, None
                if "point" in data:
                    py, px = data["point"]
                elif "box_2d" in data:
                    ymin, xmin, ymax, xmax = data["box_2d"]
                    py = (ymin + ymax) // 2
                    px = (xmin + xmax) // 2

                if found and py is not None and px is not None:
                    screen_x = int((px / 1000.0) * orig_w)
                    screen_y = int((py / 1000.0) * orig_h)
                    print(f"[Vision Grounding] Found '{query}' at screen pixel ({screen_x}, {screen_y}) via {model}")
                    return (screen_x, screen_y)
                elif not found:
                    print(f"[Vision Grounding] Element '{query}' reported not visible on screen by {model}.")
                    return None
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    print(f"[Vision Grounding] Model {model} rate limited, falling back...")
                else:
                    print(f"[Vision Grounding] Model {model} warning: {err_str[:80]}")
                continue

        return None

    def find_and_click(self, query: str, double_click: bool = False, button: str = 'left') -> dict:
        """
        Locate any visual UI element on screen and autonomously click it.
        Executes silently without touching audio or displaying alerts.
        """
        if not query or not query.strip():
            return {'success': False, 'message': 'Element query khali hai.'}

        coords = self.locate_element(query.strip())
        if not coords:
            return {'success': False, 'message': f"Visual element '{query}' screen pe nahi mila."}

        x, y = coords
        if not pyautogui:
            return {'success': False, 'message': 'PyAutoGUI available nahi hai click karne ke liye.'}

        try:
            if double_click:
                pyautogui.doubleClick(x=x, y=y, button=button)
            else:
                pyautogui.click(x=x, y=y, button=button)

            return {
                'success': True,
                'x': x,
                'y': y,
                'message': f"Clicked '{query}' at ({x}, {y})."
            }
        except Exception as e:
            return {'success': False, 'message': f"Click error at ({x}, {y}): {e}"}

    # =========================================================================
    # 3. MULTIMODAL SCENE ANALYSIS
    # =========================================================================

    def analyze(self, question: str = None) -> str:
        """Capture screen and analyze with Gemini Multimodal Vision."""
        if not self.ai_engine:
            return "AI vision engine ready nahi hai bhai."

        try:
            img = self.capture()
            if not img:
                return "Screen capture nahi ho paya."

            return self.ai_engine.analyze_screen(img, question)
        except Exception as e:
            return f"Screen analyze karne mein error aaya: {e}"

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from raw text or markdown block, unwrapping lists to dicts."""
        if not text:
            return {}

        def _clean(v):
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                return v[0]
            if isinstance(v, dict):
                return v
            return {}

        try:
            val = json.loads(text.strip())
            c = _clean(val)
            if c:
                return c
        except Exception:
            pass

        import re
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if m:
            try:
                val = json.loads(m.group(1).strip())
                c = _clean(val)
                if c:
                    return c
            except Exception:
                pass

        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                val = json.loads(text[start:end+1])
                c = _clean(val)
                if c:
                    return c
            except Exception:
                pass
        return {}


