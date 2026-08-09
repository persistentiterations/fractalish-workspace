# Building a Standalone Executable

The packaged CLI installs with `pip`, but a true standalone executable must be
built separately for each target operating system.

## Windows

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
pip install pyinstaller
pyinstaller --clean guardian.spec
```

The executable will be created as `dist\Guardian.exe`.

## Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pyinstaller
pyinstaller --clean guardian.spec
```

Build on the same operating-system family that will run the executable. A
Windows executable should be built and tested on Windows.
