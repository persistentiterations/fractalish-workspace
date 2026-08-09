# Stage 6 Live Runbook

Do not use an existing or production container.

Docker's documented `pause` operation suspends all processes in the selected
container; `unpause` resumes them. Stage 6 uses a disposable `busybox` sleep
container and targets its full immutable ID.

After fixture and regression gates pass:

```powershell
docker run -d --name bolt-on-stage6-disposable busybox sleep 3600
$ContainerId = docker inspect --format "{{.Id}}" bolt-on-stage6-disposable
$ContainerId
```

The printed value must be 64 hexadecimal characters.

Run:

```powershell
python .\products\bolt_on_continuity_v0_1\tools\qualify_stage_6_live.py `
  --container-id $ContainerId `
  --acknowledge-disposable-container
```

Required ending:

```text
STAGE 6 CONTROLLED NATIVE EXECUTION LIVE: PASS
```

Confirm recovery:

```powershell
docker inspect --format "running={{.State.Running}} paused={{.State.Paused}}" $ContainerId
```

Required:

```text
running=true paused=false
```

Remove only the disposable container:

```powershell
docker rm -f $ContainerId
```
