"""
Jarvis Deep Windows Kernel Engine.
Full OS System-Level Access: File System Search & Reading, Drive Diagnostics,
Running Process Management, PowerShell / Shell Automation, Network Status, and Window Orchestration.
"""

import os
import sys
import re
import time
import ctypes
from ctypes import wintypes
import subprocess
import shutil
import webbrowser
import urllib.parse
import urllib.request
import datetime
import winreg
import glob
from typing import Optional, List, Dict, Tuple, Any

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.02
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

try:
    import psutil
except ImportError:
    psutil = None

# Win32 Constants
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
HWND_TOP = 0
HWND_TOPMOST = -1
SWP_SHOWWINDOW = 0x0040
SWP_FRAMECHANGED = 0x0020
SWP_NOACTIVATE = 0x0010


class SystemControl:
    """Full-access Windows Operating System Control Engine."""

    APPS = {
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'calc': 'calc.exe',
        'chrome': 'chrome.exe',
        'google chrome': 'chrome.exe',
        'brave': 'brave.exe',
        'brave browser': 'brave.exe',
        'browser': 'brave.exe',
        'drive': 'brave.exe',
        'firefox': 'firefox.exe',
        'edge': 'msedge.exe',
        'microsoft edge': 'msedge.exe',
        'microsoft': 'msedge.exe',
        'msedge': 'msedge.exe',
        'spotify': 'spotify.exe',
        'vscode': 'code.cmd',
        'vs code': 'code.cmd',
        'visual studio code': 'code.cmd',
        'file explorer': 'explorer.exe',
        'explorer': 'explorer.exe',
        'files': 'explorer.exe',
        'settings': 'ms-settings:',
        'cmd': 'cmd.exe',
        'command prompt': 'cmd.exe',
        'powershell': 'powershell.exe',
        'terminal': 'wt.exe',
        'windows terminal': 'wt.exe',
        'task manager': 'taskmgr.exe',
        'taskmgr': 'taskmgr.exe',
        'paint': 'mspaint.exe',
        'word': 'winword.exe',
        'excel': 'excel.exe',
        'powerpoint': 'powerpnt.exe',
        'discord': 'discord.exe',
        'telegram': 'telegram.exe',
        'whatsapp': 'whatsapp.exe',
        'steam': 'steam.exe',
        'epic games': 'EpicGamesLauncher.exe',
        'minecraft': 'MinecraftLauncher.exe',
        'minecraft launcher': 'MinecraftLauncher.exe',
        'vlc': 'vlc.exe',
    }

    def __init__(self):
        if sys.platform == "win32":
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32
        else:
            self.user32 = None
            self.kernel32 = None

        self.screen_width = self.user32.GetSystemMetrics(0) if self.user32 else 1920
        self.screen_height = self.user32.GetSystemMetrics(1) if self.user32 else 1080
        self.screen_reader = None

    # =========================================================================
    # 1. FILE SYSTEM EXPLORATION & DEEP SEARCH
    # =========================================================================

    def search_files(self, filename: str, search_dir: str = None, max_results: int = 5) -> dict:
        """Deep recursive search for files or folders across drives with smart separator & noise handling."""
        q_raw = filename.lower().strip()
        if not q_raw:
            return {'success': False, 'files': [], 'message': 'Search query khali hai.'}

        # Media and command noise words to strip for better title matching
        MEDIA_NOISE = {
            'film', 'movie', 'video', 'song', 'mp4', 'mkv', 'avi', 'gaana', 'track',
            'dvdrip', 'hd', '1080p', '720p', 'file', 'play', 'open', 'khol', 'chala',
            'chalao', 'dekho', 'dikhao', 'from', 'in', 'folder', 'holder', 'holdar', 'pholder',
            'drive', 'se', 'me', 'mein', 'pe'
        }

        q_clean = re.sub(r'[._\-\+]+', ' ', q_raw).strip()
        all_words = [w for w in q_clean.split() if len(w) > 1]
        title_words = [w for w in all_words if w not in MEDIA_NOISE]

        # Determine target search roots
        search_roots = []
        if search_dir:
            sd = search_dir.strip()
            # Normalize drive shortcuts (e.g. 'D:', 'd drive', 'D')
            drive_m = re.match(r'^([a-zA-Z])(?:\s*drive|:)?$', sd, re.IGNORECASE)
            if drive_m:
                sd_path = f"{drive_m.group(1).upper()}:\\"
                if os.path.exists(sd_path):
                    search_roots.append(sd_path)
            elif os.path.exists(sd):
                search_roots.append(sd)
            else:
                # Check if it matches a known folder on C:\ or D:\ or User directory
                for root_cand in ['D:\\', 'C:\\', os.path.expanduser('~')]:
                    cand = os.path.join(root_cand, sd)
                    if os.path.exists(cand):
                        search_roots.append(cand)
                        break

        if not search_roots:
            home = os.path.expanduser('~')
            hotspots = [
                'D:\\MOVIES',
                os.path.join(home, 'Downloads'),
                os.path.join(home, 'Desktop'),
                os.path.join(home, 'Videos'),
                os.path.join(home, 'Documents'),
                os.path.join(home, 'Music'),
                'D:\\',
                'C:\\'
            ]
            search_roots = [d for d in hotspots if os.path.exists(d)]

        skip_dirs = {'node_modules', '$recycle.bin', 'system volume information', 'windows', 'appdata', '.git', '.cache'}
        results = []

        def matches_query(f_name: str, parent_dir: str) -> bool:
            f_clean = re.sub(r'[._\-\+]+', ' ', f_name.lower())
            # 1. Direct raw or clean substring
            if q_raw in f_name.lower() or (len(q_clean) > 2 and q_clean in f_clean):
                return True
            # 2. All title words present in filename
            if title_words and all(w in f_clean for w in title_words):
                return True
            # 3. Parent directory match (e.g. folder named "Tum Mile" containing video)
            p_clean = re.sub(r'[._\-\+]+', ' ', os.path.basename(parent_dir).lower())
            if title_words and all(w in p_clean for w in title_words):
                if any(f_name.lower().endswith(ext) for ext in ('.mp4', '.mkv', '.avi', '.mp3', '.wav', '.flac', '.mov', '.wmv', '.webm')):
                    return True
            # 4. 60%+ of all words matched
            if all_words and len(all_words) >= 2:
                matched_cnt = sum(1 for w in all_words if w in f_clean or w in p_clean)
                if matched_cnt / len(all_words) >= 0.6:
                    return True
            return False

        for root_dir in search_roots:
            if len(results) >= max_results:
                break
            try:
                for root, dirs, files in os.walk(root_dir):
                    dirs[:] = [d for d in dirs if d.lower() not in skip_dirs and not d.startswith('.')]
                    # Check folders first
                    for d in dirs:
                        if matches_query(d, root):
                            full_p = os.path.join(root, d)
                            results.append(full_p)
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
                    # Check files
                    for f in files:
                        if matches_query(f, root):
                            full_p = os.path.join(root, f)
                            results.append(full_p)
                            if len(results) >= max_results:
                                break
                    if len(results) >= max_results:
                        break
            except Exception:
                continue

        if results:
            msg = f"Found {len(results)} matches:\n" + "\n".join(f"- {p}" for p in results)
            return {'success': True, 'files': results, 'message': msg}
        return {'success': False, 'files': [], 'message': f'"{filename}" nahi mila PC pe.'}

    def open_folder(self, folder_name: str, drive: str = None) -> dict:
        """Open a folder/directory in Windows Explorer with smart name resolution.
        Handles direct paths (e.g. 'D:\\Games'), drive letters ('D:', 'D drive'),
        or folder names across drives with phonetic tolerance ('movies holder' -> 'movies').
        """
        raw = folder_name.strip().strip('"').strip("'") if folder_name else ""
        if not raw and not drive:
            subprocess.Popen(['explorer.exe'])
            return {'success': True, 'message': 'File Explorer open kar diya, Sir.'}

        # Phonetic & noise cleanup: strip 'holder', 'folder', 'directory', 'khol', etc.
        clean_name = re.sub(r'\b(holder|holdar|pholder|folder|directory|mein|in|open|khol|kholo|dikhao)\b', '', raw, flags=re.IGNORECASE).strip()

        # Check if clean_name or raw is a drive shortcut (e.g. 'D:', 'D drive', 'd')
        drive_match = re.match(r'^([a-zA-Z])(?:\s*drive|:)?$', clean_name or raw, re.IGNORECASE)
        if drive_match:
            d_path = f"{drive_match.group(1).upper()}:\\"
            if os.path.exists(d_path):
                subprocess.Popen(['explorer.exe', d_path])
                return {'success': True, 'path': d_path, 'message': f"{d_path} open kar diya, Sir."}

        # Check if raw or clean_name exists directly as a path
        for cand in [raw, clean_name]:
            if cand and os.path.exists(cand):
                abs_p = os.path.abspath(cand)
                subprocess.Popen(['explorer.exe', abs_p])
                return {'success': True, 'path': abs_p, 'message': f"{os.path.basename(abs_p) or abs_p} folder open kar diya, Sir."}

        # Determine target search roots
        target_roots = []
        if drive:
            d_letter_m = re.search(r'([a-zA-Z])', drive)
            if d_letter_m:
                d_root = f"{d_letter_m.group(1).upper()}:\\"
                if os.path.exists(d_root):
                    target_roots.append(d_root)

        # Check if clean_name starts with a drive letter, e.g. "D: Games" or "D:\Games"
        d_prefix_m = re.match(r'^([a-zA-Z]):[\\/]*(.*)', clean_name)
        if d_prefix_m:
            letter = d_prefix_m.group(1).upper()
            subpath = d_prefix_m.group(2).strip()
            d_root = f"{letter}:\\"
            if os.path.exists(d_root):
                target_roots = [d_root]
                clean_name = subpath

        if not target_roots:
            home = os.path.expanduser('~')
            hotspots = [
                'D:\\',
                os.path.join(home, 'Downloads'),
                os.path.join(home, 'Desktop'),
                os.path.join(home, 'Documents'),
                os.path.join(home, 'Videos'),
                os.path.join(home, 'Music'),
                os.path.join(home, 'Pictures'),
                'C:\\'
            ]
            target_roots = [d for d in hotspots if os.path.exists(d)]

        search_target = clean_name.lower().strip()

        # 1. Exact match in direct children
        for root in target_roots:
            try:
                for entry in os.listdir(root):
                    entry_path = os.path.join(root, entry)
                    if os.path.isdir(entry_path) and entry.lower() == search_target:
                        subprocess.Popen(['explorer.exe', entry_path])
                        return {'success': True, 'path': entry_path, 'message': f"{entry} folder open kar diya, Sir."}
            except Exception:
                continue

        # 2. Substring match in direct children
        for root in target_roots:
            try:
                for entry in os.listdir(root):
                    entry_path = os.path.join(root, entry)
                    if os.path.isdir(entry_path):
                        if search_target and (search_target in entry.lower() or entry.lower() in search_target):
                            subprocess.Popen(['explorer.exe', entry_path])
                            return {'success': True, 'path': entry_path, 'message': f"{entry} folder open kar diya, Sir."}
            except Exception:
                continue

        # 3. Search 1 level deeper
        for root in target_roots:
            try:
                for parent_entry in os.listdir(root):
                    parent_path = os.path.join(root, parent_entry)
                    if os.path.isdir(parent_path) and not parent_entry.startswith('.') and parent_entry.lower() not in ('$recycle.bin', 'system volume information', 'windows'):
                        try:
                            for child in os.listdir(parent_path):
                                child_path = os.path.join(parent_path, child)
                                if os.path.isdir(child_path):
                                    if search_target and (search_target == child.lower() or search_target in child.lower()):
                                        subprocess.Popen(['explorer.exe', child_path])
                                        return {'success': True, 'path': child_path, 'message': f"{child} folder open kar diya, Sir."}
                        except Exception:
                            continue
            except Exception:
                continue

        # 4. Fallback: If drive specified, just open drive root
        if target_roots:
            subprocess.Popen(['explorer.exe', target_roots[0]])
            return {'success': True, 'path': target_roots[0], 'message': f"'{clean_name}' specific folder nahi mila, {target_roots[0]} open kar diya, Sir."}

        return {'success': False, 'message': f"Folder '{folder_name}' nahi mila PC pe, Sir."}

    def open_file(self, path: str, search_dir: str = None) -> dict:
        """Open any file or directory directly in its default handler. Searches if not direct path."""
        target_path = path.strip().strip('"').strip("'") if path else ""

        # If it's a directory, delegate to open_folder
        if target_path and os.path.isdir(target_path):
            return self.open_folder(target_path)

        if not os.path.exists(target_path):
            found = self.search_files(target_path, search_dir=search_dir, max_results=1)
            if found.get('files'):
                target_path = found['files'][0]
                if os.path.isdir(target_path):
                    return self.open_folder(target_path)
            else:
                return {'success': False, 'message': f"'{path}' file nahi mili PC pe."}

        try:
            os.startfile(target_path)
            return {'success': True, 'file': target_path, 'message': f"{os.path.basename(target_path)} open kar diya."}
        except Exception as e:
            return {'success': False, 'message': f"Could not open {target_path}: {e}"}

    def play_media(self, query: str, search_dir: str = None) -> dict:
        """Specifically search for and play movies, videos, or songs."""
        return self.open_file(query, search_dir=search_dir)

    def read_file(self, path: str, max_chars: int = 1500) -> dict:
        """Read and inspect text content of a file."""
        if not os.path.exists(path):
            found = self.search_files(path, max_results=1)
            if found.get('files'):
                path = found['files'][0]
            else:
                return {'success': False, 'message': f"File '{path}' not found."}

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_chars)
            return {'success': True, 'content': content, 'message': f"File preview ({os.path.basename(path)}):\n{content}"}
        except Exception as e:
            return {'success': False, 'message': f"Error reading file: {e}"}

    def write_file(self, file_path: str, content: str) -> dict:
        """Create or overwrite a file with given content 100% silently in the background.
        Never opens Notepad or moves cursor. Defaults relative paths to Desktop.
        """
        raw_path = file_path.strip().strip('"').strip("'") if file_path else ""
        if not raw_path:
            return {'success': False, 'message': 'File path specify nahi kiya, Sir.'}

        desktop_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        if raw_path.lower().startswith(('desktop\\', 'desktop/')):
            target_path = os.path.join(desktop_dir, re.split(r'[\\/]', raw_path, maxsplit=1)[-1])
        elif not os.path.isabs(raw_path):
            target_path = os.path.join(desktop_dir, raw_path)
        else:
            target_path = os.path.abspath(raw_path)

        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)

            filename = os.path.basename(target_path)
            print(f"[File Created] Silently wrote {len(content)} chars to {target_path}")
            return {
                'success': True,
                'path': target_path,
                'message': f"'{filename}' desktop par silently create kar diya hai, Sir."
            }
        except Exception as e:
            return {'success': False, 'message': f"Failed to create file: {e}"}

    def _resolve_folder_path(self, path: str = None) -> Optional[str]:
        """Smartly resolve a path or folder name across user drives and common hotspots."""
        if not path:
            return os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.exists(path):
            return os.path.abspath(path)

        # Clean noise
        clean = re.sub(r'\b(folder|directory|mein|in|open|khol|kholo|dikhao)\b', '', str(path), flags=re.IGNORECASE).strip()
        for cand in [str(path).strip(), clean]:
            if cand and os.path.exists(cand):
                return os.path.abspath(cand)

        # Extract base folder name (e.g. 'C:\Users\Username\Downloads' -> 'Downloads')
        base_name = os.path.basename(os.path.normpath(clean or str(path))).lower().strip()
        candidates = [c for c in [base_name, clean.lower().strip() if clean else ''] if c]

        # Search drive hotspots
        home = os.path.expanduser('~')
        roots = ['D:\\', os.path.join(home, 'Downloads'), os.path.join(home, 'Desktop'),
                 os.path.join(home, 'Videos'), os.path.join(home, 'Documents'), os.path.join(home, 'Music'), 'C:\\']

        for r in [d for d in roots if os.path.exists(d)]:
            try:
                for entry in os.listdir(r):
                    p = os.path.join(r, entry)
                    if os.path.isdir(p):
                        el = entry.lower()
                        for c in candidates:
                            if el == c or c in el or el in c:
                                return p
            except Exception:
                continue
        return None

    def list_directory(self, path: str = None) -> dict:
        """Inspect a directory to list files, count movies/media/documents, and report contents."""
        target = self._resolve_folder_path(path)
        if not target or not os.path.exists(target):
            return {'success': False, 'message': f"Folder '{path}' nahi mila, Sir."}

        try:
            items = os.listdir(target)
            dirs = []
            files = []
            video_files = []
            audio_files = []
            doc_files = []

            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.flv', '.m4v'}
            audio_exts = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'}
            doc_exts = {'.pdf', '.docx', '.doc', '.txt', '.py', '.json', '.xlsx', '.csv'}

            for item in items:
                p = os.path.join(target, item)
                if os.path.isdir(p):
                    if not item.startswith('.') and item.lower() not in ('$recycle.bin', 'system volume information'):
                        dirs.append(item)
                elif os.path.isfile(p):
                    files.append(item)
                    ext = os.path.splitext(item)[1].lower()
                    if ext in video_exts:
                        video_files.append(item)
                    elif ext in audio_exts:
                        audio_files.append(item)
                    elif ext in doc_exts:
                        doc_files.append(item)

            folder_name = os.path.basename(target) or target
            summary_parts = []
            if video_files:
                summary_parts.append(f"{len(video_files)} movie/video files")
            if audio_files:
                summary_parts.append(f"{len(audio_files)} audio files")
            if doc_files:
                summary_parts.append(f"{len(doc_files)} document/code files")
            if dirs:
                summary_parts.append(f"{len(dirs)} subfolders: {', '.join(dirs[:5])}")

            summary_str = ", ".join(summary_parts) if summary_parts else f"{len(files)} files, {len(dirs)} folders"
            sample_titles = [os.path.splitext(f)[0] for f in (video_files if video_files else files)[:8]]

            msg = f"In '{folder_name}' ({target}): Total {len(files)} files ({summary_str}). Sample titles: {', '.join(sample_titles)}."
            return {
                'success': True,
                'path': target,
                'folder_name': folder_name,
                'total_files': len(files),
                'video_count': len(video_files),
                'audio_count': len(audio_files),
                'doc_count': len(doc_files),
                'subfolders': dirs,
                'sample_titles': sample_titles,
                'message': msg
            }
        except Exception as e:
            return {'success': False, 'message': f"Folder '{target}' inspect karte waqt error: {e}"}

    # =========================================================================
    # 2. HARDWARE, DRIVES & RUNNING PROCESSES KNOWLEDGE
    # =========================================================================

    def get_disk_drives(self) -> dict:
        """Get storage status for all drives (C:, D:, E:, etc.)."""
        if not psutil:
            return {'success': False, 'message': 'psutil not available.'}
        try:
            drives = []
            for part in psutil.disk_partitions(all=False):
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    total_gb = round(usage.total / (1024 ** 3), 1)
                    drives.append(f"{part.device} ({free_gb} GB free of {total_gb} GB, {usage.percent}% used)")
                except Exception:
                    continue
            msg = "Drive Storage: " + " | ".join(drives)
            return {'success': True, 'drives': drives, 'message': msg}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def list_running_processes(self, top_n: int = 10) -> dict:
        """List top memory and CPU consuming processes."""
        if not psutil:
            return {'success': False, 'message': 'psutil not available.'}
        try:
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except Exception:
                    continue

            # Sort by memory percent
            procs = sorted(procs, key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)[:top_n]
            summary = [f"{p['name']} ({round(p['memory_percent'], 1)}% RAM)" for p in procs if p.get('name')]
            return {'success': True, 'processes': summary, 'message': "Top active apps: " + ", ".join(summary[:5])}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def kill_process(self, process_name: str) -> dict:
        """Terminate a stuck or requested process."""
        name = process_name.lower().replace('.exe', '').strip()
        os.system(f'taskkill /F /IM "{name}.exe" /T >nul 2>&1')
        return {'success': True, 'message': f"Terminated process '{name}'."}

    # =========================================================================
    # 3. POWERSHELL & SHELL COMMAND AUTOMATION
    # =========================================================================

    def run_powershell_command(self, cmd: str) -> dict:
        """Execute a safe PowerShell / CMD command on the system and capture output."""
        try:
            res = subprocess.run(
                ['powershell', '-Command', cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            out = res.stdout.strip() or res.stderr.strip()
            return {'success': res.returncode == 0, 'output': out, 'message': out[:300]}
        except Exception as e:
            return {'success': False, 'message': f"Shell error: {e}"}

    def lock_pc(self) -> dict:
        """Lock the Windows workstation."""
        if self.user32:
            self.user32.LockWorkStation()
            return {'success': True, 'message': "PC locked."}
        os.system('rundll32.exe user32.dll,LockWorkStation')
        return {'success': True, 'message': "PC locked."}

    def empty_recycle_bin(self) -> dict:
        """Empty Windows Recycle Bin."""
        try:
            self.run_powershell_command("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
            return {'success': True, 'message': "Recycle Bin empty kar diya bhai!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def get_network_info(self) -> dict:
        """Get local IP and network status."""
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return {'success': True, 'ip': ip, 'hostname': hostname, 'message': f"Connected on IP: {ip} ({hostname})"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def toggle_wifi(self, state: str = "off") -> dict:
        """Turn Wi-Fi on or off, or disconnect without admin rights."""
        netsh_exe = r"C:\Windows\System32\netsh.exe"
        st = state.lower().strip() if state else "off"
        try:
            if st in ('off', 'disable', 'disconnect', 'band'):
                res = subprocess.run([netsh_exe, "wlan", "disconnect"], capture_output=True, text=True)
                return {'success': True, 'message': 'Wi-Fi disconnect kar diya hai, Sir.'}
            else:
                subprocess.Popen(['powershell', '-Command', 'Start-Process ms-settings:network-wifi'])
                return {'success': True, 'message': 'Wi-Fi settings open kar diya hai, Sir.'}
        except Exception as e:
            return {'success': False, 'message': f"Wi-Fi toggle error: {e}"}

    def toggle_bluetooth(self, state: str = "off") -> dict:
        """Open Bluetooth Settings or Quick Settings to toggle Bluetooth."""
        try:
            subprocess.Popen(['powershell', '-Command', 'Start-Process ms-settings:bluetooth'])
            return {'success': True, 'message': 'Bluetooth settings open kar diya hai, Sir.'}
        except Exception as e:
            return {'success': False, 'message': f"Bluetooth toggle error: {e}"}

    # =========================================================================
    # 4. UNIVERSAL APP DISCOVERY
    # =========================================================================

    def find_installed_app_path(self, app_name: str) -> Optional[str]:
        query = app_name.lower().strip().replace('launcher', '').replace('app', '').strip()

        if app_name.lower() in self.APPS:
            mapped = self.APPS[app_name.lower()]
            which_path = shutil.which(mapped)
            if which_path:
                return which_path

        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                with winreg.OpenKey(root_key, sub) as key:
                    count = winreg.QueryInfoKey(key)[0]
                    for i in range(count):
                        try:
                            app_key_name = winreg.EnumKey(key, i)
                            if query in app_key_name.lower():
                                with winreg.OpenKey(key, app_key_name) as app_k:
                                    val, _ = winreg.QueryValueEx(app_k, "")
                                    if val and os.path.exists(val.strip('"')):
                                        return val.strip('"')
                        except Exception:
                            continue
            except Exception:
                pass

        start_menu_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs")
        ]
        for s_dir in start_menu_dirs:
            if os.path.exists(s_dir):
                for root, _, files in os.walk(s_dir):
                    for file in files:
                        if query in file.lower() and file.endswith(('.lnk', '.exe')):
                            return os.path.join(root, file)

        common_locations = [
            os.path.expandvars(rf"%LOCALAPPDATA%\Programs\{app_name}"),
            os.path.expandvars(rf"%APPDATA%\{app_name}"),
            os.path.expandvars(rf"%PROGRAMFILES%\{app_name}"),
            os.path.expandvars(rf"%PROGRAMFILES(X86)%\{app_name}"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
        ]
        for loc in common_locations:
            if os.path.exists(loc):
                if os.path.isfile(loc):
                    return loc
                for root, _, files in os.walk(loc):
                    for f in files:
                        if query in f.lower() and f.endswith('.exe'):
                            return os.path.join(root, f)

        resolved = shutil.which(f"{query}.exe") or shutil.which(query)
        if resolved:
            return resolved

        # Check local Games directories (e.g. D:\GAMES, C:\GAMES)
        for games_dir in [r"D:\GAMES", r"C:\GAMES", os.path.expanduser(r"~\Games")]:
            if os.path.exists(games_dir):
                q_words = [w for w in re.split(r'\s+', query.lower()) if len(w) > 2 or w.isdigit()]
                best_folder = None
                best_score = 0
                try:
                    for folder in os.listdir(games_dir):
                        full_f = os.path.join(games_dir, folder)
                        if os.path.isdir(full_f):
                            score = sum(1 for w in q_words if w in folder.lower())
                            if score > best_score and score >= 2:
                                best_score = score
                                best_folder = full_f

                    if best_folder:
                        exe_candidates = []
                        for root, _, files in os.walk(best_folder):
                            for f in files:
                                if f.lower().endswith('.exe') and not any(k in f.lower() for k in ['unins', 'crash', 'reporter', 'setup', 'update', 'directx', 'install', 'tool']):
                                    exe_candidates.append(os.path.join(root, f))
                        if exe_candidates:
                            sp = next((e for e in exe_candidates if 'sp.exe' in e.lower() or 'game.exe' in e.lower()), None)
                            return sp or exe_candidates[0]
                        return best_folder
                except Exception:
                    pass

        return None

    # =========================================================================
    # 5. WIN32 WINDOW MANAGEMENT
    # =========================================================================

    def _get_top_level_windows(self) -> List[Tuple[int, str, str]]:
        if not self.user32:
            return []

        results = []
        GW_OWNER = 4
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_windows_callback(hwnd, _):
            if self.user32.GetWindow(hwnd, GW_OWNER):
                return True
            if self.user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
                return True
            if not self.user32.IsWindowVisible(hwnd) and not self.user32.IsIconic(hwnd):
                return True

            length = self.user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value

            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            exe_name = ""
            if pid.value:
                hproc = self.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
                if hproc:
                    try:
                        pbuf = ctypes.create_unicode_buffer(4096)
                        sz = wintypes.DWORD(len(pbuf))
                        if self.kernel32.QueryFullProcessImageNameW(hproc, 0, pbuf, ctypes.byref(sz)):
                            exe_name = os.path.basename(pbuf.value).lower()
                    finally:
                        self.kernel32.CloseHandle(hproc)

            if title or exe_name:
                results.append((int(hwnd), title, exe_name))
            return True

        self.user32.EnumWindows(enum_windows_callback, 0)
        return results

    def find_window_hwnd(self, search: str) -> Optional[int]:
        search = search.lower().strip()
        windows = self._get_top_level_windows()

        # Resolve app name to exe name via APPS dict for better matching
        resolved_exe = self.APPS.get(search, '').lower()

        for hwnd, title, exe in windows:
            if search == title.lower() or search == exe or f"{search}.exe" == exe:
                return hwnd

        for hwnd, title, exe in windows:
            if search in title.lower() or search in exe:
                return hwnd

        # Try matching by resolved exe name (e.g. "file explorer" → "explorer.exe")
        if resolved_exe:
            for hwnd, title, exe in windows:
                if exe == resolved_exe or resolved_exe.replace('.exe', '') in exe:
                    return hwnd

        return None

    def wait_for_window(self, search: str, timeout_seconds: float = 3.0) -> Optional[int]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            hwnd = self.find_window_hwnd(search)
            if hwnd:
                return hwnd
            time.sleep(0.05)
        return None

    def focus_window_hwnd(self, hwnd: int) -> bool:
        if not self.user32 or not hwnd:
            return False

        try:
            self.user32.ShowWindow(hwnd, SW_RESTORE)
            fg = self.user32.GetForegroundWindow()
            tid_target = self.user32.GetWindowThreadProcessId(hwnd, None)
            tid_fg = self.user32.GetWindowThreadProcessId(fg, None) if fg else 0

            if tid_fg and tid_target and tid_fg != tid_target:
                self.user32.AttachThreadInput(tid_fg, tid_target, True)

            self.user32.SetForegroundWindow(hwnd)

            if tid_fg and tid_target and tid_fg != tid_target:
                self.user32.AttachThreadInput(tid_fg, tid_target, False)

            return True
        except Exception:
            return False

    def snap_window_exact(self, hwnd: int, position: str) -> bool:
        if not self.user32 or not hwnd:
            return False

        self.focus_window_hwnd(hwnd)
        w = self.screen_width
        h = self.screen_height
        pos = position.lower().strip()

        x, y, target_w, target_h = 0, 0, w, h
        flags = SWP_SHOWWINDOW | SWP_FRAMECHANGED

        if pos in ['left', 'baye', 'left-half']:
            x, y, target_w, target_h = 0, 0, w // 2, h
            self.user32.ShowWindow(hwnd, SW_RESTORE)
            self.user32.SetWindowPos(hwnd, HWND_TOP, x, y, target_w, target_h, flags)
        elif pos in ['right', 'daye', 'right-half']:
            x, y, target_w, target_h = w // 2, 0, w // 2, h
            self.user32.ShowWindow(hwnd, SW_RESTORE)
            self.user32.SetWindowPos(hwnd, HWND_TOP, x, y, target_w, target_h, flags)
        elif pos in ['maximize', 'max', 'full']:
            self.user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
        elif pos in ['minimize', 'min', 'hide']:
            self.user32.ShowWindow(hwnd, SW_SHOWMINIMIZED)
        else:
            return False

        return True

    def open_app(self, app_name: str, url: str = None) -> dict:
        app_raw = app_name.strip() if app_name else ""
        app_key = app_raw.lower()

        # 1. Intercept Windows Explorer invocations: "explorer D:\Games", "file explorer D:\Games"
        m_exp = re.match(r'^(?:file\s+)?explorer(?:\.exe)?\s+(.+)$', app_raw, re.IGNORECASE)
        if m_exp:
            path_part = m_exp.group(1).strip().strip('"').strip("'")
            return self.open_folder(path_part)

        # 2. Intercept plain drive commands passed to open_app
        drive_m = re.match(r'^([a-zA-Z])(?:\s*drive|:)?$', app_key)
        if drive_m:
            return self.open_folder(f"{drive_m.group(1).upper()}:\\")

        # 3. Intercept explicit path or existing folder/file
        if (':\\' in app_raw or ':/' in app_raw) and os.path.exists(app_raw):
            if os.path.isdir(app_raw):
                return self.open_folder(app_raw)
            else:
                return self.open_file(app_raw)

        if url:
            browser_exe = self.find_installed_app_path(app_key)
            if browser_exe:
                try:
                    subprocess.Popen([browser_exe, url])
                    return {'success': True, 'message': f"Opened {url} in {app_name}."}
                except Exception:
                    pass
            webbrowser.open(url)
            return {'success': True, 'message': f"Opened {url}."}

        discovered_path = self.find_installed_app_path(app_name)
        if discovered_path:
            try:
                if discovered_path.endswith('.lnk'):
                    os.startfile(discovered_path)
                elif os.path.isdir(discovered_path):
                    return self.open_folder(discovered_path)
                else:
                    working_dir = os.path.dirname(discovered_path)
                    subprocess.Popen(f'"{discovered_path}"', shell=True, cwd=working_dir)
                return {'success': True, 'message': f"Opened {app_name}."}
            except Exception as e:
                print(f"[Launch Path Error] {e}")

        cmd = self.APPS.get(app_key, app_name)
        try:
            if hasattr(os, 'startfile'):
                os.startfile(cmd)
                return {'success': True, 'message': f"Opened {app_name}."}
        except Exception:
            pass

        try:
            subprocess.Popen(f'start "" "{cmd}"', shell=True)
            return {'success': True, 'message': f"Started {app_name}."}
        except Exception:
            pass

        try:
            subprocess.Popen(['powershell', '-Command', f'Start-Process "{app_name}"'], shell=True)
            return {'success': True, 'message': f"Launched {app_name}."}
        except Exception as e:
            return {'success': False, 'message': f"Could not launch {app_name}: {e}"}

    def open_url(self, url: str, browser: str = None) -> dict:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        if browser:
            browser_exe = self.find_installed_app_path(browser)
            if browser_exe:
                try:
                    subprocess.Popen([browser_exe, url])
                    return {'success': True, 'message': f"Opened {url} in {browser}."}
                except Exception as e:
                    print(f"[Open URL Error] {e}")

        webbrowser.open(url)
        return {'success': True, 'message': f"Opened {url}."}

    def snap_window(self, window_title: str, position: str) -> dict:
        hwnd = self.wait_for_window(window_title, timeout_seconds=1.5)
        if not hwnd:
            hwnd = self.user32.GetForegroundWindow() if self.user32 else None

        if hwnd and self.snap_window_exact(hwnd, position):
            return {'success': True, 'message': f'Snapped "{window_title}" to {position}.'}

        if pyautogui:
            pos = position.lower()
            if 'left' in pos:
                pyautogui.hotkey('win', 'left')
            elif 'right' in pos:
                pyautogui.hotkey('win', 'right')
            elif 'max' in pos:
                pyautogui.hotkey('win', 'up')
            return {'success': True, 'message': f'Snapped via hotkey to {position}.'}

        return {'success': False, 'message': f'Could not snap "{window_title}".'}

    def focus_window(self, window_title: str) -> dict:
        hwnd = self.find_window_hwnd(window_title)
        if hwnd and self.focus_window_hwnd(hwnd):
            return {'success': True, 'message': f'Focused "{window_title}".'}
        return {'success': False, 'message': f'Window "{window_title}" not found.'}

    def close_app(self, window_title: str) -> dict:
        hwnd = self.find_window_hwnd(window_title)
        if hwnd and self.user32:
            WM_CLOSE = 0x0010
            self.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            return {'success': True, 'message': f'Closed "{window_title}".'}

        os.system(f'taskkill /F /IM "{window_title}.exe" /T >nul 2>&1')
        return {'success': True, 'message': f'Closed {window_title}.'}

    def minimize_window(self, window_title: str) -> dict:
        hwnd = self.find_window_hwnd(window_title)
        if hwnd and self.user32:
            self.user32.ShowWindow(hwnd, SW_SHOWMINIMIZED)
            return {'success': True, 'message': f'Minimized "{window_title}".'}
        return {'success': False, 'message': f'Window "{window_title}" not found.'}

    def list_windows(self) -> List[str]:
        windows = self._get_top_level_windows()
        titles = [t for _, t, _ in windows if t and t.strip()]
        ignore = ['Program Manager', 'Settings', 'Windows Input Experience', 'Default IME']
        return [t for t in titles if t not in ignore]

    def get_active_window(self) -> str:
        if not self.user32:
            return ""
        hwnd = self.user32.GetForegroundWindow()
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        return ""

    # =========================================================================
    # 6. INPUT EMULATION
    # =========================================================================

    def type_text(self, text: str) -> dict:
        if not text:
            return {'success': True, 'message': 'Empty text.'}
        try:
            if pyperclip and (any(ord(c) >= 128 for c in text) or '\n' in text):
                pyperclip.copy(text)
                time.sleep(0.03)
                if pyautogui:
                    pyautogui.hotkey('ctrl', 'v')
            elif pyautogui:
                pyautogui.write(text, interval=0.005)
            return {'success': True, 'message': 'Text typed.'}
        except Exception as e:
            return {'success': False, 'message': f"Type text error: {e}"}

    def press_keys(self, keys: str) -> dict:
        if not pyautogui:
            return {'success': False, 'message': 'pyautogui is not available.'}
        try:
            parts = [k.strip().lower() for k in keys.split('+')]
            pyautogui.hotkey(*parts)
            return {'success': True, 'message': f'Pressed: {keys}'}
        except Exception as e:
            return {'success': False, 'message': f"Press keys error: {e}"}

    def click_at(self, x: int, y: int, button: str = 'left') -> dict:
        if pyautogui:
            pyautogui.click(x=x, y=y, button=button)
            return {'success': True, 'message': f'Clicked at ({x}, {y}).'}
        return {'success': False, 'message': 'pyautogui not available.'}

    def scroll(self, direction: str = 'down', amount: int = 3) -> dict:
        if pyautogui:
            clicks = amount * 120
            if direction.lower() == 'down':
                clicks = -clicks
            pyautogui.scroll(clicks)
            return {'success': True, 'message': f'Scrolled {direction}.'}
        return {'success': False, 'message': 'pyautogui not available.'}

    def search_web(self, query: str, browser: str = None) -> dict:
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        return self.open_url(url, browser=browser)

    def take_screenshot(self, save_to_desktop: bool = True):
        if not ImageGrab:
            return None
        try:
            img = ImageGrab.grab()
            if save_to_desktop:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                filename = f"Screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                img.save(os.path.join(desktop, filename))
            return img
        except Exception:
            return None

    def get_time(self) -> str:
        return datetime.datetime.now().strftime('%I:%M %p')

    def get_date(self) -> str:
        return datetime.datetime.now().strftime('%B %d, %Y')

    def system_info(self) -> dict:
        if not psutil:
            return {'success': False, 'message': 'psutil not installed'}
        try:
            cpu = psutil.cpu_percent(interval=0.2)
            mem = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            battery_str = f"{batt.percent}%" if batt else "Plugged In"
            return {
                'success': True,
                'cpu_percent': cpu,
                'memory_percent': mem,
                'battery': battery_str,
                'message': f"CPU: {cpu}%, RAM: {mem}%, Battery: {battery_str}"
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def set_volume(self, level: int) -> dict:
        if not pyautogui:
            return {'success': False, 'message': 'pyautogui not available.'}
        try:
            level = max(0, min(100, int(level)))
            pyautogui.press('volumedown', presses=50)
            steps = level // 2
            if steps > 0:
                pyautogui.press('volumeup', presses=steps)
            return {'success': True, 'message': f'Volume set to {level}%.'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # =========================================================================
    # 7. AUTONOMOUS HYBRID CLICKING & DOMAIN AUTOMATION
    # =========================================================================

    def set_screen_reader(self, screen_reader):
        """Bind ScreenReader instance for visual grounding."""
        self.screen_reader = screen_reader

    def find_and_click(self, element_description: str, double_click: bool = False, button: str = 'left') -> dict:
        """Find any visual element on screen via Gemini Vision Grounding and click it."""
        if not self.screen_reader:
            return {'success': False, 'message': 'Screen reader not configured.'}
        return self.screen_reader.find_and_click(element_description, double_click=double_click, button=button)

    def _resolve_yt_video_id(self, query: str) -> Optional[str]:
        """
        Quickly resolve the top YouTube/YouTube Music video ID for any song query in ~0.6-0.9s.
        Fetches the initial search result payload headlessly and extracts the top 11-char ID.
        """
        try:
            search_query = urllib.parse.quote_plus(f"{query} audio")
            search_url = f"https://www.youtube.com/results?search_query={search_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                if matches:
                    return matches[0]
        except Exception as e:
            print(f"[YouTube Music Video ID Resolver] Notice: {e}")
        return None

    def play_youtube_music(self, query: str) -> dict:
        """
        Autonomously play a song or music track on YouTube Music.
        Resolves direct 11-character Video ID for instant autoplay on music.youtube.com/watch?v=...
        Falls back to search results if offline or unresolvable.
        """
        q_raw = query.strip()
        # Clean noise words: "play", "chalao", "gaana", "song", "on youtube music", "youtube music pe"
        noise = [
            r'\bplay\b', r'\bchalao\b', r'\bchala do\b', r'\blaga do\b', r'\bsunao\b',
            r'\bon\s+youtube\s+music\b', r'\byoutube\s+music\s+pe\b', r'\byoutube\s+music\s+par\b',
            r'\byoutube\s+music\b', r'\bgaana\b', r'\bsong\b', r'\btrack\b', r'\bmusic\b'
        ]
        q_clean = q_raw
        for pattern in noise:
            q_clean = re.sub(pattern, '', q_clean, flags=re.IGNORECASE).strip()
        if not q_clean:
            q_clean = q_raw or "Bollywood hits"

        # Step 1: Resolve direct video ID for instant autoplay
        video_id = self._resolve_yt_video_id(q_clean)

        if video_id:
            # Direct song playback URL — instantly autoplays the song!
            play_url = f"https://music.youtube.com/watch?v={video_id}"
            print(f"[YouTube Music] Resolved video ID: {video_id}. Direct play URL: {play_url}")
            self.open_url(play_url)
        else:
            # Fallback to search query page if resolution timed out
            fallback_url = f"https://music.youtube.com/search?q={urllib.parse.quote(q_clean)}"
            print(f"[YouTube Music] Resolution fallback. Opening search URL: {fallback_url}")
            self.open_url(fallback_url)

        return {
            'success': True,
            'message': f"Playing '{q_clean}' on YouTube Music.",
            'voice_text': 'Chala diya Boss!'
        }

    def automate_steam(self, game_name: str, action: str = "install") -> dict:
        """
        Autonomously interact with Steam for game discovery, installation, and launching.
        Uses Steam protocol handlers combined with visual button grounding.
        """
        g_raw = game_name.strip()
        noise = [
            r'\bdownload\b', r'\binstall\b', r'\bplay\b', r'\bopen\b', r'\bkholo\b',
            r'\bchalao\b', r'\bgame\b', r'\bsteam\s+pe\b', r'\bon\s+steam\b', r'\bsteam\b'
        ]
        g_clean = g_raw
        for pattern in noise:
            g_clean = re.sub(pattern, '', g_clean, flags=re.IGNORECASE).strip()
        if not g_clean:
            g_clean = g_raw

        act = action.lower().strip()
        if act in ('install', 'download', 'search', 'buy', 'open'):
            url = f"steam://url/StoreSearchPage?term={urllib.parse.quote(g_clean)}"
            try:
                os.startfile(url)
            except Exception:
                self.open_app('steam')

            time.sleep(2.0)
            self.focus_window("Steam")

            if act in ('install', 'download'):
                time.sleep(1.0)
                if self.screen_reader:
                    card_coords = self.screen_reader.locate_element(f"first search result card for {g_clean} in Steam store")
                    if card_coords and pyautogui:
                        pyautogui.click(card_coords[0], card_coords[1])
                        time.sleep(2.0)
                        btn_coords = self.screen_reader.locate_element("green Install or Play Game or Download button in Steam")
                        if btn_coords:
                            pyautogui.click(btn_coords[0], btn_coords[1])
                            return {
                                'success': True,
                                'message': f"Started download/install for '{g_clean}' on Steam.",
                                'voice_text': 'Download shuru kar diya Boss!'
                            }

                return {
                    'success': True,
                    'message': f"Opened Steam store for '{g_clean}'.",
                    'voice_text': 'Download shuru kar diya Boss!'
                }
            else:
                return {
                    'success': True,
                    'message': f"Opened Steam for '{g_clean}'.",
                    'voice_text': 'Khol diya Boss!'
                }
        else:
            try:
                os.startfile("steam://open/games")
            except Exception:
                self.open_app('steam')

            time.sleep(1.5)
            self.focus_window("Steam")
            if self.screen_reader:
                play_coords = self.screen_reader.locate_element(f"Play button or title for {g_clean} in Steam library")
                if play_coords and pyautogui:
                    pyautogui.click(play_coords[0], play_coords[1])
            return {
                'success': True,
                'message': f"Launched '{g_clean}' on Steam.",
                'voice_text': 'Chala diya Boss!'
            }

