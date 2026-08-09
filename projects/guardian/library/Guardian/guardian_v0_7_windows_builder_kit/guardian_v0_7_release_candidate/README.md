# Guardian v0.7 — Windows Release Candidate

> Guardian may miss harmful, unsafe, or newly developed content. Results are
> informational and do not guarantee safety. A pass is not a safety
> certification.

Guardian v0.7 prepares the frozen Guardian 0.5 engine for a real Windows
standalone release and clean-machine usability test.

## Current status

- Python package: verified
- Visual demonstration: verified
- Windows build and validation scripts: prepared
- Native Windows executable: not built in this Linux environment
- Python-free Windows validation: pending on a Windows machine

## Build on Windows

Open PowerShell in the project folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\BUILD_WINDOWS.ps1
```

The build script:

- creates an isolated build environment;
- installs pinned build tools;
- builds `Guardian.exe`;
- copies it into the Windows release folder;
- generates release checksums;
- runs the complete Windows validation script.

The build computer needs Python. The end-user validation computer does not.

## End-user validation

Copy `release\Guardian-v0.7-Windows` to the Python-free Windows machine and
run:

```text
CHECK_RELEASE_CHECKSUMS.cmd
VALIDATE_GUARDIAN.cmd
RUN_GUARDIAN_DEMO.cmd
```

See `WINDOWS_CLEAN_MACHINE_CHECKLIST.md`.

Frozen engine SHA-256:

```text
db269d956eaa39fdba9c1e19840590da378c6c30ac24511bc82687d138212bd8
```
