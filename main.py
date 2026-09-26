"""
Main Entry Point for Jarvis Assistant.
Launches the PyWebView desktop application with a clean JS API bridge.
"""

import os
import sys
import warnings

# Suppress library deprecation and harmless internal warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Ensure running on Windows
if sys.platform != "win32":
    print("\n[ERROR] FRIDAY is designed exclusively for Windows 10 / 11.")
    print("It relies on deep Win32 kernel APIs, COM, and native audio hardware subsystems.")
    sys.exit(1)

# Ensure UTF-8 console encoding on Windows to avoid charmap codec errors
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import shutil
base_dir = os.path.dirname(os.path.abspath(__file__))

# First-run setup: automatically initialize config.json from template if missing
config_file = os.path.join(base_dir, 'config.json')
example_config = os.path.join(base_dir, 'config.example.json')
if not os.path.exists(config_file) and os.path.exists(example_config):
    try:
        shutil.copyfile(example_config, config_file)
        print("[First-Run Setup] Created config.json from config.example.json template.")
    except Exception as e:
        print(f"[First-Run Setup] Notice creating config.json: {e}")

# First-run setup: initialize contacts.json if missing
contacts_file = os.path.join(base_dir, 'contacts.json')
example_contacts = os.path.join(base_dir, 'contacts.example.json')
if not os.path.exists(contacts_file) and os.path.exists(example_contacts):
    try:
        shutil.copyfile(example_contacts, contacts_file)
        print("[First-Run Setup] Created contacts.json from contacts.example.json template.")
    except Exception as e:
        print(f"[First-Run Setup] Notice creating contacts.json: {e}")

import webview
from core.assistant import Assistant


class JSApiBridge:
    """Clean, dedicated JavaScript API Bridge.
    Exposes only explicitly defined methods to pywebview, preventing COM/WinForms property recursion.
    """

    def __init__(self, assistant: Assistant):
        self._assistant = assistant

    def start_listening(self):
        return self._assistant.start_listening()

    def stop_listening(self):
        return self._assistant.stop_listening()

    def send_text_message(self, text: str):
        return self._assistant.send_text_message(text)

    def toggle_wake_word(self, enabled: bool):
        return self._assistant.toggle_wake_word(enabled)

    def toggle_dictation(self, enabled: bool):
        return self._assistant.toggle_dictation(enabled)

    def get_config(self):
        return self._assistant.get_config()

    def update_config(self, key: str, value: str):
        return self._assistant.update_config(key, value)

    def get_chat_history(self):
        return self._assistant.get_chat_history()

    def clear_chat_history(self):
        return self._assistant.clear_chat_history()

    def set_assistant_name(self, name: str, wake_word: str = None):
        return self._assistant.set_assistant_name(name, wake_word)

    def set_ai_model(self, model: str):
        return self._assistant.set_ai_model(model)

    def get_tts_quota(self):
        return self._assistant.get_tts_quota()

    def set_tts_engine(self, engine: str):
        return self._assistant.set_tts_engine(engine)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ui_dir = os.path.join(base_dir, 'ui')

    # Create assistant orchestrator instance
    assistant = Assistant()

    # Create the clean API bridge
    bridge = JSApiBridge(assistant)

    # Create the window
    window = webview.create_window(
        title=assistant.config.get('assistant_name', 'JARVIS'),
        url=os.path.join(ui_dir, 'index.html'),
        js_api=bridge,
        width=1200,
        height=800,
        min_size=(800, 600),
        background_color='#0a0a0f',
        frameless=False,
        easy_drag=True,
        text_select=False,
    )

    # Pass window reference to assistant for evaluate_js calls
    assistant.set_window(window)

    # Start PyWebView (Edge WebView2)
    webview.start(
        func=assistant.start,
        debug=False,
        gui='edgechromium'
    )

    # Cleanup upon closing
    assistant.stop()


if __name__ == '__main__':
    main()
