"""
Social Bridge Server — On-Demand Featherweight IPC Bridge between Browser (Tampermonkey)
and FRIDAY Gatekeeper Brain on 127.0.0.1:8765.
Starts in < 10ms on-demand, consumes 0% CPU while waiting, and cleanly shuts down when stopped.
"""

import json
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)

PORT = 8765
HOST = "127.0.0.1"


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server so incoming requests never block each other."""
    daemon_threads = True
    allow_reuse_address = True


class BridgeRequestHandler(BaseHTTPRequestHandler):
    """Handles incoming CORS requests from Tampermonkey userscript."""

    server_instance: 'SocialBridgeServer' = None

    def log_message(self, format, *args):
        """Suppress default stdout access logging to keep terminal clean."""
        pass

    def _set_cors_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests from browser."""
        self._set_cors_headers(204)

    def do_GET(self):
        """Health and status inspection endpoint."""
        if self.path == "/status":
            srv = self.server_instance
            data = {
                "running": True,
                "auto_chat_enabled": srv.auto_chat_enabled if srv else False,
                "active_contact": srv.active_contact if srv else None,
                "last_active": srv.last_active_time if srv else 0
            }
            body = json.dumps(data).encode("utf-8")
            self._set_cors_headers(200)
            self.wfile.write(body)
        elif self.path == "/pending_outbound":
            srv = self.server_instance
            pending = srv.pop_pending_outbound() if srv else None
            if pending:
                data = {
                    "has_pending": True,
                    "message": pending.get("message", ""),
                    "contact": pending.get("contact", "")
                }
            else:
                data = {"has_pending": False}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._set_cors_headers(200)
            self.wfile.write(body)
        else:
            self._set_cors_headers(404)
            self.wfile.write(b'{"error": "not found"}')

    def do_POST(self):
        """Process incoming chat messages or control commands."""
        if self.path == "/incoming":
            srv = self.server_instance
            if not srv:
                self._set_cors_headers(503)
                self.wfile.write(b'{"should_reply": false, "error": "Server not ready"}')
                return

            srv.touch_activity()

            try:
                content_length = int(self.headers.get('Content-Length', 0))
                raw_body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(raw_body) if raw_body else {}
            except Exception as e:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({"should_reply": False, "error": str(e)}).encode('utf-8'))
                return

            sender = data.get("sender", "Friend")
            text = data.get("text", "").strip()
            url = data.get("url", "")

            print(f"\n[Bridge HTTP Server] >>> Incoming from Browser ({sender}): '{text}'")

            # Delegate to Friday callback
            response_data = {"should_reply": False}
            if srv.incoming_callback and text:
                try:
                    response_data = srv.incoming_callback(sender, text, url)
                except Exception as ex:
                    logger.error(f"[BridgeRequestHandler Error] {ex}")
                    response_data = {"should_reply": False, "error": str(ex)}

            reply_text = response_data.get("reply", "")
            print(f"[Bridge HTTP Server] <<< Replying to Browser: '{reply_text}' (should_reply: {response_data.get('should_reply')})")

            body = json.dumps(response_data, ensure_ascii=False).encode("utf-8")
            self._set_cors_headers(200)
            self.wfile.write(body)

        elif self.path == "/stop":
            srv = self.server_instance
            if srv:
                srv.stop()
            self._set_cors_headers(200)
            self.wfile.write(b'{"stopped": true}')

        else:
            self._set_cors_headers(404)
            self.wfile.write(b'{"error": "not found"}')


class SocialBridgeServer:
    """Manages the lifecycle of the local IPC bridge server on 127.0.0.1:8765."""

    def __init__(self, incoming_callback: Optional[Callable[[str, str, str], Dict[str, Any]]] = None):
        self.incoming_callback = incoming_callback
        self.server: Optional[ThreadedHTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.auto_chat_enabled = False
        self.active_contact = None
        self.last_active_time = 0
        self.inactivity_timeout = 600  # 10 minutes auto-shutdown
        self.pending_outbound: Optional[Dict[str, Any]] = None

    def set_callback(self, callback: Callable[[str, str, str], Dict[str, Any]]):
        self.incoming_callback = callback

    def set_pending_outbound(self, message: str, contact: str = ""):
        """Queue an initial intro or greeting message for the browser userscript to pick up on page load."""
        self.pending_outbound = {
            "message": message.strip(),
            "contact": contact.strip(),
            "timestamp": time.time()
        }
        logger.info(f"[SocialBridgeServer] Queued pending outbound message for '{contact}': '{message}'")

    def pop_pending_outbound(self) -> Optional[Dict[str, Any]]:
        """Retrieve and clear the pending outbound message if present."""
        if getattr(self, 'pending_outbound', None):
            res = self.pending_outbound
            self.pending_outbound = None
            return res
        return None

    def touch_activity(self):
        self.last_active_time = time.time()

    def start(self, contact: str = None) -> bool:
        """Starts the bridge server on 127.0.0.1:8765 on a background daemon thread in < 10ms."""
        if self.is_running:
            self.auto_chat_enabled = True
            if contact:
                self.active_contact = contact.lower().strip()
            self.touch_activity()
            return True

        try:
            # Bind handler to this server instance
            handler_cls = type('BoundHandler', (BridgeRequestHandler,), {'server_instance': self})
            self.server = ThreadedHTTPServer((HOST, PORT), handler_cls)
            self.is_running = True
            self.auto_chat_enabled = True
            self.active_contact = contact.lower().strip() if contact else None
            self.touch_activity()

            self.server_thread = threading.Thread(target=self._run_server, daemon=True, name="SocialBridgeServer")
            self.server_thread.start()

            # Start background inactivity watchdog
            threading.Thread(target=self._watchdog_loop, daemon=True, name="SocialBridgeWatchdog").start()

            logger.info(f"[SocialBridgeServer] Listening on http://{HOST}:{PORT} (Active for: {self.active_contact})")
            return True
        except Exception as e:
            logger.error(f"[SocialBridgeServer Start Error] {e}")
            self.is_running = False
            self.server = None
            return False

    def _run_server(self):
        try:
            if self.server:
                self.server.serve_forever()
        except Exception:
            pass
        finally:
            self.is_running = False

    def _watchdog_loop(self):
        """Auto-shuts down server if no messages occur for 10 minutes."""
        while self.is_running and self.auto_chat_enabled:
            time.sleep(15)
            if self.last_active_time and (time.time() - self.last_active_time > self.inactivity_timeout):
                logger.info("[SocialBridgeServer] 10 minutes inactivity detected. Auto-stopping bridge.")
                self.stop()
                break

    def stop(self) -> bool:
        """Shuts down the server and cleanly frees port 8765."""
        if not self.is_running:
            self.auto_chat_enabled = False
            self.active_contact = None
            return True

        self.auto_chat_enabled = False
        self.active_contact = None
        self.is_running = False

        if self.server:
            try:
                # Stop serve_forever loop and close socket
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                time.sleep(0.05)
                self.server.server_close()
            except Exception as e:
                logger.warning(f"[SocialBridgeServer Close Notice] {e}")

        self.server = None
        self.server_thread = None
        logger.info(f"[SocialBridgeServer] Stopped and port {PORT} released.")
        return True


# Global singleton
bridge_server = SocialBridgeServer()
