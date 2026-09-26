# FRIDAY — Autonomous Windows 11 Desktop AI Assistant

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://www.microsoft.com/windows)
[![Gemini](https://img.shields.io/badge/AI%20Engine-Gemini%202.5%20Live%20Bidi-8E75C4.svg)](https://aistudio.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*A hyper-competent, real-time multimodal duplex voice assistant and private executive co-pilot engineered natively for Windows 11.*

</div>

---

## ⚡ Core Capabilities

- **🎙️ Real-Time Gemini Multimodal Live Bidi Voice**:
  - Sub-300ms speech-to-speech latency powered by `gemini-2.5-flash-native-audio-latest`.
  - Continuous 16kHz PCM microphone streaming with instant barge-in (interruption) detection.
  - 24kHz studio-quality neural audio output with natural inflection, wit, and authentic emotion.
  - Seamless bilingual understanding (Hindi, Hinglish, and English).

- **🖥️ 40+ Deep Win32 Kernel Automation Tools**:
  - **App & Window Orchestration**: Dynamic window snapping (left, right, maximize, grid), focus management, task switching, and process kill.
  - **Silent Background File I/O**: Read, write, and create files/scripts in the background without moving cursor or hijacking keyboard focus.
  - **PowerShell Automation**: Secure terminal execution, network diagnostics, Wi-Fi toggling, and recycle bin management.
  - **Visual Screen Grounding**: AI vision screen peeler that extracts on-screen text and OCR data directly into clipboard.

- **🛡️ Autonomous Social Gatekeeper (Instagram Direct & Snapchat Web)**:
  - 100% Native DOM Message Bridge via Tampermonkey userscripts.
  - **Zero Mouse Hijacking**: Interacts directly with browser React DOM using synthetic input events and DOM stamping (`dataset.fridaySent`).
  - Context-aware contact screening, dynamic conversational icebreakers, and autonomous multi-turn messaging.

- **🧠 Persistent Long-Term Memory & Conflict Resolution**:
  - Persistent user profile, boundaries, and relationship directives saved in thread-safe JSON.
  - Automatic semantic conflict resolution ensuring negated preferences (e.g., dislikes) immediately prune contradictory memories.

- **📚 Student Reflexion Engine**:
  - Learns like a human assistant from user feedback and corrections.
  - Automatically identifies teaching moments (*"from now on...", "aage se aise mat karna..."*), extracts actionable rules into a Student Notebook, and strictly adheres to them in future turns.

- **🌐 Live Web Intelligence & Local Vector RAG**:
  - Autonomous web research engine (Tavily AI) for real-time news, live sports, documentation, and weather.
  - Embedded local semantic vector memory using Gemini embeddings and cosine similarity.

- **✨ Cybernetic HUD GUI**:
  - Desktop interface built on PyWebView (Edge WebView2).
  - Interactive 3D Three.js particle orb audio visualizer, live real-time transcripts, and dark glassmorphic controls.

---

## 📋 Prerequisites

1. **Operating System**: **Windows 10 or 11 (64-bit)** *(FRIDAY relies natively on Win32 user32, COM, and audio subsystems)*.
2. **Python**: **Python 3.10, 3.11, or 3.12**.
3. **Google Gemini API Key**: Free API key from [Google AI Studio](https://aistudio.google.com/).
4. **(Optional) Tavily API Key**: Free search API key from [Tavily AI](https://app.tavily.com/) for live real-time web research.

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/anonymousagyat/FRIDAY-AI.git
cd FRIDAY-AI
```

### 2. Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configuration
On first launch, FRIDAY will automatically initialize `config.json` from `config.example.json`. Alternatively, you can copy it manually:
```powershell
copy config.example.json config.json
```
Open `config.json` and insert your Gemini API Key:
```json
{
    "assistant_name": "Friday",
    "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
    "gemini_live_model": "gemini-2.5-flash-native-audio-latest",
    "gemini_voice": "Aoede",
    "default_browser": "chrome",
    "tavily_api_key": ""
}
```

### 5. Launch FRIDAY
```powershell
python main.py
```

---

## 📱 Social Gatekeeper Setup (Optional)

To enable autonomous chatting and message gatekeeping for Instagram Direct or Snapchat Web:

1. Install the [Tampermonkey Extension](https://www.tampermonkey.net/) in your browser (Brave, Chrome, or Edge).
2. Open Tampermonkey Dashboard $\rightarrow$ **Add a new script**:
   - For Instagram Direct: Copy and paste the contents of [`friday_bridge_userscript.js`](friday_bridge_userscript.js).
   - For Snapchat Web: Copy and paste the contents of [`friday_snapchat_bridge.js`](friday_snapchat_bridge.js).
3. Save the scripts (`Ctrl + S`).
4. Ensure your browser extension permissions are set to **"On all sites"** and **Developer mode** is enabled under `chrome://extensions` or `brave://extensions`.

---

## 🛠️ Project Structure

```text
FRIDAY-AI/
├── core/
│   ├── action_executor.py       # Executes 40+ atomic Win32 PC actions
│   ├── ai_engine.py             # Agentic planner and prompt architecture
│   ├── assistant.py             # Core orchestrator coordinating voice & tools
│   ├── context_tracker.py       # Multi-turn window and conversation context
│   ├── gemini_live_client.py    # Bidirectional WebSocket Gemini Live voice client
│   ├── memory.py                # Thread-safe persistent long-term memory engine
│   ├── screen_peeler.py         # Gemini Vision OCR text extraction
│   ├── screen_reader.py         # Visual screen analysis and bounding
│   ├── social_bridge_server.py  # Local HTTP bridge (127.0.0.1:8765)
│   ├── social_gatekeeper.py     # Social persona engine and DOM dispatcher
│   ├── student_engine.py        # Autonomous reflexion and learning notebook
│   ├── system_control.py        # Deep Windows kernel and process orchestrator
│   ├── task_planner.py          # Atomic action declarations and tool schemas
│   ├── vector_rag.py            # Local vector semantic knowledge oracle
│   └── web_researcher.py        # Tavily AI live web crawler
├── ui/
│   ├── assets/                  # HUD images, particle textures
│   ├── css/styles.css           # Glassmorphism cybernetic HUD styling
│   ├── js/                      # Three.js 3D orb and audio visualizer scripts
│   └── index.html               # Main desktop webview interface
├── config.example.json          # Configuration template
├── contacts.example.json        # Contact directory template
├── friday_bridge_userscript.js  # Instagram Direct Tampermonkey userscript
├── friday_snapchat_bridge.js    # Snapchat Web Tampermonkey userscript
├── main.py                      # Application bootstrap and PyWebView launcher
├── requirements.txt             # Python package dependencies
├── LICENSE                      # MIT License
└── README.md                    # Documentation
```

---

## 🔒 Privacy & Security

- **No Remote Telemetry**: Your conversations, local files, and user memory remain 100% on your local computer.
- **Local Credential Storage**: Keys and personal memory files (`config.json`, `contacts.json`, `user_memory.json`, `chat_history.json`) are strictly excluded via `.gitignore` and never committed or transmitted to third parties.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
