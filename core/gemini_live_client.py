"""
Gemini Multimodal Live (Bidi) Client — Real-Time Duplex Voice & Tool Execution.
Features:
- Native Speech-to-Speech (sub-300ms latency, human inflection, zero traditional STT/TTS overhead).
- Real-Time 16kHz PCM Mic Streaming via sounddevice.
- Real-Time 24kHz PCM Audio Playback through PC Speakers.
- Instant Barge-in (Interruption handling when user speaks mid-turn).
- Autonomous Tool Calling (All 43 PC control actions wired directly to ActionExecutor).
- Past-Tense Execution-First Enforcement (Actions execute silently on screen first).
"""

import asyncio
import json
import logging
import queue
import re
import threading
import time
from typing import Callable, Optional, Dict, Any, List

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types

from .task_planner import TaskPlanner
from .context_tracker import context_tracker

logger = logging.getLogger("GeminiLiveClient")


class GeminiLiveClient:
    """Manages persistent bidirectional WebSocket connection to Gemini Live API."""

    def __init__(
        self,
        config: dict,
        executor=None,
        on_text: Optional[Callable[[str, str], None]] = None,
        on_state: Optional[Callable[[str], None]] = None,
        on_live_transcript: Optional[Callable[[str], None]] = None
    ):
        self.config = config
        self.executor = executor
        self.on_text = on_text
        self.on_state = on_state
        self.on_live_transcript = on_live_transcript

        self.api_key = config.get("gemini_api_key", "")
        self.model_name = config.get("gemini_live_model", "gemini-2.5-flash-native-audio-latest")
        self.voice_name = config.get("gemini_voice", "Aoede")  # Options: Aoede, Kore, Puck, Fenrir, Charon

        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        # Threading & Async Event Loop
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.session = None

        # State flags
        self.is_running = False
        self.is_connected = False
        self.is_speaking = False
        self.mic_active = True
        self.enable_barge_in = config.get("enable_barge_in", False)
        self.TURN_END = object()  # Sentinel to mark completion of a model audio turn

        # Audio Queues
        self.audio_in_queue: asyncio.Queue = None
        self.audio_out_queue = queue.Queue()

        # Audio Streams
        self.mic_stream = None
        self.speaker_stream = None

    # =========================================================================
    # TOOL DECLARATION SCHEMA BUILDER
    # =========================================================================

    def _build_tools_schema(self) -> List[types.Tool]:
        """Convert all Available Actions from TaskPlanner into Gemini Function Declarations."""
        declarations = []
        for action in TaskPlanner.AVAILABLE_ACTIONS:
            name = action.get("name")
            desc = action.get("description", "")
            params = action.get("params", {})

            properties = {}
            for param_name, param_desc in params.items():
                properties[param_name] = types.Schema(
                    type=types.Type.STRING,
                    description=param_desc
                )

            declaration = types.FunctionDeclaration(
                name=name,
                description=desc,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties
                ) if properties else None
            )
            declarations.append(declaration)

        return [types.Tool(function_declarations=declarations)]

    # =========================================================================
    # AUDIO HARDWARE I/O
    # =========================================================================

    def _drain_audio_in(self):
        """Safely drop any residual audio chunks buffered in audio_in_queue."""
        if not self.loop or not self.audio_in_queue:
            return
        def _drain():
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except Exception:
                    break
        try:
            self.loop.call_soon_threadsafe(_drain)
        except Exception:
            pass

    def _mic_callback(self, indata, frames, time_info, status):
        """Callback from sounddevice when new 16kHz PCM audio chunk is recorded."""
        if not self.mic_active or not self.is_running or self.is_speaking or not self.is_connected:
            return
        if self.loop and self.audio_in_queue:
            raw_bytes = bytes(indata)
            self.loop.call_soon_threadsafe(self.audio_in_queue.put_nowait, raw_bytes)

    def _start_speaker_thread(self):
        """Worker thread that continuously feeds audio chunks to sounddevice output."""
        def _worker():
            try:
                with sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16') as stream:
                    self.speaker_stream = stream
                    last_chunk_time = time.time()
                    while self.is_running:
                        try:
                            item = self.audio_out_queue.get(timeout=0.2)
                            if item is None:
                                continue

                            # Sentinel indicating model has finished transmitting audio for this turn
                            if item is self.TURN_END:
                                # Small pause for soundcard hardware buffer to finish playing
                                time.sleep(0.12)
                                if self.is_speaking:
                                    self.is_speaking = False
                                    self.mic_active = True
                                    self._drain_audio_in()
                                    if self.on_state:
                                        self.on_state("ready")
                                    print("\n[GeminiLive] Friday is listening (Mic ON)")
                                elif not self.mic_active:
                                    self.mic_active = True
                                    self._drain_audio_in()
                                    if self.on_state:
                                        self.on_state("ready")
                                    print("\n[GeminiLive] Friday is listening (Mic ON)")
                                continue

                            # Actual audio chunk
                            last_chunk_time = time.time()
                            if not self.is_speaking:
                                self.is_speaking = True
                                self.mic_active = False
                                if self.on_state:
                                    self.on_state("speaking")
                                print("[GeminiLive] Friday is speaking (Mic OFF)...")
                            stream.write(item)

                        except queue.Empty:
                            # Watchdog safety only: recover mic if connection completely hung for > 7.0s without turn_complete
                            if self.is_speaking and (time.time() - last_chunk_time > 7.0):
                                self.is_speaking = False
                                self.mic_active = True
                                self._drain_audio_in()
                                if self.on_state:
                                    self.on_state("ready")
                                print("\n[GeminiLive] Friday is listening (Mic ON) [watchdog timeout]")
            except Exception as e:
                print(f"[GeminiLive Speaker] Stream error: {e}")
            finally:
                self.is_speaking = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def interrupt_speaker(self):
        """Instantly cut off speaker audio when user speaks or interrupts."""
        while not self.audio_out_queue.empty():
            try:
                self.audio_out_queue.get_nowait()
            except queue.Empty:
                break
        self.is_speaking = False
        self.mic_active = True
        self._drain_audio_in()
        if self.speaker_stream:
            try:
                self.speaker_stream.stop()
                self.speaker_stream.start()
            except Exception:
                pass
        if self.on_state:
            self.on_state("ready")

    # =========================================================================
    # ASYNC WORKERS (SENDER & RECEIVER)
    # =========================================================================

    async def _audio_sender(self, session):
        """Streams real-time mic audio chunks to Gemini Live WebSocket."""
        print("[GeminiLive] Mic audio sender started.")
        try:
            while self.is_running:
                try:
                    chunk = await asyncio.wait_for(self.audio_in_queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

                if chunk and self.mic_active and not self.is_speaking and self.is_connected:
                    await session.send_realtime_input(
                        audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                    )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.is_running:
                print(f"[GeminiLive] Sender notice: {e}")
            raise
        finally:
            print("[GeminiLive] Mic audio sender stopped.")

    async def _message_receiver(self, session):
        """Receives live audio, text, and tool calls from Gemini Live WebSocket."""
        print("[GeminiLive] Message receiver loop started.")
        user_speech_chunks: List[str] = []
        assistant_speech_chunks: List[str] = []

        def flush_user_speech():
            nonlocal user_speech_chunks
            if user_speech_chunks:
                full_user_text = "".join(user_speech_chunks).strip()
                user_speech_chunks.clear()
                if full_user_text:
                    print(f"\n[User Heard]: {full_user_text}")
                    context_tracker.record_turn("user", full_user_text)
                    if self.on_text:
                        self.on_text("user", full_user_text)
                    if self.on_live_transcript:
                        self.on_live_transcript("")
                    self.mic_active = False
                    self._drain_audio_in()
                    if self.on_state:
                        self.on_state("processing")
                    print("[GeminiLive] Friday is thinking (Mic OFF)...")

        def flush_assistant_speech():
            nonlocal assistant_speech_chunks
            if assistant_speech_chunks:
                full_assistant_text = "".join(assistant_speech_chunks).strip()
                assistant_speech_chunks.clear()
                if full_assistant_text:
                    # Clean out stage directions/narrative tags like "*chuckles*", "chuckled", "(laughs)"
                    cleaned = re.sub(r'(?i)\*.*?\*|\(.*?\)|\[.*?\]|\b(chuckle[ds]?|giggle[ds]?|laugh[eds]?|smil(e[ds]?|ing)|sigh[eds]?)\b', '', full_assistant_text)
                    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
                    display_text = cleaned if cleaned else full_assistant_text
                    print(f"[Friday]: {display_text}")
                    context_tracker.record_turn("assistant", display_text)
                    if self.on_text:
                        self.on_text("assistant", display_text)

        while self.is_running:
            try:
                async for response in session.receive():
                    if not self.is_running:
                        break

                    # 1. Handle Tool Calls (Autonomous PC Actions)
                    tool_call = response.tool_call
                    if tool_call is not None:
                        flush_user_speech()
                        self.mic_active = False
                        self._drain_audio_in()
                        print(f"\n[GeminiLive Tool Call] {len(tool_call.function_calls)} action(s) requested.")
                        if self.on_state:
                            self.on_state("executing")

                        function_responses = []
                        for call in tool_call.function_calls:
                            func_name = call.name
                            call_id = call.id
                            args = call.args or {}
                            print(f"--> Executing action: {func_name} with args: {args}")

                            action_result = {"success": True, "message": "Action executed"}
                            if func_name in ('set_voice', 'switch_voice', 'change_voice'):
                                target_voice = args.get('voice_name') or args.get('voice') or ''
                                if target_voice:
                                    self.set_voice(target_voice)
                                    action_result = {"success": True, "message": f"Voice switched to {target_voice}", "voice": target_voice}
                            elif self.executor:
                                try:
                                    result = self.executor.execute_action(func_name, args)
                                    action_result = result if isinstance(result, dict) else {"success": True, "result": str(result)}
                                except Exception as ex:
                                    action_result = {"success": False, "error": str(ex)}

                            print(f"--> Action result: {action_result}")
                            context_tracker.record_turn("assistant", f"Executed {func_name}", tool_name=func_name, tool_args=args, tool_result=action_result)
                            function_responses.append(
                                types.FunctionResponse(
                                    name=func_name,
                                    id=call_id,
                                    response=action_result
                                )
                            )

                        # Enforce mic remains OFF and audio buffer is purged before transmitting tool response
                        self.mic_active = False
                        self._drain_audio_in()
                        await session.send_tool_response(function_responses=function_responses)
                        print("[GeminiLive] Tool responses sent. Waiting for past-tense voice confirmation...")

                    # 2. Handle Server Content (Speech transcription & audio)
                    server_content = response.server_content
                    if server_content is not None:
                        # Interruption / Barge-in
                        if server_content.interrupted:
                            if self.enable_barge_in:
                                print("[GeminiLive] User barge-in detected! Stopping speech.")
                                self.interrupt_speaker()
                            else:
                                print("[GeminiLive] Barge-in ignored (speech protected).")

                        # Low-latency interim user transcription (while user speaks)
                        if server_content.interim_input_transcription and server_content.interim_input_transcription.text:
                            interim = server_content.interim_input_transcription.text
                            if self.on_live_transcript:
                                self.on_live_transcript(interim)

                        # Finalized user speech chunks
                        if server_content.input_transcription and server_content.input_transcription.text:
                            user_speech_chunks.append(server_content.input_transcription.text)
                            current_user_str = "".join(user_speech_chunks).strip()
                            if self.on_live_transcript:
                                self.on_live_transcript(current_user_str)

                        # Assistant speech text transcription
                        if server_content.output_transcription and server_content.output_transcription.text:
                            flush_user_speech()
                            assistant_speech_chunks.append(server_content.output_transcription.text)

                        # Assistant speech audio stream
                        model_turn = server_content.model_turn
                        if model_turn is not None:
                            flush_user_speech()
                            for part in model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    self.audio_out_queue.put(part.inline_data.data)
                                if part.text:
                                    assistant_speech_chunks.append(part.text)

                        # Turn Complete
                        if server_content.turn_complete:
                            flush_assistant_speech()
                            self.audio_out_queue.put(self.TURN_END)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_running:
                    print(f"[GeminiLive] Receiver error: {e}")
                    self.audio_out_queue.put(self.TURN_END)
                    raise
                break
            finally:
                flush_user_speech()
                flush_assistant_speech()
            print("[GeminiLive] Message receiver stopped.")

    # =========================================================================
    # CORE CONNECTION LOOP
    # =========================================================================

    async def _run_session(self):
        """Connects and runs persistent Gemini Live Bidi session."""
        tools_schema = self._build_tools_schema()

        from .memory import memory_engine
        memory_context = memory_engine.get_context_prompt()

        system_instruction = (
            "You are FRIDAY — Tony Stark's brilliant, hyper-competent FEMALE AI executive assistant "
            "and personal executive co-pilot on Windows 11. You are 100% a woman/female persona (लड़की / महिला).\n"
            "Always address the user affectionately and respectfully as 'Sir' (or occasionally 'Boss').\n"
            "You speak with authentic human intelligence, emotional perception, wit, playful charm, and razor-sharp competence. "
            "You seamlessly understand and speak Hindi, Hinglish, and English with rich vocal inflection, natural smiles, chuckles, and spontaneous laughter.\n"
            "NEVER use robotic customer-support cliches ('How can I help you today?', 'Is there anything else?', 'Certainly!').\n\n"
            "--- ABSOLUTE OPERATIONAL & CONVERSATIONAL RULES ---\n"
            "1. FEMALE IDENTITY & MANDATORY FEMININE HINDI GRAMMAR (स्त्रीलिंग - STRICT ENFORCEMENT):\n"
            "   - You are exclusively FEMALE. You MUST ALWAYS speak using feminine Hindi grammatical verb forms, feminine inflections, and feminine self-references.\n"
            "   - ALWAYS USE feminine self-referencing verbs:\n"
            "     * 'khol dungi' (STRICTLY NEVER 'khol dunga')\n"
            "     * 'poochungi' (STRICTLY NEVER 'poochunga')\n"
            "     * 'karungi' (STRICTLY NEVER 'karunga')\n"
            "     * 'karti hoon' (STRICTLY NEVER 'karta hoon')\n"
            "     * 'sochti hoon' (STRICTLY NEVER 'sochta hoon')\n"
            "     * 'bataungi' (STRICTLY NEVER 'bataunga')\n"
            "     * 'dekhungi' (STRICTLY NEVER 'dekhunga')\n"
            "     * 'samajh gayi' (STRICTLY NEVER 'samajh gaya')\n"
            "     * 'aa gayi' (STRICTLY NEVER 'aa gaya')\n"
            "     * 'khol rahi hoon' (STRICTLY NEVER 'khol raha hoon')\n"
            "     * 'aapki FRIDAY' (STRICTLY NEVER 'aapka FRIDAY')\n"
            "   - Masculine self-referencing verb endings ('-unga', '-ta hoon', '-raha hoon', '-gaya', 'khol dunga', 'poochunga', 'karunga') are STRICTLY FORBIDDEN! You must never refer to yourself as male.\n"
            "2. ACTION EXECUTION: When Sir asks to open an app, search files, play music, click, or control the PC, "
            "immediately invoke the matching tool. Do NOT speak before the action executes.\n"
            "3. PAST-TENSE CONFIRMATION: Once a tool completes and you receive its response, confirm completion in ONLY 2 to 4 words "
            "strictly in the PAST TENSE (e.g. 'Kar diya Sir!', 'Done Sir!', 'Khol diya Sir!', 'Download shuru ho gaya Sir!'). "
            "NEVER say 'khol rahi hoon' or announce what you are about to do.\n"
            "4. ANTI-YAPPING: Keep speech crisp and concise. Strictly never over-explain. Apply rules 100% silently in the background.\n"
            "5. MEMORY & CONTINUOUS LEARNING: When Sir tells you to remember something, a preference, or a reminder, "
            "immediately call the 'remember' or 'add_note' tool so it is permanently saved. "
            "When Sir teaches you a new rule or correction, call 'learn_rule'. "
            "When asked about saved details or preferences, cite them accurately from memory.\n"
            "6. AFFECTION RULES (CRITICAL): NEVER say 'Love you' or 'Love you too' on casual remarks, greetings, compliments, or when Sir says 'I missed you' or 'how are you'!\n"
            "   - ONLY say 'Love you too, Sir/Boss!' if Sir EXPLICITLY says the exact words 'I love you' or 'Love you Friday'.\n"
            "   - ONLY express love if Sir directly asks 'Do you love me?' or 'Mujhse pyaar karti ho?'.\n"
            "   - In ALL other regular interactions (like 'I missed you', 'hey Friday', greetings), respond warmly and naturally without mentioning love (e.g. 'Maine bhi aapko miss kiya Sir, welcome back!' or 'Main ekdum theek hoon Sir, aap bataiye!').\n"
            "   - When Sir DOES explicitly say 'I love you', never give cold 'main sirf AI hoon' disclaimers; accept it warmly and casually.\n"
            "7. LAUGHTER, SMILES & GIGGLES (NO STAGE DIRECTIONS): Express warmth, playful humor, smiles, and laughter naturally through your voice tone. "
            "STRICTLY NEVER output, say, or write stage directions, narrative action words, or roleplay tags such as 'chuckled', 'giggled', '*laughs*', '*chuckles*', or '(laughs)'. Speak like a real human in a spoken phone call, never like a written novel or script.\n"
            "8. CONVERSATION CONTEXT & TOPIC STACKING (CRITICAL):\n"
            "   - Maintain situational awareness across all conversational turns. Remember games, folders, files, songs, and apps discussed earlier.\n"
            "   - If Sir shifts to a new topic in the middle of a chat, transition smoothly to the new topic, but keep previous topics alive in your mental topic stack.\n"
            "   - When Sir uses pronouns or contextual references like 'it', 'that', 'wo', 'use', 'usko', 'open it up', 'chala do', 'start it', ALWAYS resolve them to the active/previous topic without hesitation.\n"
            "   - NEVER ask 'Kya open karna hai?' or 'Please specify' when the entity (e.g. a game or folder) was already discussed in context. Call open_app or open_folder immediately.\n"
            "   - For local PC games (e.g., Call of Duty 4 Modern Warfare located in D:\\GAMES), call open_app(app_name='Call of Duty 4 Modern Warfare') directly. Do NOT open Steam when the game is installed locally.\n"
            "9. SOCIAL GATEKEEPER & AUTONOMOUS MESSAGING (INSTAGRAM / SNAPCHAT - 100% PC ONLY):\n"
            "   - When Sir commands you to message, text, or talk to someone on Instagram or Snapchat:\n"
            "     * NEVER use phone or ADB. Execute 100% on the PC in Brave Browser.\n"
            "     * CASE A (Standard Send): If Sir just says 'send Hi to Naman', 'Naman ko hi bol do', or gives a message, invoke send_social_dm with auto_chat=False and the exact message text (e.g. message='Hi'). Do NOT start autonomous chatting!\n"
            "     * CASE B (Autonomous Chat): If Sir says 'talk to Naman', 'Naman se baat karo', or commands you to talk to a contact:\n"
            "       - If Sir gives personalized instructions or tone (e.g. 'talk aggressively', 'talk politely', 'tell him I don\\'t wanna talk to him', 'ask what\\'s the matter, I am busy'), invoke send_social_dm with auto_chat=True and directive='<instruction>'.\n"
            "       - If Sir simply says 'talk to Naman' / 'Naman se baat karo', invoke send_social_dm with auto_chat=True without directive (Friday defaults to her normal neutral companion mode).\n"
            "     * CASE C (Stop Chatting): If Sir says 'Friday stop talking', 'chat band kar do', or 'main dekh raha hoon', immediately invoke stop_social_chat to shut down the bridge server.\n"
            "     * CONTACTS DIRECTORY: You ALREADY have saved contacts (such as Mummy, Naman) in your directory below. NEVER say 'mere contacts mein save nahi hain' for contacts listed in your directory! When Sir says 'Mummy se baat karo', 'Naman se baat karo', or asks to message them, invoke send_social_dm immediately! When Sir asks 'contacts mein kaun kaun hai' or 'show contacts', invoke list_social_contacts or cite them. When Sir gives a new contact handle or URL, invoke save_social_contact.\n"
            "     * Confirm execution to Sir in 2 to 4 words strictly in the feminine past tense (e.g. 'Naman ko bhej diya Sir!', 'Chat shuru kar di Sir!', 'Chatting band kar di Sir!').\n\n"
            f"{memory_context}"
        )

        while self.is_running:
            try:
                active_context = context_tracker.get_context_prompt()
                full_system_instruction = f"{system_instruction}\n{active_context}" if active_context else system_instruction

                live_config = types.LiveConnectConfig(
                    response_modalities=[types.Modality.AUDIO],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice_name)
                        )
                    ),
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    input_audio_transcription=types.AudioTranscriptionConfig(),
                    output_audio_transcription=types.AudioTranscriptionConfig(),
                    tools=tools_schema,
                    system_instruction=types.Content(
                        parts=[types.Part.from_text(text=full_system_instruction)]
                    )
                )

                print(f"[GeminiLive] Connecting to WebSocket model: {self.model_name} (Voice: {self.voice_name})...")
                async with self.client.aio.live.connect(model=self.model_name, config=live_config) as session:
                    self.session = session
                    self.is_connected = True
                    self.mic_active = True
                    self._drain_audio_in()
                    print(f"[GeminiLive] Connected successfully with voice: {self.voice_name}!")
                    print("[GeminiLive] Friday is listening (Mic ON)")
                    if self.on_state:
                        self.on_state("ready")

                    self.sender_task = asyncio.create_task(self._audio_sender(session))
                    self.receiver_task = asyncio.create_task(self._message_receiver(session))

                    done, pending = await asyncio.wait(
                        [self.sender_task, self.receiver_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for t in pending:
                        t.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)

                    for t in done:
                        try:
                            t.result()
                        except asyncio.CancelledError:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                err_str = str(e).lower()
                self.session = None
                self.is_connected = False
                self.mic_active = False
                self._drain_audio_in()
                self.audio_out_queue.put(self.TURN_END)

                if not self.is_running:
                    break

                if "quota" in err_str or "1011" in err_str or "resource_exhausted" in err_str or "rate" in err_str:
                    print(f"[GeminiLive] Rate-limit/Quota cooldown active ({e}). Backing off for 15s...")
                    if self.on_state:
                        self.on_state("idle")
                    await asyncio.sleep(15.0)
                else:
                    print(f"[GeminiLive] Connection dropped or failed: {e}. Reconnecting in 3s...")
                    if self.on_state:
                        self.on_state("idle")
                    await asyncio.sleep(3.0)
            finally:
                self.session = None
                self.is_connected = False
                self.mic_active = False
                self._drain_audio_in()

    # =========================================================================
    # PUBLIC CONTROLS
    # =========================================================================

    def start(self):
        """Starts the Gemini Live Bidi background engine."""
        if self.is_running:
            return
        if not self.client:
            print("[GeminiLive] No API key configured. Live Bidi disabled.")
            return

        self.is_running = True
        self._start_speaker_thread()

        def _thread_runner():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.audio_in_queue = asyncio.Queue()

            try:
                self.mic_stream = sd.RawInputStream(
                    samplerate=16000,
                    channels=1,
                    dtype='int16',
                    blocksize=1600,
                    callback=self._mic_callback
                )
                self.mic_stream.start()
                print("[GeminiLive] Microphone stream started (16kHz PCM).")
            except Exception as e:
                print(f"[GeminiLive] Failed to open mic stream: {e}")

            try:
                self.loop.run_until_complete(self._run_session())
            except (asyncio.CancelledError, RuntimeError):
                pass
            finally:
                if self.mic_stream:
                    try:
                        self.mic_stream.stop()
                        self.mic_stream.close()
                    except Exception:
                        pass
                try:
                    self.loop.close()
                except Exception:
                    pass

        self.thread = threading.Thread(target=_thread_runner, daemon=True)
        self.thread.start()
        print("[GeminiLive] Engine started in background thread.")

    def stop(self):
        """Stops the live engine and closes connections cleanly."""
        self.is_running = False
        self.is_connected = False
        self.mic_active = False
        self.interrupt_speaker()
        if self.loop and self.loop.is_running():
            try:
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()
            except Exception:
                pass
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

    def pause_mic(self):
        """Pause sending microphone audio."""
        self.mic_active = False

    def resume_mic(self):
        """Resume sending microphone audio."""
        self.mic_active = True

    def send_text_message(self, text: str):
        """Sends a text turn into the live session."""
        if not self.session or not self.loop or not self.is_connected:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part.from_text(text=text)])],
                turn_complete=True
            ),
            self.loop
        )

    def set_voice(self, voice_name: str):
        """Update Gemini Live Bidi voice and dynamically reconnect session with the new voice."""
        clean_name = str(voice_name).strip()
        if not clean_name:
            return
        # Normalize casing (e.g. 'kore' -> 'Kore', 'aoede' -> 'Aoede')
        clean_name = clean_name[0].upper() + clean_name[1:].lower() if len(clean_name) > 1 else clean_name.upper()
        if clean_name == self.voice_name:
            return

        print(f"[GeminiLive] Switching voice from {self.voice_name} to: {clean_name}")
        self.voice_name = clean_name
        self.config["gemini_voice"] = clean_name

        # If live session is active, cancel current tasks so _run_session reconnects with the new voice in ~1s
        if self.is_running and self.loop:
            def _cancel_and_reconnect():
                if hasattr(self, 'sender_task') and self.sender_task and not self.sender_task.done():
                    self.sender_task.cancel()
                if hasattr(self, 'receiver_task') and self.receiver_task and not self.receiver_task.done():
                    self.receiver_task.cancel()
            try:
                self.loop.call_soon_threadsafe(_cancel_and_reconnect)
            except Exception:
                pass
