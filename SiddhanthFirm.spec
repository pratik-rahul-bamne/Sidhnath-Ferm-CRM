# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('database.sql', '.'), ('.env.example', '.')],
    hiddenimports=['jinja2', 'reportlab', 'reportlab.platypus', 'reportlab.lib', 'reportlab.lib.colors', 'reportlab.lib.pagesizes', 'reportlab.lib.units', 'reportlab.lib.styles', 'reportlab.lib.enums', 'flask', 'flask_bcrypt', 'sqlite3', 'dotenv'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'ultralytics', 'cv2', 'scipy', 'sklearn', 'pandas', 'matplotlib', 'IPython', 'jupyter', 'pytest', 'dlib', 'tkinter', 'zmq'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SiddhanthFirm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
