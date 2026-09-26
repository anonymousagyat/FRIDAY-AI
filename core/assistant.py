"""
FRIDAY Orchestrator — Gemini Multimodal Live (Bidi WebSocket) Native Audio Kernel.
Pure real-time duplex voice, sub-300ms speech-to-speech, autonomous Win32 PC tool calling.
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from .ai_engine import AIEngine
from .system_control import SystemControl
from .task_planner import TaskPlanner
from .screen_reader import ScreenReader
from .action_executor import ActionExecutor
from .web_researcher import WebResearcher
from .mobile_control import MobileControl
from .vector_rag import VectorMemory
from .phantom_typer import PhantomTyper
from .screen_peeler import ScreenPeeler
from .gemini_live_client import GeminiLiveClient
from .social_gatekeeper import SocialGatekeeper


class Assistant:
    """Real-Time Duplex Voice AI Orchestrator powered exclusively by Gemini Live Bidi."""

    def __init__(self, window=None):
        self.window = window
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.base_dir, 'config.json')
        self.history_path = os.path.join(self.base_dir, 'chat_history.json')

        # 1. Config & Persistent History
        self.config = self._load_config()
        self.chat_history = self._load_history()

        # 2. Kernel Automation & Tool Subsystems
        self.ai = AIEngine(self.config)
        self.system = SystemControl()
        self.screen_reader = ScreenReader(ai_engine=self.ai)
        self.system.set_screen_reader(self.screen_reader)
        self.web_researcher = WebResearcher(self.config.get('tavily_api_key', ''))
        self.mobile = MobileControl()
        self.vector_rag = VectorMemory(gemini_api_key=self.config.get('gemini_api_key', ''))
        self.phantom_typer = PhantomTyper()
        self.screen_peeler = ScreenPeeler(self.ai)
        self.social_gatekeeper = SocialGatekeeper(
            ai_engine=self.ai,
            mobile_control=self.mobile,
            system_control=self.system,
            base_dir=self.base_dir
        )
        self.planner = TaskPlanner(self.ai)
        self.executor = ActionExecutor(
            self.system,
            self.screen_reader,
            self.web_researcher,
            self.mobile,
            self.vector_rag,
            self.phantom_typer,
            self.screen_peeler,
            self.social_gatekeeper
        )

        # 3. Dictation Mode
        self.dictation_mode = self.config.get('dictation_mode', False)

        # 4. Gemini Multimodal Live Bidi Client (Primary & Sole Voice Engine)
        self.live_client = None
        if self.config.get('gemini_api_key'):
            try:
                self.live_client = GeminiLiveClient(
                    config=self.config,
                    executor=self.executor,
                    on_text=self._add_chat_message,
                    on_state=self._update_ui_state,
                    on_live_transcript=self._set_live_transcript
                )
                print("[Assistant] Gemini Live Bidi client initialized.")
            except Exception as e:
                print(f"[Assistant] Gemini Live Bidi initialization error: {e}")
                self.live_client = None

        # 5. Wire Hermes Bridge (Background task agent)
        try:
            from .hermes_bridge import hermes_bridge
            class _HermesVoiceAdapter:
                def __init__(self, asst):
                    self.asst = asst
                def speak_sync(self, text):
                    self.asst.send_assistant_alert(text)
            hermes_bridge.set_voice_output(_HermesVoiceAdapter(self))
        except Exception as e:
            print(f"[Assistant] Hermes bridge wiring notice: {e}")

        # 6. Wire Student Reflexion Engine
        try:
            from .student_engine import student_engine
            self.student = student_engine
            self.student.set_ai_engine(self.ai)
        except Exception as e:
            print(f"[Assistant] Student engine wiring notice: {e}")
            self.student = None

    # =========================================================================
    # LIFECYCLE & WINDOW ATTACHMENT
    # =========================================================================

    def set_window(self, window):
        self.window = window
        if window:
            window.events.loaded += self._on_ui_loaded

    def _on_ui_loaded(self):
        name = self.config.get('assistant_name', 'Friday')
        self._evaluate_js(f"setAssistantName('{name}')")
        voice = self.config.get('gemini_voice', 'Aoede')
        self._evaluate_js(f"updateVoiceBadge('{voice}')")

        if self.live_client:
            self.live_client.start()
            self._update_ui_state("ready")
        else:
            self._update_ui_state("idle")

    def start(self):
        if self.live_client:
            self.live_client.start()

    def stop(self):
        if self.live_client:
            self.live_client.stop()
        if hasattr(self, 'social_gatekeeper') and self.social_gatekeeper:
            try:
                self.social_gatekeeper.stop_autonomous_chat()
            except Exception:
                pass
        self._save_config()
        self._save_history()

    # =========================================================================
    # PERSISTENCE
    # =========================================================================

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        try:
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        disk_config = json.load(f)
                    for key in ['gemini_api_key', 'tavily_api_key', 'gemini_voice', 'gemini_live_model']:
                        if key in disk_config:
                            self.config[key] = disk_config[key]
                except Exception:
                    pass
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Config save error: {e}")

    def _load_history(self) -> list:
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self):
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"History save error: {e}")

    # =========================================================================
    # UI BRIDGE HELPERS
    # =========================================================================

    def _evaluate_js(self, js_code: str):
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.updateAssistantState) {{ {js_code} }}")
            except Exception:
                pass

    def _update_ui_state(self, state: str):
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.updateAssistantState) updateAssistantState('{state}')")
            except Exception:
                pass

    def _add_chat_message(self, role: str, text: str):
        escaped = text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
        self.chat_history.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        max_history = self.config.get('max_history', 50)
        if len(self.chat_history) > max_history:
            self.chat_history = self.chat_history[-max_history:]
        self._save_history()

        if self.window:
            try:
                self.window.evaluate_js(f"if(window.addChatMessage) addChatMessage('{role}', '{escaped}')")
            except Exception:
                pass

    def _set_live_transcript(self, text: str):
        escaped = text.replace('\\', '\\\\').replace("'", "\\'")
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.setLiveTranscript) setLiveTranscript('{escaped}')")
            except Exception:
                pass

    def _show_notification(self, text: str, ntype: str = 'info'):
        escaped = text.replace('\\', '\\\\').replace("'", "\\'")
        if self.window:
            try:
                self.window.evaluate_js(f"if(window.showNotification) showNotification('{escaped}', '{ntype}')")
            except Exception:
                pass

    def send_assistant_alert(self, text: str):
        """Send background notification alert into chat and Live session."""
        self._add_chat_message("assistant", text)
        if self.live_client and self.live_client.is_connected:
            self.live_client.send_text_message(f"[Background System Notification]: {text}")

    # =========================================================================
    # PUBLIC API (Exposed via JSApiBridge)
    # =========================================================================

    def start_listening(self) -> None:
        if self.live_client:
            if not self.live_client.is_running:
                self.live_client.start()
            self.live_client.resume_mic()
            self._update_ui_state("listening")

    def stop_listening(self) -> None:
        if self.live_client:
            self.live_client.pause_mic()
            self._update_ui_state("idle")

    def send_text_message(self, text: str) -> None:
        clean = (text or "").strip()
        if not clean:
            return
        self._add_chat_message("user", clean)
        if self.live_client:
            if not self.live_client.is_running:
                self.live_client.start()
            self.live_client.send_text_message(clean)
            self._update_ui_state("processing")

    def toggle_dictation(self, enabled: bool) -> None:
        self.dictation_mode = enabled
        self.config['dictation_mode'] = enabled
        self._save_config()
        self._show_notification(
            "Dictation mode ON — spoken words will type at cursor" if enabled else "Dictation mode OFF",
            "success"
        )

    def get_config(self) -> dict:
        return self.config

    def update_config(self, key: str, value: str) -> None:
        self.config[key] = value
        self._save_config()

        if key == 'gemini_voice':
            clean_val = str(value).strip()
            if self.live_client:
                self.live_client.set_voice(clean_val)
            self._evaluate_js(f"updateVoiceBadge('{clean_val}')")
            self._show_notification(f"Gemini Live Voice switched to {clean_val}!", "success")
        elif key == 'gemini_api_key':
            clean_key = str(value).strip()
            self.vector_rag = VectorMemory(gemini_api_key=clean_key)
            self.executor.set_vector_memory(self.vector_rag)
            self.ai = AIEngine(self.config)
            self.screen_reader.set_ai_engine(self.ai)
            self.screen_peeler = ScreenPeeler(self.ai)
            self.executor.set_screen_peeler(self.screen_peeler)
            if self.live_client:
                self.live_client.api_key = clean_key
                try:
                    from google import genai
                    self.live_client.client = genai.Client(api_key=clean_key)
                    self.live_client.start()
                except Exception as e:
                    print(f"[Assistant] Live client key restart notice: {e}")
            self._show_notification("Gemini API key updated!", "success")
        elif key == 'tavily_api_key':
            clean_tavily = str(value).strip()
            self.web_researcher = WebResearcher(clean_tavily)
            self.executor.set_web_researcher(self.web_researcher)
            self._show_notification("Tavily AI Search Key updated!", "success")
        elif key == 'assistant_name':
            self.set_assistant_name(value)

    def set_assistant_name(self, name: str, wake_word: str = None) -> dict:
        clean_name = name.strip() if name else "Friday"
        self.config['assistant_name'] = clean_name
        self._save_config()

        self.ai = AIEngine(self.config)
        self.planner = TaskPlanner(self.ai)
        self.screen_reader.set_ai_engine(self.ai)

        if self.window:
            try:
                self.window.set_title(clean_name)
            except Exception:
                pass

        self._evaluate_js(f"setAssistantName('{clean_name}')")
        self._show_notification(f"Assistant renamed to {clean_name}.", "success")
        return {'success': True, 'name': clean_name}

    def get_chat_history(self) -> list:
        return self.chat_history

    def clear_chat_history(self) -> None:
        self.chat_history = []
        self._save_history()
        if self.ai:
            self.ai.reset_chat()

    # Legacy Compatibility Stubs (Clean no-ops)
    def toggle_wake_word(self, enabled: bool) -> None:
        pass

    def set_ai_model(self, model: str) -> dict:
        return {'success': True, 'model': model}

    def get_tts_quota(self) -> dict:
        return {
            'name': 'Google Gemini Live (Bidi Duplex)',
            'status': 'Active',
            'quota_remaining': 'Unlimited Free (24kHz Native Audio)',
            'quota_percent': 100,
            'details': 'Direct duplex WebSocket streaming'
        }

    def set_tts_engine(self, engine: str) -> dict:
        return self.get_tts_quota()
