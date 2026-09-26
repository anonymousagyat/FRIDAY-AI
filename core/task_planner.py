"""
Task Planner — Action registry for the AI brain.
No hardcoded intent detection. The AI decides everything.
"""

from typing import List, Dict, Any


class TaskPlanner:
    """Provides the action toolkit to the AI engine. No rule-based planning."""

    AVAILABLE_ACTIONS = [
        {
            'name': 'open_app',
            'description': 'Open any application or game by name',
            'params': {'app_name': 'Name of the app to launch'}
        },
        {
            'name': 'close_app',
            'description': 'Close an application window',
            'params': {'window_title': 'Title of window to close'}
        },
        {
            'name': 'open_url',
            'description': 'Open a URL in a browser',
            'params': {'url': 'Full URL', 'browser': 'Optional: brave/chrome/edge'}
        },
        {
            'name': 'search_web',
            'description': 'Google search in browser',
            'params': {'query': 'Search query', 'browser': 'Optional browser'}
        },
        {
            'name': 'research_web',
            'description': 'Autonomous AI web intelligence (Tavily). Searches the live internet behind the scenes, extracts real-time answers, news, facts, scores, or documentation, and speaks/summarizes the answer without opening a browser window.',
            'params': {'query': 'Search query or question to research online'}
        },
        {
            'name': 'focus_window',
            'description': 'Bring window to foreground',
            'params': {'window_title': 'Window title'}
        },
        {
            'name': 'snap_window',
            'description': 'Snap window to left/right/maximize/minimize',
            'params': {'window_title': 'Window title', 'position': 'left/right/maximize/minimize'}
        },
        {
            'name': 'minimize_window',
            'description': 'Minimize a window',
            'params': {'window_title': 'Window title'}
        },
        {
            'name': 'type_text',
            'description': 'Type text at cursor',
            'params': {'text': 'Text to type'}
        },
        {
            'name': 'press_keys',
            'description': 'Press keyboard shortcut',
            'params': {'keys': 'Key combo like ctrl+c, alt+tab'}
        },
        {
            'name': 'click_at',
            'description': 'Click at screen coordinates',
            'params': {'x': 'X', 'y': 'Y'}
        },
        {
            'name': 'scroll',
            'description': 'Scroll up or down',
            'params': {'direction': 'up/down', 'amount': 'Number of clicks'}
        },
        {
            'name': 'search_files',
            'description': 'Find files or media on PC by keyword or title',
            'params': {'filename': 'File name or keyword to search', 'search_dir': 'Optional directory or drive'}
        },
        {
            'name': 'open_folder',
            'description': 'Open a directory or folder or drive in File Explorer (e.g. Games, Movies, Downloads, D drive)',
            'params': {'folder_name': 'Folder name or path (e.g. Games, Movies, Downloads)', 'drive': 'Optional drive letter (e.g. D or C)'}
        },
        {
            'name': 'open_file',
            'description': 'Open a file or document directly in its default application (can pass query or path)',
            'params': {'path': 'File path or name', 'search_dir': 'Optional directory'}
        },
        {
            'name': 'play_media',
            'description': 'Play a movie, video, or song by title or query from PC storage',
            'params': {'query': 'Name of the movie/song', 'search_dir': 'Optional folder or drive path'}
        },
        {
            'name': 'read_file',
            'description': 'Read text content of a file',
            'params': {'path': 'File path'}
        },
        {
            'name': 'write_file',
            'description': 'Create or write text/code/script to a file SILENTLY in the background without opening Notepad or touching keyboard/cursor. Default relative paths to Desktop.',
            'params': {'file_path': 'File path or filename (e.g. calculator.py, notes.txt, Desktop/code.py)', 'content': 'Full text or code content to write'}
        },
        {
            'name': 'list_directory',
            'description': 'Inspect a folder or directory to see all files, count movies/videos/music/documents, and check contents. ALWAYS use this when user asks "how many movies/files are in X folder", "what is in X folder", or wants to inspect a directory.',
            'params': {'path': 'Folder name, path, or query (e.g. "Movies", "Downloads", "Desktop", "D:\\MOVIES")'}
        },
        {
            'name': 'get_disk_drives',
            'description': 'Storage info for all drives',
            'params': {}
        },
        {
            'name': 'list_running_processes',
            'description': 'List active processes and RAM/CPU usage',
            'params': {}
        },
        {
            'name': 'kill_process',
            'description': 'Force close a process',
            'params': {'process_name': 'Process name'}
        },
        {
            'name': 'system_info',
            'description': 'CPU, RAM, battery stats',
            'params': {}
        },
        {
            'name': 'get_network_info',
            'description': 'IP address and hostname',
            'params': {}
        },
        {
            'name': 'toggle_wifi',
            'description': 'Turn Wi-Fi on or off, or disconnect Wi-Fi',
            'params': {'state': 'on or off'}
        },
        {
            'name': 'toggle_bluetooth',
            'description': 'Turn Bluetooth on or off or open Bluetooth settings',
            'params': {'state': 'on or off'}
        },
        {
            'name': 'run_powershell_command',
            'description': 'Execute PowerShell command',
            'params': {'cmd': 'Command string'}
        },
        {
            'name': 'lock_pc',
            'description': 'Lock computer',
            'params': {}
        },
        {
            'name': 'empty_recycle_bin',
            'description': 'Empty recycle bin',
            'params': {}
        },
        {
            'name': 'take_screenshot',
            'description': 'Capture screen to Desktop',
            'params': {}
        },
        {
            'name': 'get_time',
            'description': 'Current time',
            'params': {}
        },
        {
            'name': 'get_date',
            'description': 'Today\'s date',
            'params': {}
        },
        {
            'name': 'set_volume',
            'description': 'Set system volume (0-100)',
            'params': {'level': 'Volume percentage'}
        },
        {
            'name': 'read_screen',
            'description': 'Analyze what\'s on screen using vision',
            'params': {'question': 'Optional question about the screen'}
        },
        {
            'name': 'find_and_click',
            'description': 'Visually locate any button, icon, link, or card on the screen using AI vision grounding and click it directly',
            'params': {'element_description': 'Visual description of the target button/element to click', 'double_click': 'Optional boolean', 'button': 'Optional left or right'}
        },
        {
            'name': 'play_youtube_music',
            'description': 'Autonomously play a song, artist, playlist, or track on YouTube Music in browser silently. Confirmation MUST be: "Chala diya Boss!"',
            'params': {'query': 'Name of song, artist, or music track to play'}
        },
        {
            'name': 'automate_steam',
            'description': 'Autonomously automate Steam to search, install, download, or launch games. Confirmation MUST be: "Download shuru kar diya Boss!" (for install/download) or "Done Boss!"',
            'params': {'game_name': 'Name of the game', 'action': 'install / launch / search'}
        },
        {
            'name': 'wait',
            'description': 'Pause for seconds',
            'params': {'seconds': 'Seconds to wait'}
        },
        {
            'name': 'dictate',
            'description': 'Toggle dictation mode',
            'params': {}
        },
        # Mobile Telekinesis (Android ADB)
        {
            'name': 'phone_battery',
            'description': 'Check connected Android smartphone battery level, percentage, and charging state',
            'params': {}
        },
        {
            'name': 'phone_open_app',
            'description': 'Open an app on connected Android phone (e.g. WhatsApp, Instagram, YouTube, Spotify, Camera, Settings, Chrome)',
            'params': {'app_name': 'Name of the app to launch on phone'}
        },
        {
            'name': 'phone_swipe',
            'description': 'Swipe on phone screen (up, down, left, right)',
            'params': {'direction': 'up/down/left/right'}
        },
        {
            'name': 'phone_tap',
            'description': 'Tap screen coordinates on phone',
            'params': {'x': 'X coordinate', 'y': 'Y coordinate'}
        },
        {
            'name': 'phone_flashlight',
            'description': 'Toggle or turn on phone camera flashlight/torch',
            'params': {}
        },
        {
            'name': 'phone_screenshot',
            'description': 'Take a screenshot of the connected phone and save to PC Desktop',
            'params': {}
        },
        {
            'name': 'phone_send_file',
            'description': 'Transfer a file from PC to connected Android phone',
            'params': {'pc_path': 'Path of file on PC'}
        },
        # Local Vector Knowledge Oracle (RAG)
        {
            'name': 'index_knowledge',
            'description': 'Index a local directory, codebase, or document into Friday\'s private local vector memory (LanceDB/Vector RAG)',
            'params': {'path': 'Folder or file path to index (e.g. C:\\Projects\\MyApp or code folder)'}
        },
        {
            'name': 'query_knowledge',
            'description': 'Semantic vector search across indexed codebases, documents, or personal notes',
            'params': {'question': 'Question or topic to look up in local knowledge base'}
        },
        # Ghost Keyboard & ScreenPeeler OCR
        {
            'name': 'ghost_type',
            'description': 'Instantly inject code, multiline scripts, or text into the user\'s active window (VS Code, terminal, editor) via ghost typing clipboard stream',
            'params': {'text': 'The code or text to inject'}
        },
        {
            'name': 'peel_screen_text',
            'description': 'Extract all text or code from the screen using Gemini Vision OCR and copy it directly to the Windows clipboard',
            'params': {}
        },
        {
            'name': 'remember',
            'description': 'Save a personal fact, preference, or information to long-term memory',
            'params': {'key': 'Name of fact/preference (e.g. favorite_browser, wifi_password)', 'value': 'The information to remember', 'category': 'Optional: facts, preferences, or user_profile'}
        },
        {
            'name': 'recall_memory',
            'description': 'Recall remembered facts or notes from long-term memory',
            'params': {'query': 'Search query or key to look up (empty for all)'}
        },
        {
            'name': 'forget_memory',
            'description': 'Remove a fact from long-term memory',
            'params': {'key': 'Key to remove', 'category': 'Optional category'}
        },
        {
            'name': 'add_note',
            'description': 'Save a quick timestamped note to memory',
            'params': {'text': 'Note content'}
        },
        {
            'name': 'delegate_to_hermes',
            'description': 'Delegate complex, multi-step, autonomous coding, research, or terminal tasks to Hermes Agent in the background',
            'params': {'task': 'Detailed instructions for the autonomous agent'}
        },
        {
            'name': 'learn_rule',
            'description': 'Save a behavioral rule, preference, or lesson taught by Sir into Friday\'s Student Notebook so she never forgets it',
            'params': {'topic': 'Topic of lesson (snake_case)', 'trigger': 'When this applies', 'rule': 'Actionable rule Sir taught', 'mistake': 'What to avoid', 'example': 'Concrete example'}
        },
        {
            'name': 'list_learned_rules',
            'description': 'Show all rules and lessons Sir has taught Friday in her Student Notebook',
            'params': {'query': 'Optional keyword to search lessons'}
        },
        {
            'name': 'set_voice',
            'description': 'Switch or change Friday speaking voice model (Options: Aoede, Kore, Leda, Autonoe, Erinome, Laomedeia, Charon, Puck, Fenrir, Zephyr, Orus, Umbriel)',
            'params': {'voice_name': 'Name of the voice to switch to (e.g. Kore, Leda, Aoede, Charon, Puck)'}
        },
        {
            'name': 'forget_learned_rule',
            'description': 'Delete a lesson from Friday\'s Student Notebook',
            'params': {'topic_or_id': 'Topic or ID of the lesson to delete'}
        },
        # Social Gatekeeper & Autonomous Messenger (Instagram / Snapchat) - 100% PC Brave Browser
        {
            'name': 'send_social_dm',
            'description': 'Send a message or start an autonomous conversation on Instagram or Snapchat with a contact (e.g. Sharaabi) on PC in Brave Browser (no phone/no ADB). If Sir just says "send hi to X", set auto_chat=False and send exact text. If Sir says "talk to X" (e.g. "Sharaabi se baat karo"), set auto_chat=True to activate autonomous chatting. If Sir provides a specific tone or instruction (e.g. "talk aggressively", "talk politely", "tell him I don\'t wanna talk to him", "ask what\'s the matter"), specify it in directive. params: {platform: "instagram"/"snapchat", contact: "name", message: "optional text", auto_chat: "true/false", directive: "optional custom instruction from Sir"}',
            'params': {
                'platform': 'Platform (instagram or snapchat)',
                'contact': 'Contact name (e.g. Sharaabi)',
                'message': 'Optional custom text to send',
                'auto_chat': 'Optional boolean (true/false) to enable autonomous chatting',
                'directive': 'Optional behavioral directive from Sir (e.g. "aggressive", "polite", "tell him I don\'t wanna talk to him", "ask what\'s the matter")'
            }
        },
        {
            'name': 'stop_social_chat',
            'description': 'Stop autonomous chatting on Instagram/Snapchat and shut down the on-demand bridge server immediately when Sir says "stop talking", "chat band kar do", or "main dekh raha hoon". params: {}',
            'params': {}
        },
        {
            'name': 'reply_as_friday',
            'description': 'Formulate and send a sharp, high-attitude gatekeeper response as FRIDAY to an incoming message from a friend on Instagram or Snapchat. params: {contact: "name", incoming_message: "text"}',
            'params': {'contact': 'Contact name', 'incoming_message': 'Incoming message text'}
        },
        {
            'name': 'save_social_contact',
            'description': 'Save or remember a contact\'s Instagram or Snapchat handle, URL, or username. params: {name: "name", platform: "instagram"/"snapchat", handle: "username or URL"}',
            'params': {'name': 'Contact name', 'platform': 'Platform (instagram or snapchat)', 'handle': 'Username/handle or direct URL'}
        },
        {
            'name': 'list_social_contacts',
            'description': 'List all saved contacts for Instagram and Snapchat. Use this whenever Sir asks "contacts mein kaun kaun hai", "show contacts", "list contacts", or checks saved contacts. params: {}',
            'params': {}
        }
    ]

    def __init__(self, ai_engine):
        self.ai_engine = ai_engine

    def plan(self, command: str, context: dict, screenshot=None) -> dict:
        """Delegate to AI engine for planning."""
        return self.ai_engine.process(command, self.AVAILABLE_ACTIONS, context, screenshot=screenshot)

    def get_available_actions(self) -> list:
        return self.AVAILABLE_ACTIONS

    # Legacy compatibility
    def is_action_command(self, text: str) -> bool:
        return True  # AI decides, not regex
