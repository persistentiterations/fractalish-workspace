# Guardian v0.7 Windows one-file build specification.
# Build only on the target operating system.
#
#   python -m PyInstaller --clean --noconfirm guardian.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("guardian_intake")
datas = collect_data_files(
    "guardian_intake",
    includes=["guardian_policy.json", "release_manifest.json"],
)

a = Analysis(
    ["guardian_launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
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
    upx=False,
    console=True,
)

