# PyInstaller build specification for Guardian.
# Run from the project root after installing PyInstaller:
#   pyinstaller --clean guardian.spec

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("guardian_intake")

a = Analysis(
    ["src/guardian_intake/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Guardian",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
