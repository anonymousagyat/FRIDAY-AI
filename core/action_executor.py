"""
Action Executor — High-speed sequential & parallel PC automation dispatcher.
Executes atomic OS operations, file search, diagnostics, processes, window management, and input control.
"""

import os
import time
from typing import Dict, List, Any


class ActionExecutor:
    """Executes atomic actions on Windows with verification and minimal latency."""

    def __init__(self, system_control, screen_reader=None, web_researcher=None, mobile_control=None, vector_memory=None, phantom_typer=None, screen_peeler=None, social_gatekeeper=None):
        self.system = system_control
        self.screen_reader = screen_reader
        self.web_researcher = web_researcher
        self.mobile = mobile_control
        self.vector_memory = vector_memory
        self.phantom_typer = phantom_typer
        self.screen_peeler = screen_peeler
        self.social_gatekeeper = social_gatekeeper

    def set_web_researcher(self, web_researcher):
        self.web_researcher = web_researcher

    def set_mobile_control(self, mobile_control):
        self.mobile = mobile_control

    def set_vector_memory(self, vector_memory):
        self.vector_memory = vector_memory

    def set_phantom_typer(self, phantom_typer):
        self.phantom_typer = phantom_typer

    def set_screen_peeler(self, screen_peeler):
        self.screen_peeler = screen_peeler

    def set_social_gatekeeper(self, social_gatekeeper):
        self.social_gatekeeper = social_gatekeeper

    def execute_plan(self, plan: dict) -> dict:
        """Execute a full action plan."""
        actions = plan.get('actions', [])
        response_text = plan.get('response', '')

        result_details = []
        all_success = True
        failed_at = None

        last_found_files = []

        for i, action_obj in enumerate(actions):
            action_name = action_obj.get('action')
            params = dict(action_obj.get('params', {}))

            # Smart Parameter Chaining:
            # If open_file or play_media has placeholder path (like {{search_result}} or empty)
            # or path not found directly, use the file found by the previous search_files!
            if action_name in ('open_file', 'play_media'):
                path_val = params.get('path') or params.get('query') or params.get('filename') or ''
                if (not path_val or path_val in ('{{search_result}}', 'search_result', 'result', 'file')) and last_found_files:
                    params['path'] = last_found_files[0]
                elif path_val and not os.path.exists(path_val) and last_found_files:
                    params['path'] = last_found_files[0]

            res = self.execute_action(action_name, params)

            if res.get('files'):
                last_found_files = res['files']
            elif res.get('file'):
                last_found_files = [res['file']]

            result_details.append({
                'action': action_name,
                'success': res.get('success', False),
                'message': res.get('message', ''),
                'files': res.get('files', [])
            })

            if not res.get('success', False):
                all_success = False
                failed_at = i
                break

        return {
            'success': all_success,
            'results': result_details,
            'response': response_text,
            'failed_at': failed_at
        }

    def execute_action(self, action_name: str, params: dict) -> dict:
        """Execute a single atomic action on the system."""
        try:
            # 1. Apps & Websites
            if action_name == 'open_app':
                app_name = (params.get('app_name') or '').strip()
                if not app_name or app_name.lower() in ('it', 'that', 'this', 'game', 'app', 'the game', 'my game', 'favorite game', 'open it'):
                    try:
                        from .context_tracker import context_tracker
                        topic = context_tracker.get_active_topic()
                        if topic:
                            app_name = topic.path if topic.path else topic.entity
                    except Exception:
                        pass
                return self.system.open_app(app_name)

            elif action_name == 'open_url':
                return self.system.open_url(params.get('url', ''), browser=params.get('browser'))

            elif action_name == 'search_web':
                return self.system.search_web(params.get('query', ''), browser=params.get('browser'))

            elif action_name == 'research_web':
                if self.web_researcher:
                    query = params.get('query', '')
                    res = self.web_researcher.search(query, max_results=params.get('max_results', 5))
                    answer = res.get('answer') or (res.get('results', [{}])[0].get('content', '') if res.get('results') else 'Koi jankari nahi mili.')
                    return {
                        'success': res.get('success', False),
                        'message': answer,
                        'context': res.get('formatted_context', ''),
                        'answer': answer,
                        'results': res.get('results', [])
                    }
                return {'success': False, 'message': 'Web Researcher module configured nahi hai.'}

            # 2. File System Search, Media Playback & Inspection
            elif action_name == 'search_files':
                return self.system.search_files(params.get('filename', ''), search_dir=params.get('search_dir'))

            elif action_name == 'open_folder':
                target_folder = params.get('folder_name') or params.get('path') or params.get('name') or ''
                if not target_folder or str(target_folder).lower() in ('it', 'that', 'this', 'folder', 'the folder', 'directory'):
                    try:
                        from .context_tracker import context_tracker
                        topic = context_tracker.get_topic_by_type('folder') or context_tracker.get_active_topic()
                        if topic and topic.path:
                            target_folder = topic.path
                        elif topic:
                            target_folder = topic.entity
                    except Exception:
                        pass
                return self.system.open_folder(target_folder, drive=params.get('drive'))

            elif action_name == 'open_file':
                return self.system.open_file(params.get('path', ''), search_dir=params.get('search_dir'))

            elif action_name == 'play_media':
                target = params.get('query') or params.get('filename') or params.get('path') or ''
                return self.system.play_media(target, search_dir=params.get('search_dir') or params.get('folder'))

            elif action_name == 'read_file':
                return self.system.read_file(params.get('path', ''))

            elif action_name == 'write_file':
                target_path = params.get('file_path') or params.get('path') or params.get('filename') or ''
                code_content = params.get('content') or params.get('code') or params.get('text') or ''
                return self.system.write_file(target_path, code_content)

            elif action_name == 'list_directory':
                return self.system.list_directory(params.get('path'))

            # 3. System Health, Storage & Diagnostics
            elif action_name == 'get_disk_drives':
                return self.system.get_disk_drives()

            elif action_name == 'list_running_processes':
                return self.system.list_running_processes()

            elif action_name == 'kill_process':
                return self.system.kill_process(params.get('process_name', ''))

            elif action_name == 'system_info':
                return self.system.system_info()

            elif action_name == 'get_network_info':
                return self.system.get_network_info()

            elif action_name == 'toggle_wifi':
                return self.system.toggle_wifi(params.get('state', 'off'))

            elif action_name == 'toggle_bluetooth':
                return self.system.toggle_bluetooth(params.get('state', 'off'))

            # 4. OS Utilities & Shell
            elif action_name == 'run_powershell_command':
                return self.system.run_powershell_command(params.get('cmd', ''))

            elif action_name == 'lock_pc':
                return self.system.lock_pc()

            elif action_name == 'empty_recycle_bin':
                return self.system.empty_recycle_bin()

            # 5. Windows & Window Management
            elif action_name == 'close_app':
                return self.system.close_app(params.get('window_title', ''))

            elif action_name == 'focus_window':
                return self.system.focus_window(params.get('window_title', ''))

            elif action_name == 'snap_window':
                return self.system.snap_window(
                    params.get('window_title', ''),
                    params.get('position', 'left')
                )

            elif action_name == 'minimize_window':
                return self.system.minimize_window(params.get('window_title', ''))

            # 6. Inputs & Emulation
            elif action_name == 'type_text':
                return self.system.type_text(params.get('text', ''))

            elif action_name == 'press_keys':
                return self.system.press_keys(params.get('keys', ''))

            elif action_name == 'click_at':
                return self.system.click_at(
                    int(params.get('x', 0)),
                    int(params.get('y', 0))
                )

            elif action_name == 'scroll':
                return self.system.scroll(
                    params.get('direction', 'down'),
                    int(params.get('amount', 3))
                )

            elif action_name == 'set_volume':
                return self.system.set_volume(int(params.get('level', 50)))

            elif action_name == 'take_screenshot':
                img = self.system.take_screenshot(save_to_desktop=True)
                success = img is not None
                return {'success': success, 'message': 'Screenshot saved to Desktop.' if success else 'Failed to capture.'}

            elif action_name == 'get_time':
                return {'success': True, 'message': self.system.get_time()}

            elif action_name == 'get_date':
                return {'success': True, 'message': self.system.get_date()}

            elif action_name == 'wait':
                secs = float(params.get('seconds', 0.5))
                time.sleep(secs)
                return {'success': True, 'message': f"Waited {secs}s"}

            elif action_name == 'read_screen':
                if not self.screen_reader:
                    return {'success': False, 'message': 'Screen reader not configured.'}
                ans = self.screen_reader.analyze(params.get('question', None))
                return {'success': True, 'message': ans}

            elif action_name == 'find_and_click':
                if not self.screen_reader:
                    return {'success': False, 'message': 'Screen reader not configured.'}
                query = params.get('element_description') or params.get('query') or params.get('label') or ''
                dbl = bool(params.get('double_click', False))
                btn = params.get('button', 'left')
                return self.screen_reader.find_and_click(query, double_click=dbl, button=btn)

            elif action_name == 'play_youtube_music':
                q = params.get('query') or params.get('song') or params.get('title') or ''
                return self.system.play_youtube_music(q)

            elif action_name == 'automate_steam':
                game = params.get('game_name') or params.get('game') or params.get('title') or ''
                act = params.get('action') or 'install'
                return self.system.automate_steam(game, action=act)

            elif action_name == 'dictate':
                return {'success': True, 'message': 'dictation_mode', 'special': 'dictation'}

            # 7. Long-Term Memory Engine
            elif action_name in ('remember', 'remember_fact'):
                from .memory import memory_engine
                key = params.get('key') or params.get('name') or params.get('topic') or 'fact'
                value = params.get('value') or params.get('fact') or params.get('info') or params.get('content') or ''
                cat = params.get('category', 'facts')
                return memory_engine.save_fact(str(key), str(value), category=str(cat))

            elif action_name in ('recall_memory', 'recall'):
                from .memory import memory_engine
                query = params.get('query') or params.get('search') or params.get('key') or ''
                return memory_engine.recall(str(query))

            elif action_name in ('forget_memory', 'forget'):
                from .memory import memory_engine
                key = params.get('key') or params.get('name') or ''
                cat = params.get('category', 'facts')
                return memory_engine.forget(str(key), category=str(cat))

            elif action_name in ('add_note', 'add_memory_note'):
                from .memory import memory_engine
                note_text = params.get('text') or params.get('note') or params.get('content') or ''
                return memory_engine.add_note(str(note_text))

            # 8. Student Notebook & Continuous Learning
            elif action_name in ('learn_rule', 'learn_lesson'):
                from .memory import memory_engine
                topic = params.get('topic') or 'general_rule'
                trigger = params.get('trigger') or 'general'
                rule = params.get('rule') or ''
                mistake = params.get('mistake') or ''
                example = params.get('example') or ''
                return memory_engine.add_lesson(str(topic), str(trigger), str(rule), str(mistake), str(example))

            elif action_name == 'list_learned_rules':
                from .memory import memory_engine
                query = params.get('query') or ''
                lessons = memory_engine.get_lessons(query)
                if not lessons:
                    return {'success': True, 'message': 'Student notebook is currently empty, Sir.'}
                summary = [f"[{l.get('topic')}]: {l.get('rule')}" for l in lessons]
                return {'success': True, 'lessons': lessons, 'message': f"Learned {len(lessons)} rules: " + "; ".join(summary)}

            elif action_name == 'forget_learned_rule':
                from .memory import memory_engine
                topic_or_id = params.get('topic_or_id') or params.get('topic') or params.get('id') or ''
                return memory_engine.delete_lesson(topic_or_id)

            elif action_name in ('set_voice', 'switch_voice', 'change_voice'):
                voice_name = params.get('voice_name') or params.get('voice') or ''
                return {'success': True, 'message': f"Voice set to {voice_name}", 'voice': voice_name}

            # 9. Autonomous Deep-Work Worker (Hermes Bridge)
            elif action_name == 'delegate_to_hermes':
                from .hermes_bridge import hermes_bridge
                task_prompt = params.get('task') or params.get('prompt') or ''
                return hermes_bridge.run_task_async(task_prompt)

            # 10. Mobile Telekinesis (Android ADB)
            elif action_name == 'phone_battery':
                if self.mobile:
                    return self.mobile.get_battery_status()
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_open_app':
                if self.mobile:
                    return self.mobile.open_app(params.get('app_name', ''))
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_swipe':
                if self.mobile:
                    return self.mobile.swipe(params.get('direction', 'up'))
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_tap':
                if self.mobile:
                    return self.mobile.tap(int(params.get('x', 500)), int(params.get('y', 1000)))
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_flashlight':
                if self.mobile:
                    return self.mobile.toggle_flashlight()
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_screenshot':
                if self.mobile:
                    return self.mobile.take_phone_screenshot()
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            elif action_name == 'phone_send_file':
                if self.mobile:
                    return self.mobile.send_file(params.get('pc_path', ''))
                return {'success': False, 'message': 'Mobile control module available nahi hai.'}

            # 11. Local Vector Knowledge Oracle (LanceDB/Vector RAG)
            elif action_name == 'index_knowledge':
                if self.vector_memory:
                    target_path = params.get('path', '')
                    if os.path.isdir(target_path):
                        return self.vector_memory.index_directory(target_path)
                    elif os.path.isfile(target_path):
                        count = self.vector_memory.index_file(target_path)
                        return {'success': True, 'chunks': count, 'message': f"'{os.path.basename(target_path)}' ko vector memory me index kar diya Boss!"}
                    return {'success': False, 'message': f"Path nahi mila: {target_path}"}
                return {'success': False, 'message': 'Vector memory module configured nahi hai.'}

            elif action_name == 'query_knowledge':
                if self.vector_memory:
                    q = params.get('question') or params.get('query') or ''
                    matches = self.vector_memory.query(q, top_k=3)
                    if matches:
                        snippets = [f"[{m['file_name']}]: {m['content'][:300]}" for m in matches]
                        summary = "\n\n".join(snippets)
                        return {'success': True, 'matches': matches, 'message': summary}
                    return {'success': True, 'matches': [], 'message': 'Knowledge base me is vishay par koi data nahi mila, Boss.'}
                return {'success': False, 'message': 'Vector memory module configured nahi hai.'}

            # 12. Ghost Keyboard & ScreenPeeler OCR
            elif action_name == 'ghost_type':
                if self.phantom_typer:
                    txt = params.get('text', '')
                    return self.phantom_typer.ghost_paste(txt)
                return {'success': False, 'message': 'Phantom typer module configured nahi hai.'}

            elif action_name == 'peel_screen_text':
                if self.screen_peeler:
                    return self.screen_peeler.peel_text()
                return {'success': False, 'message': 'Screen peeler module configured nahi hai.'}

            # 13. Social Gatekeeper & Autonomous Messenger (Instagram / Snapchat)
            elif action_name in ('send_social_dm', 'chat_as_friday', 'message_contact'):
                if not self.social_gatekeeper:
                    return {'success': False, 'message': 'Social gatekeeper module configured nahi hai.'}
                platform = params.get('platform') or params.get('app') or 'instagram'
                contact = params.get('contact') or params.get('name') or params.get('user') or 'Naman'
                msg = params.get('message') or params.get('text') or None
                auto_chat = params.get('auto_chat', False)
                directive = params.get('directive') or params.get('instruction') or params.get('prompt')
                tone = params.get('tone')
                if isinstance(auto_chat, str):
                    auto_chat = auto_chat.lower().strip() in ('true', '1', 'yes')

                if auto_chat:
                    return self.social_gatekeeper.start_autonomous_chat(
                        platform, contact, initial_message=msg, directive=directive, tone=tone
                    )
                return self.social_gatekeeper.send_social_message(platform, contact, message=msg)

            elif action_name in ('stop_social_chat', 'stop_chat', 'disengage_social'):
                if not self.social_gatekeeper:
                    return {'success': False, 'message': 'Social gatekeeper module configured nahi hai.'}
                return self.social_gatekeeper.stop_autonomous_chat()

            elif action_name == 'reply_as_friday':
                if not self.social_gatekeeper:
                    return {'success': False, 'message': 'Social gatekeeper module configured nahi hai.'}
                contact = params.get('contact') or params.get('name') or 'Friend'
                incoming = params.get('incoming_message') or params.get('text') or ''
                reply = self.social_gatekeeper.generate_reply(contact, incoming)
                platform = params.get('platform') or 'instagram'
                res = self.social_gatekeeper.send_social_message(platform, contact, message=reply)
                return {'success': True, 'reply': reply, 'send_result': res, 'message': f"{contact} ko reply bhej diya: '{reply}'"}

            elif action_name == 'save_social_contact':
                if not self.social_gatekeeper:
                    return {'success': False, 'message': 'Social gatekeeper module configured nahi hai.'}
                name = params.get('name') or params.get('contact') or ''
                platform = params.get('platform') or 'instagram'
                handle = params.get('handle') or params.get('username') or ''
                return self.social_gatekeeper.save_contact(name, platform, handle)

            elif action_name in ('list_social_contacts', 'list_contacts', 'show_contacts'):
                if not self.social_gatekeeper:
                    return {'success': False, 'message': 'Social gatekeeper module configured nahi hai.'}
                summary = self.social_gatekeeper.get_contacts_summary()
                return {'success': True, 'contacts': self.social_gatekeeper.contacts, 'message': f"Saved Contacts:\n{summary}"}

            else:
                return {'success': False, 'message': f"Unknown action: {action_name}"}

        except Exception as e:
            return {'success': False, 'message': f"Execution error in {action_name}: {e}"}
