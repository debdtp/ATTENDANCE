# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# We collect the 'models' directory which contains the downloaded face analysis models.
# PyInstaller will copy this folder directly into the build so the app works offline.
extra_datas = [
    ('models', 'models'),
]

# If settings.json exists, we can bundle it as a default configuration.
if os.path.exists('settings.json'):
    extra_datas.append(('settings.json', '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        'pandas',
        'numpy',
        'matplotlib',
        'matplotlib.backends.backend_qtagg',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'onnxruntime',
        'insightface',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'email', 'http', 'html', 'pydoc'],
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
    name='AutoAttendAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True if you want a cmd console behind the app for debugging logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app_icon.ico', # Uncomment and provide path if you have an .ico file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoAttendAI',
)
