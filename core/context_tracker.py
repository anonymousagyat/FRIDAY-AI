"""
Active Conversation Context & Topic Stacking Engine for FRIDAY.
Maintains real-time dialogue memory, active entity stack, topic shifts, and pronoun resolution.
"""

import time
import re
import os
from typing import Dict, Any, List, Optional


class TopicFrame:
    """Represents an active or background conversational topic/entity."""
    def __init__(self, topic_type: str, entity: str, details: str = "", path: str = ""):
        self.topic_type = topic_type  # 'game', 'folder', 'app', 'music', 'system', 'general'
        self.entity = entity
        self.details = details
        self.path = path
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 1

    def touch(self, details: str = "", path: str = ""):
        self.last_accessed = time.time()
        self.access_count += 1
        if details:
            self.details = details
        if path:
            self.path = path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_type": self.topic_type,
            "entity": self.entity,
            "details": self.details,
            "path": self.path,
            "age_seconds": round(time.time() - self.last_accessed, 1),
            "access_count": self.access_count
        }


class ContextTracker:
    """
    Tracks dialogue turns, active topics, topic shifts, and resolves references.
    Provides real-time dynamic context to Gemini Live Bidi sessions.
    """

    def __init__(self, max_history: int = 20, max_topics: int = 6):
        self.max_history = max_history
        self.max_topics = max_topics
        self.topic_stack: List[TopicFrame] = []
        self.dialogue_history: List[Dict[str, Any]] = []
        self.current_turn = 0

    # =========================================================================
    # TOPIC STACK & CONTEXT SHIFTING
    # =========================================================================

    def push_topic(self, topic_type: str, entity: str, details: str = "", path: str = "") -> Optional[TopicFrame]:
        """
        Pushes a new topic to the top of the stack, or promotes it if already present.
        Allows topic shifting while keeping previous topics alive in the stack.
        """
        clean_entity = entity.strip()
        if not clean_entity:
            return None

        # Check if already in stack (case-insensitive)
        for i, frame in enumerate(self.topic_stack):
            if frame.entity.lower() == clean_entity.lower() or (path and frame.path and frame.path.lower() == path.lower()):
                frame.touch(details, path)
                # Move to top of stack
                self.topic_stack.pop(i)
                self.topic_stack.insert(0, frame)
                return frame

        # Create new frame and push to top
        new_frame = TopicFrame(topic_type, clean_entity, details, path)
        self.topic_stack.insert(0, new_frame)

        # Enforce max topic stack size
        if len(self.topic_stack) > self.max_topics:
            self.topic_stack = self.topic_stack[:self.max_topics]

        return new_frame

    def get_active_topic(self) -> Optional[TopicFrame]:
        """Returns the currently active topic (top of stack)."""
        return self.topic_stack[0] if self.topic_stack else None

    def get_topic_by_type(self, topic_type: str) -> Optional[TopicFrame]:
        """Finds the most recent topic of a specific type in the stack."""
        for frame in self.topic_stack:
            if frame.topic_type.lower() == topic_type.lower():
                return frame
        return None

    def find_topic(self, keyword: str) -> Optional[TopicFrame]:
        """Finds any topic in the stack matching a keyword."""
        q = keyword.lower().strip()
        for frame in self.topic_stack:
            if q in frame.entity.lower() or q in frame.details.lower() or q in frame.path.lower():
                return frame
        return None

    # =========================================================================
    # DIALOGUE RECORDING & AUTOMATIC ENTITY EXTRACTION
    # =========================================================================

    def record_turn(
        self,
        role: str,
        text: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_result: Optional[Dict[str, Any]] = None
    ):
        """Records a user or assistant dialogue turn and updates the topic stack."""
        clean_text = text.strip() if text else ""
        self.current_turn += 1

        entry = {
            "turn": self.current_turn,
            "role": role,
            "text": clean_text,
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S")
        }

        if tool_name:
            entry["tool_name"] = tool_name
            entry["tool_args"] = tool_args or {}
            entry["tool_result"] = tool_result or {}

        self.dialogue_history.append(entry)
        if len(self.dialogue_history) > self.max_history:
            self.dialogue_history = self.dialogue_history[-self.max_history:]

        # Automatic context extraction from tool executions
        if tool_name and tool_result and tool_result.get("success"):
            self._extract_tool_entities(tool_name, tool_args or {}, tool_result)

        # Automatic extraction from memory recall results
        if tool_name == 'recall_memory' and tool_result:
            matches = tool_result.get('matches') or {}
            facts = matches.get('facts') or {}
            notes = matches.get('notes') or []
            mem_blob = " ".join([str(v) for v in facts.values()] + [str(n) for n in notes])
            if mem_blob:
                self._extract_text_entities(mem_blob, "memory")

        # Automatic extraction from user or assistant text
        if clean_text:
            self._extract_text_entities(clean_text, role)

    def _extract_tool_entities(self, tool_name: str, args: dict, result: dict):
        """Extracts confirmed entities from successful tool executions."""
        if tool_name in ('list_directory', 'open_folder', 'search_files'):
            path = result.get('path') or args.get('path') or args.get('folder_name') or ''
            subfolders = result.get('subfolders') or []
            if 'games' in str(path).lower():
                for sub in subfolders:
                    if any(k in sub.lower() for k in ['call of duty', 'dark souls', 'mario', 'sleeping dogs', 'ninja', 'katana']):
                        full_sub_path = f"{path}\\{sub}" if path else sub
                        self.push_topic('game', sub, f"Local game verified in {path}", full_sub_path)

            if path:
                self.push_topic('folder', os.path.basename(path) or str(path), f"Directory verified: {path}", str(path))

        elif tool_name == 'play_youtube_music':
            q = args.get('query', '')
            if q:
                self.push_topic('music', q, "Track played on YouTube Music")

        elif tool_name in ('open_app', 'automate_steam'):
            app = args.get('app_name') or args.get('game_name') or ''
            if app:
                t_type = 'game' if tool_name == 'automate_steam' or 'game' in app.lower() else 'app'
                self.push_topic(t_type, app, f"Launched via {tool_name}")

    def _extract_text_entities(self, text: str, role: str):
        """Extracts prominent subjects from user, assistant, or memory statements."""
        t_low = text.lower()

        # Pronoun reference check: if turn is pure pronoun action, refresh active topic
        is_pronoun_ref = bool(re.search(r'\b(it|that|wo|use|usko|pehle wala|wapas|kholo|open it|chala do|chalao|start it)\b', t_low))
        if is_pronoun_ref and self.topic_stack:
            self.topic_stack[0].touch()

        # 1. Scan against local games in D:\GAMES
        games_dir = r"D:\GAMES"
        if os.path.exists(games_dir):
            try:
                for folder in os.listdir(games_dir):
                    if folder.startswith('.'):
                        continue
                    clean_folder = re.sub(r'\[.*?\]|-SteamRIP\.com', '', folder).strip()
                    words = [w for w in re.split(r'[\s\-_]+', clean_folder.lower()) if len(w) > 2 and w not in ('files', 'zip', 'definitive', 'edition', 'online')]
                    if words and all(w in t_low for w in words):
                        self.push_topic('game', clean_folder, f"Local game verified in {games_dir}", os.path.join(games_dir, folder))
                        return
                    matching_words = sum(1 for w in words if w in t_low)
                    if len(words) >= 2 and matching_words >= 2:
                        self.push_topic('game', clean_folder, f"Local game verified in {games_dir}", os.path.join(games_dir, folder))
                        return
            except Exception:
                pass

        # 2. General Game Patterns
        game_patterns = [
            r'call\s*of\s*duty(?:\s*\d+)?(?:\s*modern\s*warfare)?(?:\s*\d+)?',
            r'modern\s*warfare(?:\s*\d+)?',
            r'dark\s*souls(?:\s*remastered)?',
            r'sleeping\s*dogs',
            r'katana\s*zero',
            r'gunbrella',
            r'mark\s*of\s*the\s*ninja',
            r'mario\s*kart'
        ]
        for pat in game_patterns:
            m = re.search(pat, t_low)
            if m:
                matched = m.group(0).title()
                if 'call of duty' in matched.lower() or 'modern warfare' in matched.lower():
                    matched = "Call of Duty 4 Modern Warfare"
                    path = r"D:\GAMES\Call of Duty 4 Morden Warfare"
                else:
                    path = ""
                self.push_topic('game', matched, f"Game mentioned in dialogue ({role})", path)
                return

        # 3. Folders (requires explicit folder/dir/drive indicator or desktop/downloads)
        folder_m = re.search(r'\b(games?|movies?|downloads?|music|code|desktop)\s+(?:folder|directory|dir|drive|me|mein)\b', t_low)
        if not folder_m:
            folder_m = re.search(r'\b(desktop|downloads|recycle bin)\b', t_low)
        if folder_m:
            f_name = folder_m.group(1).title()
            p = r"D:\GAMES" if f_name.lower() in ('game', 'games') else f_name
            self.push_topic('folder', f_name, f"Folder: {f_name}", p)

    # =========================================================================
    # DYNAMIC PROMPT BUILDER FOR GEMINI LIVE
    # =========================================================================

    def get_context_prompt(self) -> str:
        """
        Generates an active topic and conversation context prompt to inject
        into FRIDAY's live session, giving her superhuman conversational memory.
        """
        if not self.topic_stack and not self.dialogue_history:
            return ""

        lines = ["\n--- REAL-TIME ACTIVE CONVERSATION CONTEXT & TOPIC STACK ---"]

        # 1. Topic Stack
        if self.topic_stack:
            lines.append("TOPIC STACK (CURRENT ACTIVE CONTEXT & PREVIOUS TOPICS):")
            for idx, frame in enumerate(self.topic_stack, 1):
                status = "[ACTIVE PRIMARY TOPIC]" if idx == 1 else f"[PREVIOUS TOPIC #{idx} - IN MEMORY]"
                desc = f"{status} Type: {frame.topic_type.upper()} | Entity: \"{frame.entity}\""
                if frame.path:
                    desc += f" | Path: {frame.path}"
                if frame.details:
                    desc += f" | Context: {frame.details}"
                lines.append(f"  {idx}. {desc}")

            lines.append("\nPRONOUN & CONTEXT RESOLUTION DIRECTIVES:")
            active = self.topic_stack[0]
            lines.append(f"- When Sir says 'it', 'that', 'wo', 'use', 'usko', 'open it up', 'chala do', 'start it', "
                         f"he is referring to: \"{active.entity}\"" + (f" located at '{active.path}'." if active.path else "."))
            lines.append("- STRICTLY NEVER ask 'Kya open karna hai?' or 'Kaunsa game?' when Sir says 'open it' or 'chalao' "
                         f"right after discussing \"{active.entity}\"! Execute action immediately on \"{active.entity}\".")
            lines.append("- If Sir shifts to a new topic (e.g. asks about something else), smoothly respond to the new topic, "
                         "while KEEPING the previous topics in the stack. If Sir later says 'wapas usi pe aao', 'remember the game', "
                         "or 'pehle wala kholo', seamlessly recall from the Topic Stack without hesitation.")

        # 2. Recent Dialogue (Last 6 turns)
        if self.dialogue_history:
            lines.append("\nRECENT CONVERSATION TURNS (LAST FEW MINUTES):")
            recent = self.dialogue_history[-8:]
            for d in recent:
                r_name = "Sir" if d["role"] == "user" else "FRIDAY"
                t_str = d.get("time_str", "")
                t_call = f" [Executed Tool: {d['tool_name']}]" if d.get("tool_name") else ""
                lines.append(f"- [{t_str}] {r_name}: {d['text']}{t_call}")

        lines.append("----------------------------------------------------------\n")
        return "\n".join(lines)


# Singleton instance
context_tracker = ContextTracker()
