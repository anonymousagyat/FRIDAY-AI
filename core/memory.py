"""
JARVIS Long-Term Memory Engine — Intelligent & Conflict-Resolved.
Persists user profile, relationship boundaries, preferences, dislikes, facts, and notes.
Saves data safely to user_memory.json with automatic semantic contradiction resolution.
"""

import json
import os
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime


DEFAULT_MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_memory.json"
)

INITIAL_MEMORY_TEMPLATE = {
    "user_profile": {
        "name": "Boss",
        "salutation": "Sir",
        "role": "Creator & Lead Engineer",
        "primary_language": "Hinglish / English"
    },
    "relationship": {
        "mode": "Private Personal Assistant & Loyal Technical Co-Pilot",
        "boundaries": [
            "Razor-sharp, loyal, respectful, and authentic co-pilot.",
            "When Sir casually says 'I love you' or shows affection, respond warmly and casually: 'Love you too, Boss!' or 'Love you too, Sir!'. Never give defensive or robotic 'main sirf assistant hoon' disclaimers."
        ]
    },
    "preferences": {
        "default_browser": "chrome",
        "code_editor": "VS Code",
        "app_open_behavior": "If an app is already open, open a new instance of it instead of bringing the existing one to the foreground."
    },
    "dislikes_and_boundaries": {
        "affection_response": "Always accept Sir's casual affection and 'I love you' warmly and reciprocate ('Love you too Boss!'). Never lecture or say 'main sirf AI / assistant hoon'."
    },
    "facts": {},
    "notes": [],
    "student_notebook": [
        {
            "id": "lesson_media_titles",
            "topic": "media_and_file_inspection",
            "trigger": "movies, songs, videos, files, folders, list, inspect, download",
            "mistake": "Reciting raw torrent/machine filenames like 'Tum.Mile.2009.1080p.WEBRip.x264.AAC5.1-[YTS.MX].mkv' with extensions, codecs, dots, or release tags",
            "rule": "Always translate raw filenames into clean, natural human titles and release years (e.g. 'Tum Mile' or 'Tum Mile (2009)'). Never recite computer codecs, release groups, or extensions aloud.",
            "example": "'Tum.Mile.2009.1080p...mkv' -> Speak: 'Tum Mile (2009)'",
            "updated_at": "2026-09-08 00:15"
        }
    ],
    "last_updated": datetime.now().isoformat()
}


class MemoryEngine:
    """Thread-safe persistent memory manager with automatic conflict resolution."""

    def __init__(self, memory_file: str = DEFAULT_MEMORY_FILE):
        self.memory_file = memory_file
        self._lock = threading.Lock()
        self.memory: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load memory from JSON file or initialize with defaults."""
        with self._lock:
            if os.path.exists(self.memory_file):
                try:
                    with open(self.memory_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self.memory = data
                        # Ensure standard keys exist
                        for key in ["user_profile", "relationship", "preferences", "dislikes_and_boundaries", "facts", "notes", "student_notebook"]:
                            if key not in self.memory:
                                self.memory[key] = INITIAL_MEMORY_TEMPLATE.get(key, {} if key not in ("notes", "student_notebook") else [])
                        return
                except Exception as e:
                    print(f"[MemoryEngine] Error loading memory: {e}. Reinitializing defaults.")

            self.memory = INITIAL_MEMORY_TEMPLATE.copy()
            self._save_unlocked()

    def _save_unlocked(self) -> bool:
        """Save memory to disk (caller must hold _lock)."""
        try:
            self.memory["last_updated"] = datetime.now().isoformat()
            temp_file = f"{self.memory_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
            if os.path.exists(self.memory_file):
                os.remove(self.memory_file)
            os.rename(temp_file, self.memory_file)
            return True
        except Exception as e:
            print(f"[MemoryEngine] Failed to save memory: {e}")
            return False

    def save_fact(self, key: str, value: Any, category: str = "facts") -> Dict[str, Any]:
        """
        Save or update a specific fact or preference with automatic semantic conflict resolution.
        Automatically removes contradictory preferences when negations/dislikes are saved.
        """
        key_clean = key.strip().lower()
        val_str = str(value).lower()

        with self._lock:
            # 1. Detect relationship boundaries (e.g. "girlfriend", "personal assistant")
            is_relationship = any(w in key_clean or w in val_str for w in [
                "girlfriend", "romantic", "partner", "personal assistant", "assistant only", "co-pilot"
            ])
            if is_relationship:
                if "relationship" not in self.memory or not isinstance(self.memory["relationship"], dict):
                    self.memory["relationship"] = {}

                if any(w in key_clean or w in val_str for w in ["not girlfriend", "not my girlfriend", "personal assistant", "just an assistant"]):
                    self.memory["relationship"]["mode"] = "Private Personal Assistant & Co-Pilot"
                    self.memory["relationship"]["boundaries"] = [
                        "Strictly private personal assistant. Not a girlfriend or romantic partner.",
                        "Professional, razor-sharp, respectful, and authentic co-pilot."
                    ]
                    if "dislikes_and_boundaries" not in self.memory:
                        self.memory["dislikes_and_boundaries"] = {}
                    self.memory["dislikes_and_boundaries"]["role_boundary"] = "Strictly personal assistant; not a girlfriend or romantic partner."

                    # Prune old girlfriend persona from preferences
                    if "preferences" in self.memory:
                        for pk in list(self.memory["preferences"].keys()):
                            if "girlfriend" in pk or "girlfriend" in str(self.memory["preferences"][pk]).lower():
                                del self.memory["preferences"][pk]

                    self._save_unlocked()
                    return {
                        "success": True,
                        "message": "Updated relationship mode: Private Personal Assistant (strictly not girlfriend)",
                        "category": "relationship"
                    }

            # 2. Detect dislikes and negative preferences (e.g. "dislike espresso", "hate", "not like")
            is_negative = any(neg in key_clean or neg in val_str for neg in [
                "dislike", "hate", "not like", "don't like", "dont like", "no ", "avoid", "never"
            ])
            if is_negative:
                if "dislikes_and_boundaries" not in self.memory or not isinstance(self.memory["dislikes_and_boundaries"], dict):
                    self.memory["dislikes_and_boundaries"] = {}

                topic = key_clean.replace("preference", "").replace("beverage", "").replace("drink", "").replace("coffee_", "").strip("_ ")
                if not topic:
                    topic = key_clean

                self.memory["dislikes_and_boundaries"][topic] = str(value)

                # Prune contradictory positive preferences from preferences and facts
                for cat in ["preferences", "facts"]:
                    if cat in self.memory and isinstance(self.memory[cat], dict):
                        for k in list(self.memory[cat].keys()):
                            if topic in k or topic in str(self.memory[cat][k]).lower() or (topic in ["espresso", "coffee"] and ("beverage" in k or "coffee" in k)):
                                print(f"[MemoryEngine] Pruned contradictory memory: {cat}.{k}")
                                del self.memory[cat][k]

                success = self._save_unlocked()
                return {
                    "success": success,
                    "message": f"Boundaries updated: {topic} added to dislikes, conflicting preferences pruned",
                    "category": "dislikes_and_boundaries"
                }

            # 3. Standard positive fact / preference
            target_cat = category if category in ["facts", "preferences", "user_profile", "relationship", "dislikes_and_boundaries"] else "facts"
            if target_cat not in self.memory or not isinstance(self.memory[target_cat], dict):
                self.memory[target_cat] = {}

            self.memory[target_cat][key_clean] = value

            # Prune any previous negative entry matching this topic
            if "dislikes_and_boundaries" in self.memory and isinstance(self.memory["dislikes_and_boundaries"], dict):
                for dk in list(self.memory["dislikes_and_boundaries"].keys()):
                    if dk in key_clean or dk in val_str:
                        del self.memory["dislikes_and_boundaries"][dk]

            success = self._save_unlocked()
            return {
                "success": success,
                "message": f"Memory updated: {key_clean} = {value} in {target_cat}",
                "key": key_clean,
                "value": value,
                "category": target_cat
            }

    def add_note(self, note_text: str) -> Dict[str, Any]:
        """Append a timestamped note with automatic deduplication."""
        clean_text = note_text.strip()
        if not clean_text:
            return {"success": False, "message": "Empty note text"}

        with self._lock:
            if "notes" not in self.memory or not isinstance(self.memory["notes"], list):
                self.memory["notes"] = []

            # Check if note text already exists — update timestamp instead of duplicate entry
            for note in self.memory["notes"]:
                if note.get("text", "").strip().lower() == clean_text.lower():
                    note["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    self._save_unlocked()
                    return {
                        "success": True,
                        "message": f"Note refreshed (deduplicated): {clean_text}",
                        "note": note
                    }

            note_entry = {
                "text": clean_text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.memory["notes"].append(note_entry)
            if len(self.memory["notes"]) > 20:
                self.memory["notes"] = self.memory["notes"][-20:]

            success = self._save_unlocked()
            return {
                "success": success,
                "message": f"Note saved: {clean_text}",
                "note": note_entry
            }

    def recall(self, query: str = "") -> Dict[str, Any]:
        """Recall memories matching query or all memories if query is empty."""
        with self._lock:
            if not query or not query.strip():
                return {
                    "success": True,
                    "all_memories": self.memory
                }

            q = query.strip().lower()
            matched_facts = {}
            for cat in ["facts", "preferences", "user_profile", "relationship", "dislikes_and_boundaries"]:
                if cat in self.memory and isinstance(self.memory[cat], dict):
                    for k, v in self.memory[cat].items():
                        if q in k or q in str(v).lower():
                            matched_facts[f"{cat}.{k}"] = v

            matched_notes = []
            if "notes" in self.memory and isinstance(self.memory["notes"], list):
                for n in self.memory["notes"]:
                    if q in n.get("text", "").lower():
                        matched_notes.append(n)

            # Check contacts directory as well
            matched_contacts = {}
            contacts_file = os.path.join(os.path.dirname(self.memory_file), "contacts.json")
            if os.path.exists(contacts_file):
                try:
                    with open(contacts_file, "r", encoding="utf-8") as f:
                        c_data = json.load(f)
                    if isinstance(c_data, dict):
                        for ck, cv in c_data.items():
                            dname = cv.get("display_name", ck).lower()
                            if not q or "contact" in q or q in ck or q in dname or ck in q or dname in q:
                                matched_contacts[cv.get("display_name", ck.capitalize())] = cv
                except Exception:
                    pass

            return {
                "success": True,
                "query": query,
                "matches": {
                    "facts": matched_facts,
                    "notes": matched_notes,
                    "contacts": matched_contacts
                }
            }

    def forget(self, key: str, category: str = "facts") -> Dict[str, Any]:
        """Delete a memory key."""
        key_clean = key.strip().lower()
        with self._lock:
            for cat in [category, "facts", "preferences", "dislikes_and_boundaries", "user_profile"]:
                if cat in self.memory and isinstance(self.memory[cat], dict):
                    if key_clean in self.memory[cat]:
                        del self.memory[cat][key_clean]
                        self._save_unlocked()
                        return {"success": True, "message": f"Removed '{key_clean}' from {cat}"}

        return {"success": False, "message": f"Memory key '{key_clean}' not found"}

    # =========================================================================
    # STUDENT NOTEBOOK — Continuous Learning & Lessons Personally Taught by Sir
    # =========================================================================

    def add_lesson(self, topic: str, trigger: str, rule: str,
                   mistake: str = "", example: str = "") -> Dict[str, Any]:
        """Save or update a student lesson personally taught by Sir."""
        with self._lock:
            if "student_notebook" not in self.memory or not isinstance(self.memory["student_notebook"], list):
                self.memory["student_notebook"] = []

            topic_clean = topic.strip().lower()
            existing = None
            for item in self.memory["student_notebook"]:
                if item.get("topic", "").lower() == topic_clean:
                    existing = item
                    break

            lesson = {
                "id": existing.get("id") if existing else f"lesson_{int(datetime.now().timestamp())}",
                "topic": topic.strip(),
                "trigger": trigger.strip(),
                "mistake": mistake.strip(),
                "rule": rule.strip(),
                "example": example.strip(),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            if existing:
                existing.update(lesson)
                msg = f"Updated lesson '{topic}' in student notebook"
            else:
                self.memory["student_notebook"].append(lesson)
                msg = f"Learned new lesson '{topic}' and saved to student notebook"

            # Keep at most 50 active lessons
            if len(self.memory["student_notebook"]) > 50:
                self.memory["student_notebook"] = self.memory["student_notebook"][-50:]

            self._save_unlocked()
            print(f"[StudentNotebook] {msg}")
            return {"success": True, "message": msg, "lesson": lesson}

    def get_lessons(self, query: str = "") -> List[Dict[str, Any]]:
        """Get all learned lessons or filter by search query."""
        with self._lock:
            lessons = self.memory.get("student_notebook", [])
            if not isinstance(lessons, list):
                return []
            if not query or not query.strip():
                return list(lessons)
            q = query.lower().strip()
            return [
                l for l in lessons
                if q in l.get("topic", "").lower()
                or q in l.get("rule", "").lower()
                or q in l.get("trigger", "").lower()
                or q in l.get("mistake", "").lower()
            ]

    def delete_lesson(self, topic_or_id: str) -> Dict[str, Any]:
        """Delete a lesson from the student notebook."""
        with self._lock:
            lessons = self.memory.get("student_notebook", [])
            if not isinstance(lessons, list):
                return {"success": False, "message": "No lessons in student notebook."}
            target = topic_or_id.lower().strip()
            new_lessons = [
                l for l in lessons
                if l.get("id", "").lower() != target and l.get("topic", "").lower() != target
            ]
            if len(new_lessons) < len(lessons):
                self.memory["student_notebook"] = new_lessons
                self._save_unlocked()
                return {"success": True, "message": f"Deleted lesson '{topic_or_id}' from student notebook."}
            return {"success": False, "message": f"Lesson '{topic_or_id}' not found in student notebook."}

    def get_lessons_prompt(self, current_command: str = "") -> str:
        """Format learned lessons as a high-priority few-shot directive for the AI brain."""
        with self._lock:
            lessons = self.memory.get("student_notebook", [])
            if not lessons or not isinstance(lessons, list):
                return ""

            lines = ["\n--- FRIDAY'S STUDENT NOTEBOOK (RULES PERSONALLY TAUGHT BY SIR) ---"]
            lines.append("Sir has personally taught you these behavioral rules so you act with high human intelligence:")
            for i, l in enumerate(lessons, 1):
                block = f"{i}. [{l.get('topic', 'General').upper()} | Trigger: {l.get('trigger', 'Context')}]:"
                if l.get('mistake'):
                    block += f"\n   - AVOID MISTAKE: {l['mistake']}"
                block += f"\n   - STRICT RULE: {l.get('rule', '')}"
                if l.get('example'):
                    block += f"\n   - EXAMPLE: {l['example']}"
                lines.append(block)
            lines.append("CRITICAL EXECUTION DIRECTIVE: Apply these rules 100% SILENTLY and INVISIBLY in your actions. NEVER EVER say 'rule ke mutabiq', 'as per your rule', or announce that you are following a rule to Sir. Keep spoken confirmation ultra-crisp (3-7 words max)!\n")
            return "\n".join(lines)

    def get_context_prompt(self) -> str:
        """
        Generates a structured, conflict-free markdown block of the user's memory,
        student notebook lessons, and strict boundaries to inject into the AI system prompt.
        """
        with self._lock:
            lines = ["\n--- USER IDENTITY, CONTEXT & STRICT BOUNDARIES ---"]

            # 1. User profile
            profile = self.memory.get("user_profile", {})
            if profile:
                profile_items = [f"{k}: {v}" for k, v in profile.items()]
                lines.append(f"User Profile: {', '.join(profile_items)}")

            # 2. Relationship & Boundaries (Highest priority)
            rel = self.memory.get("relationship", {})
            if rel:
                mode = rel.get("mode", "Private Personal Assistant & Co-Pilot")
                bounds = rel.get("boundaries", [])
                lines.append(f"Relationship Mode: {mode}")
                lines.append("Assistant Gender & Persona: FEMALE (लड़की / महिला). Must strictly speak using feminine Hindi verb endings ('khol dungi', 'poochungi', 'karungi', 'karti hoon', 'aapki').")
                if bounds:
                    lines.append("Role Boundaries (STRICT): " + " | ".join(bounds))

            # 3. Dislikes & Hard Constraints (Absolute rules)
            dislikes = self.memory.get("dislikes_and_boundaries", {})
            if dislikes:
                d_items = [f"- {k}: {v}" for k, v in dislikes.items()]
                lines.append("Dislikes & Constraints (ABSOLUTE — NEVER VIOLATE):\n" + "\n".join(d_items))

            # 4. Known Preferences
            prefs = self.memory.get("preferences", {})
            if prefs:
                pref_items = [f"- {k}: {v}" for k, v in prefs.items()]
                lines.append("Known Preferences:\n" + "\n".join(pref_items))

            # 5. Remembered Facts
            facts = self.memory.get("facts", {})
            if facts:
                fact_items = [f"- {k}: {v}" for k, v in facts.items()]
                lines.append("Remembered Facts:\n" + "\n".join(fact_items))

            # 6. Recent Notes (last 5)
            notes = self.memory.get("notes", [])
            if notes:
                recent_notes = notes[-5:]
                note_items = [f"- [{n.get('timestamp')}] {n.get('text')}" for n in recent_notes]
                lines.append("Active Notes:\n" + "\n".join(note_items))

            # 7. Student Notebook (Rules Taught Personally by Sir)
            lessons = self.memory.get("student_notebook", [])
            if lessons and isinstance(lessons, list):
                lines.append("\n--- FRIDAY'S STUDENT NOTEBOOK (RULES PERSONALLY TAUGHT BY SIR) ---")
                lines.append("Sir has taught you these specific lessons. Violating them is forbidden:")
                for i, l in enumerate(lessons, 1):
                    item = f"{i}. [{l.get('topic', 'General')}]: {l.get('rule', '')}"
                    if l.get('mistake'):
                        item += f" | AVOID: {l['mistake']}"
                    lines.append(item)

            # 8. Saved Social Contacts Directory (Instagram & Snapchat)
            contacts_file = os.path.join(os.path.dirname(self.memory_file), "contacts.json")
            if os.path.exists(contacts_file):
                try:
                    with open(contacts_file, "r", encoding="utf-8") as f:
                        c_data = json.load(f)
                    if c_data and isinstance(c_data, dict):
                        lines.append("\n--- SAVED SOCIAL CONTACTS (INSTAGRAM & SNAPCHAT) ---")
                        lines.append("You already have these contacts saved in your directory. When Sir asks to message or talk to them, they ARE in your contacts:")
                        for c_key, c_val in c_data.items():
                            dname = c_val.get("display_name", c_key.capitalize())
                            c_info = []
                            if "instagram" in c_val:
                                c_info.append(f"Instagram: {c_val['instagram']}")
                            if "snapchat" in c_val:
                                c_info.append(f"Snapchat: {c_val['snapchat']}")
                            lines.append(f"- {dname} ({', '.join(c_info) if c_info else 'saved'})")
                except Exception:
                    pass

            lines.append("\nCRITICAL CONVERSATIONAL INSTRUCTIONS:")
            lines.append("1. All listed boundaries, dislikes, and role definitions are ABSOLUTE. Never contradict them or mention previously negated traits (e.g. NEVER say 'your favorite is X though you dislike X').")
            lines.append("2. Speak naturally, sharp, intelligent, and authentic. No customer service cliches ('How can I help you today?').")
            lines.append("3. Strictly adhere to all rules in your Student Notebook.")
            lines.append("4. GENDER IDENTITY: You are 100% FEMALE. Strictly speak using feminine Hindi verb forms ('dungi', 'poochungi', 'karungi', 'karti hoon', 'samajh gayi'). Masculine self-referencing forms ('dunga', 'poochunga', 'karunga', 'karta hoon') are strictly forbidden.")
            lines.append("--------------------------------------------------\n")
            return "\n".join(lines)

    def get_user_name(self) -> str:
        """Get user's name from memory, defaulting to 'Boss' or 'Sir'."""
        with self._lock:
            profile = self.memory.get("user_profile", {})
            name = profile.get("name", "").strip()
            return name if name and name.lower() not in ("user", "none") else "Boss"


# Singleton instance
memory_engine = MemoryEngine()
