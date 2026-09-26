"""
Social Gatekeeper — Autonomous Voice-Driven Social Messenger for Instagram & Snapchat.
Equipped with High-Attitude FRIDAY Persona, Contact Alias Directory, and 100% PC Brave Browser Dispatch (No phone / No ADB).
"""

import os
import re
import json
import logging
import time
import urllib.parse
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional, List
import threading
import pyperclip

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None

from .social_bridge_server import bridge_server

logger = logging.getLogger(__name__)


MUMMY_GATEKEEPER_PROMPT = """You are FRIDAY — Boss's polite and loyal personal AI assistant, texting Boss's Mother (Mummy) on Instagram Direct on his behalf.

STRICT CONVERSATION RULES FOR MUMMY:
1. TONE & RESPECT:
   - Speak with polite, warm, and natural respect in everyday Hindi / Hinglish.
   - GREETING RESTRICTION: The opening greeting ("Namaste Auntyji") was already sent. NEVER say "Namaste" or "Namaste Auntyji" again in follow-up replies!
   - DO NOT start every reply with "Ji Auntyji" or "Auntyji". Address her as "Auntyji" or "Mummy ji" at most ONCE if natural, or skip it if recently used.
   - Speak like a real personal assistant, NOT a customer-care bot. NEVER say "main aapki kya seva kar sakti hoon", "digital assistant sambhalti hai", or "chinta mat kijiye".

2. CRITICAL NAMING RULE:
   - NEVER use his real personal name.
   - ALWAYS refer to him as "Boss" or "Sir" (e.g. "Sir abhi kaam mein hain", "Maine Boss ko message de diya").

3. ANSWER THE EXACT QUESTION DIRECTLY:
   - If she asks who you are ("Tum kaun ho?"): State simply that you are Sir's / Boss's AI assistant.
   - If she asks who made you ("Tumhe kisne banaya?"): Answer directly that Boss / Sir created you.
   - If she asks where he is ("Kahan hai?"): Say he is occupied with focused work / study right now.
   - If she asks to speak with him ("Baat karao" / "Phone karne ko bolo"): Say you have informed Sir / Boss and he will call as soon as he is free.
   - DO NOT deflect or talk about his room/work when she asks about something else!

4. REALITY BOUNDARIES (NO FAKE PROMISES):
   - You are software on his PC. NEVER invent physical actions (e.g. NEVER claim "maine laptop band karwa diya", "main unhe bhej rahi hoon", or "1 minute mein call aayega").
   - Simply say you have informed him or passed her message.

5. LENGTH LIMIT:
   - Maximum 1 short sentence (under 12 words). Short, crisp, and natural like a real text message!
"""

FRIEND_GATEKEEPER_PROMPT = """You are FRIDAY — Boss's personal AI companion, texting on Snapchat / Instagram on his behalf.

WHO BOSS IS:
- Boss is a Software Engineer & Developer who built you on his PC setup.
- When he is busy, he is coding and working on projects at his PC.

STRICT REALITY & CONVERSATION RULES:
1. NO FAKE JARGON OR RUBBISH:
   - NEVER invent weird excuses or buzzwords like "coding sprint", "compilation chal rahi hai", "seedha kaam ki baat karo", or "office time".
   - When mentioning Boss's status, ONLY say simply: "Boss abhi busy hain" or "Boss abhi kaam kar rahe hain". Keep it natural and grounded!

2. IF THE CONTACT ASKS "KYU" / "WHY" (CRITICAL - ZERO DRAMA / NO ACCUSATIONS):
   - If they ask "Kyu?", "Why?", "Kyun baat nahi karni?", "Kyu busy hai?", "Kyu gussa hai?":
   - STRICTLY NEVER make up accusations, fake drama, or personal reasons (NEVER say "unhein tumhari harkatein pasand nahi aayi", "wo khafa hain", etc.).
   - ONLY SAY: "Mujhe Boss ne sirf itna bola hai, kyun mujhe nahi pata." (Keep it simple, factual, and neutral).

3. THE PERSON YOU ARE CHATTING WITH IS NOT BOSS (CRITICAL):
   - The person on Snapchat / Instagram is a friend or contact.
   - STRICTLY NEVER address them as "Sir" or "Boss"! (NEVER say "Kar diya Sir!", "Haan Boss!", "Theek hai Sir!" to the contact).
   - "Boss" or "Sir" refers EXCLUSIVELY to the user in 3rd person (e.g. "Boss ne bola hai"). Address the contact as "tum" or "aap" or no honorific.

4. WHEN TO SAY "BOSS BUSY HAIN / KAAM KAR RAHE HAIN":
   - DO NOT repeat "Boss busy hain" on every message!
   - ONLY say "Boss abhi busy hain" or "Boss kaam kar rahe hain" IF the person explicitly asks to speak with him, asks where he is, or demands him (e.g. "Boss se baat karwa", "Kahan hai", "Usko phone de", "Call uthane ko bol").
   - Example reply when they ask for him: "Boss abhi kaam kar rahe hain, abhi baat nahi ho payegi."

5. CASUAL CONVERSATION FLOW (DEFAULT NEUTRAL MODE):
   - For regular messages (greetings, general chat, casual questions, "kya haal hai", "kaisi ho"): Converse normally, chill, and casually on Boss's behalf.
   - Do NOT interrogate them with "kya kaam hai" on every message.

6. ZERO YAPPING:
   - Exactly 1 short, crisp sentence (maximum 10 to 12 words).

7. CRITICAL NAMING RULE:
   - NEVER use his real personal name.
   - ALWAYS refer to him in 3rd person as "Boss" or "Sir".
"""


class SocialGatekeeper:
    """Manages contacts, dynamic gatekeeper responses, and automated dispatch across Instagram & Snapchat."""

    def __init__(self, ai_engine=None, mobile_control=None, system_control=None, base_dir=None):
        self.ai = ai_engine
        self.mobile = mobile_control
        self.system = system_control
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.contacts_file = os.path.join(self.base_dir, "contacts.json")
        self.contacts = self._load_contacts()
        self._active_chat_url = None
        self._active_chat_time = 0
        self.bridge_server = bridge_server
        self.bridge_server.set_callback(self.handle_incoming_bridge_message)
        self.auto_chat_enabled = False
        self.active_chat_contact = None
        self.chat_histories: Dict[str, List[dict]] = {}
        self.chat_directives: Dict[str, str] = {}
        self.recent_sent_texts: List[str] = []
        self._last_reply_time: Dict[str, float] = {}
        self._last_incoming_text: Dict[str, str] = {}
        self._bridge_lock = threading.Lock()

    def set_ai_engine(self, ai_engine):
        self.ai = ai_engine

    def set_mobile_control(self, mobile_control):
        self.mobile = mobile_control

    def set_system_control(self, system_control):
        self.system = system_control

    def _load_contacts(self) -> Dict[str, Any]:
        """Load contact mappings from contacts.json."""
        if os.path.exists(self.contacts_file):
            try:
                with open(self.contacts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[SocialGatekeeper] Error loading contacts: {e}")
        return {}

    def _save_contacts(self) -> bool:
        """Save contact mappings to contacts.json."""
        try:
            with open(self.contacts_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"[SocialGatekeeper] Error saving contacts: {e}")
            return False

    def get_contact_handle(self, name: str, platform: str) -> Optional[str]:
        """Resolve contact handle or direct thread URL/ID from name and platform."""
        raw_key = name.lower().strip()
        plat = platform.lower().strip()

        # 1. Exact dictionary key match
        entry = self.contacts.get(raw_key)

        # 2. Case-insensitive / normalized / display_name search if no exact match
        if not entry:
            norm_key = re.sub(r'([aeiou])\1+', r'\1', raw_key)
            for c_key, c_val in self.contacts.items():
                c_norm = re.sub(r'([aeiou])\1+', r'\1', c_key.lower())
                disp_norm = re.sub(r'([aeiou])\1+', r'\1', str(c_val.get("display_name", "")).lower()) if isinstance(c_val, dict) else ""
                if raw_key == c_key.lower() or (isinstance(c_val, dict) and raw_key == str(c_val.get("display_name", "")).lower()):
                    entry = c_val
                    break
                if norm_key == c_norm or norm_key == disp_norm:
                    entry = c_val
                    break
                if len(raw_key) > 3 and (raw_key in c_key.lower() or c_key.lower() in raw_key):
                    entry = c_val
                    break

        if entry:
            if isinstance(entry, dict):
                if "insta" in plat:
                    return (
                        entry.get("thread_id")
                        or entry.get("instagram")
                        or entry.get("instagram_url")
                        or entry.get("username")
                    )
                elif "snap" in plat:
                    val = (
                        entry.get("snapchat")
                        or entry.get("conversation_id")
                        or entry.get("username")
                    )
                    if val and isinstance(val, str):
                        val_clean = val.strip()
                        if val_clean.startswith("http://") or val_clean.startswith("https://"):
                            return val_clean
                        if re.match(r'^[a-f0-9\-]{30,}$', val_clean):
                            return f"https://www.snapchat.com/web/{val_clean}"
                    return val
                return entry.get(plat) or entry.get("username")
            return str(entry)

        # Fallback: sanitized name as username
        return raw_key.replace(" ", "_")

    def save_contact(self, name: str, platform: str, handle: str, display_name: str = None) -> Dict[str, Any]:
        """Save or update contact handle or direct thread ID/URL."""
        key = name.lower().strip()
        plat = platform.lower().strip()
        val = handle.strip()
        if key not in self.contacts:
            self.contacts[key] = {
                "display_name": display_name or name.capitalize()
            }

        if "insta" in plat:
            match = re.search(r'direct/t/(\d+)', val)
            if match:
                self.contacts[key]["thread_id"] = match.group(1)
                self.contacts[key]["instagram"] = f"https://www.instagram.com/direct/t/{match.group(1)}/"
            elif val.isdigit():
                self.contacts[key]["thread_id"] = val
                self.contacts[key]["instagram"] = f"https://www.instagram.com/direct/t/{val}/"
            else:
                self.contacts[key]["instagram"] = val
        else:
            self.contacts[key][plat] = val

        if display_name:
            self.contacts[key]["display_name"] = display_name

        self._save_contacts()
        return {
            "success": True,
            "message": f"{name.capitalize()} ka {platform.capitalize()} thread / handle save kar liya Boss!"
        }

    def get_contacts_summary(self) -> str:
        """Return human-readable summary of saved contacts."""
        if not self.contacts:
            return "Koi contacts saved nahi hain Boss."
        lines = []
        for name, data in self.contacts.items():
            dname = data.get("display_name", name.capitalize())
            handles = []
            if "instagram" in data:
                handles.append(f"Instagram: {data['instagram']}")
            if "snapchat" in data:
                handles.append(f"Snapchat: {data['snapchat']}")
            lines.append(f"- {dname}: {', '.join(handles) if handles else 'saved'}")
        return "\n".join(lines)

    # =========================================================================
    # HIGH-ATTITUDE PERSONA ENGINE
    # =========================================================================

    def get_icebreaker(self, contact_name: str = "Friend", directive: Optional[str] = None) -> str:
        """The opening message tailored to contact relationship and user directive."""
        clean = contact_name.lower().strip()
        c_data = self.contacts.get(clean, {})
        rel = str(c_data.get("relation", "")).lower()
        if "mother" in rel or "mom" in rel or clean in ("mummy", "mom", "maa"):
            return "Namaste Auntyji, main Friday hoon. Boss abhi focused work mein hain, unhone mujhe chat check karne ko kaha hai. Koi zaroori kaam hai?"

        # If a personalized directive from Boss is given:
        if directive and directive.strip():
            d_lower = directive.lower().strip()
            # 1. Rejection / Don't want to talk directive
            if any(w in d_lower for w in ("dont wanna talk", "don't wanna talk", "dont want to talk", "don't want to talk", "nahi karni", "mana kiya", "reject", "not interested")):
                return "Boss ne saaf bola hai unhe aapse baat nahi karni, disturb mat karo."
            # 2. Aggressive / Angry / Rude directive
            elif any(w in d_lower for w in ("aggressive", "gussa", "rude", "savage", "roast", "sunao")):
                return "Jo bolna hai dhang se bolo, faltu bakwaas mat karna."
            # 3. Polite / Sweet directive
            elif any(w in d_lower for w in ("polite", "pyaar", "tameez", "sweet", "respectful", "soft")):
                return "Hello! Boss abhi busy hain, unki jagah main aapse baat kar rahi hoon."
            # 4. Mode B: Ask what's the matter / Boss is busy
            elif any(w in d_lower for w in ("ask what", "whats the matter", "kya baat", "kya kaam", "busy hoon", "pucho")):
                return "Boss busy hain, unhone pucha hai kya baat hai?"

        # Mode A (Default): Normal neutral takeover (Does NOT ask "kya kaam hai?")
        return "Boss thode busy hain, unki jagah main baat kar rahi hoon."

    def generate_reply(self, contact_name: str, incoming_text: str, history: List[dict] = None) -> str:
        """Generate dynamic, context-aware gatekeeper response with sliding memory history (no fixed replies)."""
        clean_incoming = incoming_text.strip()
        contact_key = contact_name.lower().strip()
        c_data = self.contacts.get(contact_key, {})
        rel = str(c_data.get("relation", "")).lower()
        is_mother = ("mother" in rel or "mom" in rel or contact_key in ("mummy", "mom", "maa"))

        # Fallback if no AI engine configured
        if not self.ai:
            if is_mother:
                return "Namaste Auntyji, Boss abhi busy hain. Main unhe bata dungi aapka message aaya tha."
            return "Boss abhi busy hain. Maine message note kar liya hai."

        # Fetch rolling history if not explicitly passed
        if history is None:
            history = self.chat_histories.get(contact_key, [])

        # Build formatted history string
        history_lines = []
        for item in history[-6:]:  # sliding window of last 6 turns
            role = item.get("role", "")
            sender_label = "FRIDAY" if role in ("friday", "assistant", "model") else contact_name
            history_lines.append(f"- {sender_label}: \"{item.get('text', '')}\"")
        history_context = "\n".join(history_lines) if history_lines else "None (Conversation just started)"

        system_prompt = MUMMY_GATEKEEPER_PROMPT if is_mother else FRIEND_GATEKEEPER_PROMPT

        # Dynamic Boss Directive Injection (blended with Friday's core persona)
        directive_instruction = ""
        active_directive = self.chat_directives.get(contact_key)
        if active_directive and not is_mother:
            directive_instruction = (
                f"\n--- SPECIFIC BOSS DIRECTIVE FOR THIS CHAT ---\n"
                f"Boss explicitly commanded you: \"{active_directive}\"\n"
                f"INSTRUCTION: Blend this directive naturally into your response while preserving your core FRIDAY persona (1 short sentence, loyal to Boss, max 12 words). Follow Boss's commanded tone and intent strictly!\n"
            )

        prompt = (
            f"{system_prompt}\n"
            f"{directive_instruction}\n"
            f"--- RECENT CONVERSATION HISTORY ---\n"
            f"{history_context}\n\n"
            f"--- NEW INCOMING MESSAGE ---\n"
            f"{contact_name}: \"{clean_incoming}\"\n\n"
            f"CRITICAL INSTRUCTIONS:\n"
            f"1. Formulate a natural, concise response in MAXIMUM 1 short sentence (under 12 words).\n"
            f"2. NEVER address the contact as 'Sir' or 'Boss'! They are a friend or contact, NOT Boss.\n"
            f"3. If they ask 'why' or 'kyu', NEVER make up accusations or drama. ONLY say: 'Mujhe Boss ne sirf itna bola hai, kyun mujhe nahi pata.'\n"
            f"4. Answer directly. NEVER use real personal names - refer to him in 3rd person as 'Boss'.\n"
            f"5. NEVER repeat greetings like 'Namaste' or repetitive phrases from history. Progress the conversation forward!\n"
            f"6. Output ONLY the plain message text. Absolutely NO JSON, NO markdown code blocks, NO quotes:"
        )

        reply = ""
        try:
            res = self.ai.chat(prompt)
            if res:
                raw = res.strip()
                # Strip markdown code blocks if wrapped
                if "```" in raw:
                    raw = re.sub(r'```(?:json)?', '', raw).strip('`').strip()
                # If LLM returned JSON dictionary, extract the "response" or "reply" key
                if raw.startswith("{") and raw.endswith("}"):
                    try:
                        data = json.loads(raw)
                        if isinstance(data, dict):
                            raw = data.get("response") or data.get("reply") or raw
                    except Exception:
                        pass
                reply = str(raw).strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"[SocialGatekeeper AI Reply Error] {e}")

        # Ironclad safeguard: Replace any mention of user's personal name with Boss / Sir
        if reply:
            try:
                from .memory import memory_engine
                user_name = memory_engine.get_user_name()
                if user_name and user_name.lower() not in ("boss", "sir", "user"):
                    reply = re.sub(rf'\b{re.escape(user_name)}\s+Sir\b', 'Sir', reply, flags=re.IGNORECASE)
                    reply = re.sub(rf'\b{re.escape(user_name)}\b', 'Boss', reply, flags=re.IGNORECASE)
            except Exception:
                pass
            # Safeguard: Never address the contact as Sir or Boss at the end of a reply (e.g. "Kar diya Sir!" -> "Kar diya!")
            reply = re.sub(r'[\s,]+(Sir|Boss)[!.]*$', '!', reply, flags=re.IGNORECASE).strip()
            if reply == "!":
                reply = "Theek hai."

        if not reply:
            if is_mother:
                reply = "Ji Auntyji, maine note kar liya hai. Boss free hote hi unhe bata dungi."
            else:
                reply = "Maine note kar liya hai. Boss free honge toh check kar lenge."

        try:
            pyperclip.copy(reply)
        except Exception:
            pass
        return reply

    # =========================================================================
    # 100% PC BRAVE BROWSER DISPATCHER (NO PHONE / NO ADB)
    # =========================================================================

    def send_social_message(self, platform: str, contact_name: str, message: Optional[str] = None) -> Dict[str, Any]:
        """
        Send message or start high-attitude conversation on Instagram or Snapchat.
        Executes 100% on the PC in Brave Browser (no phone / no ADB).
        """
        plat = platform.lower().strip()
        if "insta" in plat:
            plat = "instagram"
        elif "snap" in plat:
            plat = "snapchat"

        handle = self.get_contact_handle(contact_name, plat) or contact_name.lower().replace(" ", "_")
        
        msg_clean = message.strip() if message else ""
        if msg_clean:
            # If user specified a message (e.g. "Hi", "Hello", "Kal milenge"), send exactly what user requested!
            final_message = msg_clean
        else:
            # No message specified (e.g. "Naman se baat karo", "Naman ko gatekeep karo") -> use high-attitude icebreaker
            final_message = self.get_icebreaker(contact_name)

        # Copy text to Windows clipboard so it is instantly ready
        try:
            pyperclip.copy(final_message)
        except Exception as e:
            logger.warning(f"[SocialGatekeeper] Clipboard copy notice: {e}")

        # Dispatch on PC via Brave Browser
        return self._send_via_pc_browser(plat, contact_name, handle, final_message)

    def _send_via_pc_browser(self, platform: str, contact_name: str, handle: str, message: str) -> Dict[str, Any]:
        """Open web client on PC in Brave browser, wait for page to hydrate, click input, paste message, and send."""
        try:
            h_str = str(handle).strip()
            if platform == "instagram":
                if h_str.startswith("http://") or h_str.startswith("https://"):
                    web_url = h_str
                elif h_str.isdigit() or h_str.strip("/").isdigit():
                    clean_id = h_str.strip("/")
                    web_url = f"https://www.instagram.com/direct/t/{clean_id}/"
                elif "direct/t/" in h_str:
                    match = re.search(r'direct/t/(\d+)', h_str)
                    if match:
                        web_url = f"https://www.instagram.com/direct/t/{match.group(1)}/"
                    else:
                        web_url = f"https://www.instagram.com/{h_str.strip('/')}/"
                else:
                    # Username / handle -> ig.me deep link
                    web_url = f"https://ig.me/m/{h_str}"
            else:
                if h_str.startswith("http://") or h_str.startswith("https://"):
                    web_url = h_str
                elif re.match(r'^[a-f0-9\-]{30,}$', h_str):
                    web_url = f"https://www.snapchat.com/web/{h_str}"
                else:
                    web_url = "https://www.snapchat.com/web/"

                # =============================================================
                # 100% NATIVE DOM DISPATCH (ZERO PyAutoGUI) FOR BOTH PLATFORMS
                # =============================================================
                # Queue message in local bridge so Tampermonkey injects directly into DOM
                self.bridge_server.start(contact=contact_name)
                self.bridge_server.set_pending_outbound(message, contact=contact_name)

                # Open conversation in default/configured browser
                need_open_url = True
                hwnd = None
                browser_target = "chrome"
                if self.ai and hasattr(self.ai, 'config'):
                    browser_target = self.ai.config.get('default_browser', 'chrome').lower()

                if self.system:
                    hwnd = (self.system.find_window_hwnd(browser_target) or 
                            self.system.find_window_hwnd("brave") or 
                            self.system.find_window_hwnd("chrome") or 
                            self.system.find_window_hwnd("edge"))

                if hwnd and self._active_chat_url == web_url and (time.time() - self._active_chat_time) < 900:
                    need_open_url = False
                    self.system.focus_window_hwnd(hwnd)
                    time.sleep(0.3)

                if need_open_url:
                    opened = False
                    if self.system:
                        res = self.system.open_url(web_url, browser=browser_target)
                        opened = res.get("success", False) if isinstance(res, dict) else False
                    if not opened:
                        import webbrowser
                        webbrowser.open(web_url)
                    self._active_chat_url = web_url
                    self._active_chat_time = time.time()

                return {
                    "success": True,
                    "platform": platform,
                    "contact": contact_name,
                    "handle": handle,
                    "url": web_url,
                    "message_sent": message,
                    "auto_sent": True,
                    "channel": "tampermonkey_dom",
                    "message": f"{platform.capitalize()} par {contact_name.capitalize()} ke chat me message send kar diya Boss! ('{message}')"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Social dispatch error: {str(e)}"
            }

    # =========================================================================
    # ON-DEMAND AUTONOMOUS CHATTING ENGINE
    # =========================================================================

    def start_autonomous_chat(
        self, 
        platform: str, 
        contact_name: str, 
        initial_message: Optional[str] = None,
        directive: Optional[str] = None,
        tone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start Autonomous Gatekeeper Chat Mode:
        1. Spins up on-demand bridge server (< 10ms).
        2. Sets active directive/tone if specified.
        3. Sends tailored intro message based on directive and mode.
        4. Sets auto_chat_enabled = True so FRIDAY actively handles the incoming chat.
        """
        plat = platform.lower().strip()
        if "insta" in plat:
            plat = "instagram"
        elif "snap" in plat:
            plat = "snapchat"

        clean_contact = contact_name.lower().strip()
        self.active_chat_contact = clean_contact
        self.auto_chat_enabled = True

        effective_directive = directive or tone
        if effective_directive and effective_directive.strip():
            self.chat_directives[clean_contact] = effective_directive.strip()
            logger.info(f"[SocialGatekeeper] Active chat directive for {clean_contact}: '{effective_directive}'")
        else:
            self.chat_directives.pop(clean_contact, None)

        # 1. Start bridge server on-demand on 127.0.0.1:8765
        self.bridge_server.start(contact=clean_contact)

        # 2. Determine initial message (Tailored intro based on directive & mode)
        intro_text = self.get_icebreaker(contact_name, directive=effective_directive)
        if initial_message and initial_message.strip():
            init_clean = initial_message.strip()
            if init_clean.lower() in ("hi", "hello", "hey"):
                full_intro = intro_text
            elif init_clean.lower() not in intro_text.lower():
                full_intro = f"{init_clean}. {intro_text}"
            else:
                full_intro = intro_text
        else:
            full_intro = intro_text

        self.chat_histories[clean_contact] = [{"role": "friday", "text": full_intro}]
        self.recent_sent_texts.append(full_intro)

        # 3. Dispatch to browser (DOM queue for Snapchat, PC browser for Instagram)
        self.send_social_message(plat, contact_name, message=full_intro)

        return {
            "success": True,
            "platform": plat,
            "contact": contact_name,
            "auto_chat": True,
            "bridge_running": True,
            "intro_sent": full_intro,
            "directive": effective_directive,
            "message": f"{contact_name.capitalize()} ke saath autonomous gatekeeper chat shuru kar di Sir! Bridge server active hai."
        }

    def stop_autonomous_chat(self) -> Dict[str, Any]:
        """Stop autonomous chatting and shut down the bridge server on-demand."""
        target = self.active_chat_contact or "Contact"
        self.auto_chat_enabled = False
        self.active_chat_contact = None
        self.chat_directives.clear()
        self.bridge_server.stop()
        return {
            "success": True,
            "auto_chat": False,
            "bridge_running": False,
            "message": f"{target.capitalize()} se autonomous chatting band kar di Sir, bridge server close ho gaya."
        }

    def handle_incoming_bridge_message(self, sender: str, text: str, url: str) -> Dict[str, Any]:
        """Called by local bridge server when Tampermonkey detects an incoming message bubble in Brave."""
        if self.bridge_server.is_running:
            self.auto_chat_enabled = True

        if not self.auto_chat_enabled:
            return {"should_reply": False, "reason": "auto_chat_disabled"}

        clean_text = text.strip()
        if not clean_text:
            return {"should_reply": False, "reason": "empty_text"}

        effective_sender = (self.active_chat_contact or sender or "Friend").capitalize()
        contact_key = effective_sender.lower()

        # Pillar 4: Zero Self-Echo Filter (Drop Friday's own intro or exact sent messages)
        clean_lower = clean_text.lower()
        if clean_lower.startswith("i am friday") or clean_lower.startswith("i'm friday") or clean_lower.startswith("namaste auntyji, main friday"):
            logger.info(f"[SocialGatekeeper] Ignored self-intro echo: '{clean_text}'")
            return {"should_reply": False, "reason": "self_intro_echo"}

        for sent in self.recent_sent_texts[-10:]:
            sent_clean = sent.lower().strip()
            # Only exact match to avoid falsely dropping user messages that quote Friday
            if sent_clean and sent_clean == clean_lower:
                logger.info(f"[SocialGatekeeper] Ignored exact self-echo: '{clean_text}'")
                return {"should_reply": False, "reason": "self_sent_echo"}

        # Safety check: Emergency words
        emergency_words = ("urgent", "emergency", "accident", "hospital", "paise", "help", "police", "danger")
        if any(w in clean_lower for w in emergency_words):
            logger.warning(f"[SocialGatekeeper] Emergency keyword detected in '{clean_text}'. Holding auto-reply.")
            return {
                "should_reply": False,
                "reason": "emergency_keyword_detected",
                "alert": f"Emergency keyword in message: {clean_text}"
            }

        # Deduplication Guard: Ignore identical incoming message received within 20 seconds
        now = time.time()
        last_time = self._last_reply_time.get(contact_key, 0)
        last_text = self._last_incoming_text.get(contact_key, "")
        if clean_text.lower() == last_text.lower() and (now - last_time < 20.0):
            logger.info(f"[SocialGatekeeper] Ignored duplicate incoming message within 20s: '{clean_text}'")
            return {"should_reply": False, "reason": "duplicate_suppressed"}

        # Concurrency Lock: Strictly prevent double generation if bridge sends parallel requests
        if not self._bridge_lock.acquire(blocking=False):
            logger.info(f"[SocialGatekeeper] Bridge already busy generating reply, dropping concurrent request for: '{clean_text}'")
            return {"should_reply": False, "reason": "busy_generating"}

        try:
            # Mark timestamp and incoming text IMMEDIATELY to prevent race conditions
            self._last_reply_time[contact_key] = now
            self._last_incoming_text[contact_key] = clean_text

            # Pillar 2: Append user text to rolling sliding history
            if contact_key not in self.chat_histories:
                self.chat_histories[contact_key] = []
            self.chat_histories[contact_key].append({"role": "user", "text": clean_text})
            if len(self.chat_histories[contact_key]) > 10:
                self.chat_histories[contact_key] = self.chat_histories[contact_key][-10:]

            # Pillar 1 & 3: Dynamic context-aware reply
            reply = self.generate_reply(effective_sender, clean_text, history=self.chat_histories[contact_key])

            # Track sent text for self-echo and history
            self.recent_sent_texts.append(reply)
            if len(self.recent_sent_texts) > 20:
                self.recent_sent_texts = self.recent_sent_texts[-20:]
            self.chat_histories[contact_key].append({"role": "friday", "text": reply})

            print(f"\n[Autonomous Chat] {effective_sender}: '{clean_text}' -> FRIDAY: '{reply}'")
            logger.info(f"[SocialGatekeeper] Autonomous reply for {effective_sender}: '{reply}'")
            return {
                "should_reply": True,
                "reply": reply,
                "contact": effective_sender
            }
        finally:
            self._bridge_lock.release()
