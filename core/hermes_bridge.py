"""
JARVIS Hermes Bridge
Connects JARVIS to Nous Research's Hermes Agent.
Executes autonomous multi-step tasks in the background without blocking voice/UI.
"""

import os
import subprocess
import threading
import time
import uuid
from typing import Dict, Any, Optional, Callable


HERMES_HOME = os.path.expandvars(r"%LOCALAPPDATA%\hermes")
HERMES_DIR = os.path.join(HERMES_HOME, "hermes-agent")
HERMES_VENV_PYTHON = os.path.join(HERMES_DIR, ".venv", "Scripts", "python.exe")
HERMES_EXE = os.path.join(HERMES_HOME, "bin", "hermes.exe")
HERMES_CMD = os.path.join(HERMES_HOME, "bin", "hermes.cmd")
HERMES_BIN = HERMES_EXE if os.path.exists(HERMES_EXE) else HERMES_CMD


class HermesBridge:
    """Bridge for delegating autonomous tasks to Hermes Agent."""

    def __init__(self, voice_output=None):
        self.voice_output = voice_output
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set_voice_output(self, voice_output):
        """Set or update voice output reference for completion alerts."""
        self.voice_output = voice_output

    def is_installed(self) -> bool:
        """Check if Hermes Agent is installed."""
        if os.path.exists(HERMES_BIN):
            return True
        if os.path.exists(HERMES_VENV_PYTHON):
            return True
        if os.path.exists(HERMES_DIR):
            return True
        return False

    def get_hermes_cmd(self) -> list:
        """Get the executable command for running Hermes."""
        # 1. Check direct binary
        if os.path.exists(HERMES_BIN):
            return [HERMES_BIN]
        # 2. Check virtualenv runner
        if os.path.exists(HERMES_VENV_PYTHON):
            return [HERMES_VENV_PYTHON, "-m", "hermes_cli.main"]
        # 3. Fallback to PATH hermes
        return ["hermes"]

    def run_task_async(
        self,
        task_prompt: str,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Launch an autonomous Hermes task in a non-blocking background thread.
        JARVIS responds to the user immediately, while Hermes works in the background.
        """
        task_id = str(uuid.uuid4())[:8]
        task_info = {
            "id": task_id,
            "prompt": task_prompt,
            "status": "running",
            "start_time": time.time(),
            "output": "",
            "error": None
        }

        with self._lock:
            self.active_tasks[task_id] = task_info

        worker_thread = threading.Thread(
            target=self._task_worker,
            args=(task_id, task_prompt, on_complete),
            daemon=True
        )
        worker_thread.start()

        return {
            "success": True,
            "task_id": task_id,
            "message": f"Hermes task {task_id} initiated in the background.",
            "prompt": task_prompt
        }

    def _task_worker(
        self,
        task_id: str,
        task_prompt: str,
        on_complete: Optional[Callable[[Dict[str, Any]], None]]
    ):
        """Background execution worker for Hermes."""
        cmd = [HERMES_BIN, "-z", task_prompt, "--yolo", "-t", "file,terminal,code_execution,web"]
        
        try:
            # Run Hermes subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=HERMES_DIR if os.path.exists(HERMES_DIR) else None,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )

            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            success = (process.returncode == 0)

            with self._lock:
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "completed" if success else "failed"
                    self.active_tasks[task_id]["output"] = stdout
                    self.active_tasks[task_id]["error"] = stderr
                    self.active_tasks[task_id]["exit_code"] = process.returncode

            result_summary = stdout[-300:] if stdout else ("Task finished" if success else stderr[-300:])

            # Notify through voice if available
            if self.voice_output:
                try:
                    notification = f"Sir, Hermes has completed your task. {result_summary[:120]}" if success else "Sir, Hermes encountered an issue executing your background task."
                    self.voice_output.speak_sync(notification)
                except Exception as e:
                    print(f"[HermesBridge] Voice alert error: {e}")

            if on_complete:
                on_complete({
                    "task_id": task_id,
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr
                })

        except Exception as e:
            with self._lock:
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "error"
                    self.active_tasks[task_id]["error"] = str(e)

            print(f"[HermesBridge] Worker exception for task {task_id}: {e}")
            if self.voice_output:
                try:
                    self.voice_output.speak_sync("Sir, Hermes task failed due to an execution error.")
                except Exception:
                    pass

    def run_task_sync(self, task_prompt: str, timeout: int = 180) -> Dict[str, Any]:
        """Run task synchronously and wait for results."""
        cmd = [HERMES_BIN, "-z", task_prompt, "--yolo", "-t", "file,terminal,code_execution,web"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=HERMES_DIR if os.path.exists(HERMES_DIR) else None,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Hermes task timed out after {timeout} seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a background task."""
        with self._lock:
            return self.active_tasks.get(task_id)


# Singleton instance
hermes_bridge = HermesBridge()
