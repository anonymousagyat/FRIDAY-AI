# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

root_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(root_dir, 'ui'), 'ui'),
    (os.path.join(root_dir, 'config.example.json'), '.'),
    (os.path.join(root_dir, 'contacts.example.json'), '.'),
    (os.path.join(root_dir, 'friday_bridge_userscript.js'), '.'),
    (os.path.join(root_dir, 'friday_snapchat_bridge.js'), '.'),
]

hiddenimports = [
    'google.genai',
    'google.genai.types',
    'sounddevice',
    'numpy',
    'requests',
    'webview',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'clr',
    'pythonnet',
    'psutil',
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'pyautogui',
    'pywinauto',
    'keyboard',
    'pyperclip',
    'edge_tts',
    'pygame',
    'ctypes',
    'ctypes.wintypes',
    'winreg',
    'sqlite3',
    'core',
    'core.action_executor',
    'core.ai_engine',
    'core.assistant',
    'core.context_tracker',
    'core.gemini_live_client',
    'core.hermes_bridge',
    'core.memory',
    'core.mobile_control',
    'core.phantom_typer',
    'core.screen_peeler',
    'core.screen_reader',
    'core.social_bridge_server',
    'core.social_gatekeeper',
    'core.student_engine',
    'core.system_control',
    'core.task_planner',
    'core.vector_rag',
    'core.web_researcher',
]

a = Analysis(
    [os.path.join(root_dir, 'main.py')],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'tensorflow', 'scipy', 'matplotlib', 'pandas', 'IPython'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FRIDAY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FRIDAY',
)
