"""
Mobile Control — Android Telekinesis Engine powered by Android Debug Bridge (ADB).
Enables seamless voice-driven smartphone control over USB or Wi-Fi:
Battery diagnostics, app launching, taps/swipes, flashlight, and file transfers.
"""

import subprocess
import os
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MobileControl:
    """Controls connected Android smartphones via local ADB daemon."""

    # Common Android Package & Intent Registry
    APP_REGISTRY = {
        'whatsapp': 'com.whatsapp',
        'instagram': 'com.instagram.android',
        'youtube': 'com.google.android.youtube',
        'spotify': 'com.spotify.music',
        'camera': 'android.media.action.IMAGE_CAPTURE',
        'chrome': 'com.android.chrome',
        'browser': 'com.android.chrome',
        'settings': 'android.settings.SETTINGS',
        'maps': 'com.google.android.apps.maps',
        'telegram': 'org.telegram.messenger',
        'gmail': 'com.google.android.gm',
        'clock': 'com.google.android.deskclock',
        'calculator': 'com.google.android.calculator',
        'photos': 'com.google.android.apps.photos',
        'gallery': 'com.google.android.apps.photos',
        'twitter': 'com.twitter.android',
        'x': 'com.twitter.android'
    }

    KEY_CODES = {
        'home': 3,
        'back': 4,
        'volume_up': 24,
        'volume_down': 25,
        'power': 26,
        'camera': 27,
        'enter': 66,
        'delete': 67,
        'mute': 164
    }

    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path

    def _run_adb(self, args: List[str], timeout: int = 8) -> subprocess.CompletedProcess:
        """Execute an ADB command safely."""
        cmd = [self.adb_path] + args
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

    def get_devices(self) -> List[str]:
        """List serial IDs of all currently attached Android devices."""
        try:
            res = self._run_adb(['devices'])
            lines = res.stdout.strip().split('\n')[1:]
            devices = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])
            return devices
        except Exception as e:
            logger.error(f"[MobileControl] Error checking adb devices: {e}")
            return []

    def is_connected(self) -> bool:
        """Check if at least one Android device is ready."""
        return len(self.get_devices()) > 0

    def connect_wifi(self, ip_port: str) -> Dict[str, Any]:
        """Connect to an Android device over Wi-Fi (e.g. 192.168.1.5:5555)."""
        try:
            res = self._run_adb(['connect', ip_port])
            success = 'connected to' in res.stdout.lower()
            return {'success': success, 'message': res.stdout.strip()}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # TELEMETRY & DIAGNOSTICS
    # ==========================================

    def get_battery_status(self) -> Dict[str, Any]:
        """Read real-time battery level and charging status."""
        devices = self.get_devices()
        if not devices:
            return {
                'success': True,
                'connected': False,
                'message': 'Koi Android phone connect nahi hai. Phone ko USB se jodiye ya Wi-Fi debugging enable karein.'
            }

        try:
            res = self._run_adb(['shell', 'dumpsys', 'battery'])
            out = res.stdout

            level_match = re.search(r'level:\s*(\d+)', out)
            level = int(level_match.group(1)) if level_match else None

            scale_match = re.search(r'scale:\s*(\d+)', out)
            scale = int(scale_match.group(1)) if scale_match else 100

            status_match = re.search(r'status:\s*(\d+)', out)
            status_code = int(status_match.group(1)) if status_match else 1

            ac_match = re.search(r'AC powered:\s*(true|false)', out, re.I)
            usb_match = re.search(r'USB powered:\s*(true|false)', out, re.I)

            is_charging = (ac_match and ac_match.group(1).lower() == 'true') or \
                          (usb_match and usb_match.group(1).lower() == 'true') or \
                          (status_code == 2)

            pct = int((level / scale) * 100) if level is not None else 0
            charging_str = "charging par hai" if is_charging else "battery par chal raha hai"
            msg = f"Boss, aapka phone {pct}% charged hai aur abhi {charging_str}."

            return {
                'success': True,
                'level': pct,
                'is_charging': is_charging,
                'message': msg
            }
        except Exception as e:
            return {'success': False, 'message': f"Battery check me error: {str(e)}"}

    # ==========================================
    # APP LAUNCHING & INTENTS
    # ==========================================

    def open_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application on the connected Android phone."""
        if not self.is_connected():
            return {'success': False, 'message': 'Android phone connect nahi hai.'}

        key = app_name.lower().strip()
        target = self.APP_REGISTRY.get(key, key)

        try:
            if target.startswith('android.'):
                # Standard Android intent action
                cmd = ['shell', 'am', 'start', '-a', target]
            elif '.' in target:
                # Direct package launch via monkey or am
                cmd = ['shell', 'monkey', '-p', target, '-c', 'android.intent.category.LAUNCHER', '1']
            else:
                # Try generic launch
                cmd = ['shell', 'monkey', '-p', f"com.{target}", '-c', 'android.intent.category.LAUNCHER', '1']

            res = self._run_adb(cmd)
            return {
                'success': True,
                'message': f"Phone pe {app_name.capitalize()} open kar diya Boss!"
            }
        except Exception as e:
            return {'success': False, 'message': f"App kholne me error: {str(e)}"}

    # ==========================================
    # INPUT & GESTURE TELEKINESIS
    # ==========================================

    def tap(self, x: int, y: int) -> Dict[str, Any]:
        """Simulate a screen tap at (x, y) coordinates."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}
        try:
            self._run_adb(['shell', 'input', 'tap', str(x), str(y)])
            return {'success': True, 'message': f"Tapped at ({x}, {y}) on phone."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def swipe(self, direction: str = 'up') -> Dict[str, Any]:
        """Swipe gestures on Android screen."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}

        # Approximate coordinates for 1080x2400 standard screen
        d = direction.lower().strip()
        coords = {
            'up': ['500', '1600', '500', '600', '300'],
            'down': ['500', '600', '500', '1600', '300'],
            'left': ['900', '1000', '200', '1000', '300'],
            'right': ['200', '1000', '900', '1000', '300']
        }
        swipe_args = coords.get(d, coords['up'])

        try:
            self._run_adb(['shell', 'input', 'swipe'] + swipe_args)
            return {'success': True, 'message': f"Phone pe swipe {d} kar diya Boss."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def press_key(self, key_name: str) -> Dict[str, Any]:
        """Simulate pressing physical/system buttons on phone."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}

        code = self.KEY_CODES.get(key_name.lower().strip())
        if not code:
            return {'success': False, 'message': f"Unknown key: {key_name}"}

        try:
            self._run_adb(['shell', 'input', 'keyevent', str(code)])
            return {'success': True, 'message': f"Pressed {key_name} on phone."}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def type_text(self, text: str) -> Dict[str, Any]:
        """Type text into active input field on phone."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}
        try:
            # Escape spaces for ADB input
            escaped = text.replace(' ', '%s')
            self._run_adb(['shell', 'input', 'text', escaped])
            return {'success': True, 'message': f"Typed on phone: {text}"}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ==========================================
    # HARDWARE & FILE ACTIONS
    # ==========================================

    def toggle_flashlight(self) -> Dict[str, Any]:
        """Toggle phone camera flashlight."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}
        try:
            # Android 13+ standard camera torch intent or shell command
            self._run_adb(['shell', 'cmd', 'camera', 'set-torch-mode', '0', 'on'])
            return {'success': True, 'message': "Phone ki flashlight on kar di Boss!"}
        except Exception as e:
            return {'success': False, 'message': f"Flashlight toggle me issue: {str(e)}"}

    def take_phone_screenshot(self, destination_dir: Optional[str] = None) -> Dict[str, Any]:
        """Take screenshot on phone and immediately download it to PC Desktop."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}

        desktop = destination_dir or os.path.join(os.path.expanduser('~'), 'Desktop')
        filename = "phone_screenshot.png"
        pc_target = os.path.join(desktop, filename)

        try:
            self._run_adb(['shell', 'screencap', '-p', '/sdcard/friday_shot.png'])
            self._run_adb(['pull', '/sdcard/friday_shot.png', pc_target])
            self._run_adb(['shell', 'rm', '/sdcard/friday_shot.png'])

            return {
                'success': True,
                'path': pc_target,
                'message': f"Phone ka screenshot leke Desktop par save kar diya Boss!"
            }
        except Exception as e:
            return {'success': False, 'message': f"Screenshot lene me error: {str(e)}"}

    def send_file(self, pc_path: str, phone_dest: str = "/sdcard/Download/") -> Dict[str, Any]:
        """Send any file from PC to phone."""
        if not self.is_connected():
            return {'success': False, 'message': 'Phone connect nahi hai.'}
        if not os.path.exists(pc_path):
            return {'success': False, 'message': f"PC par file nahi mili: {pc_path}"}

        try:
            self._run_adb(['push', pc_path, phone_dest])
            fname = os.path.basename(pc_path)
            return {'success': True, 'message': f"'{fname}' phone ke Downloads folder me bhej di Boss!"}
        except Exception as e:
            return {'success': False, 'message': str(e)}
