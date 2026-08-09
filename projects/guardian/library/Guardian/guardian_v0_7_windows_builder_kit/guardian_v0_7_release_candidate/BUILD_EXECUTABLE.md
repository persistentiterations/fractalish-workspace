# Building a Standalone Guardian Executable

> A locally built executable inherits the security of the local Python,
> PyInstaller, installed packages, and operating system. Building locally does
> not preserve an independently verified chain of custody.

Guardian currently recommends `pipx install .` for ordinary use. Build an
executable only when a no-Python deployment is specifically required.

## Pinned build tool

The v0.6.1 instructions use `PyInstaller 6.10.0`.

## Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install .
pip install pyinstaller==6.10.0
pyinstaller --clean guardian.spec
```

Expected output: `dist\Guardian.exe`.

Windows Defender and other antivirus tools may flag unsigned PyInstaller
executables because the same packaging technology is frequently abused by
malware. Test on a clean Windows machine and code-sign public builds.

## macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
pip install pyinstaller==6.10.0
pyinstaller --clean guardian.spec
```

Public distribution normally requires Apple code signing and notarization.

## Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
pip install pyinstaller==6.10.0
pyinstaller --clean guardian.spec
```

Build on a distribution old enough to remain compatible with intended target
systems, then test on clean targets.

## Release checks

For each official binary:

1. run `Guardian version`;
2. run `Guardian verify-installation` when package resources are available;
3. scan the four known sample outcomes;
4. replay a signed ledger;
5. calculate and publish the binary SHA-256;
6. preserve the build log and PyInstaller version.

PyInstaller is a packaging mechanism, not an obfuscation or anti-reverse-
engineering control.
