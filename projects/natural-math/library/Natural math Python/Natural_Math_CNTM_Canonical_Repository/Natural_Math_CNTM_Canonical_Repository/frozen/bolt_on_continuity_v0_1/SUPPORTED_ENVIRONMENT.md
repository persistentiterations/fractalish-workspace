# Supported Environment Contract — v0.1

## Qualified target to be built

Stage 0 selects one configured Linux Docker container as the target for later qualification:

| Dimension | v0.1 contract |
|---|---|
| Host | Local Docker Engine |
| Container type | Linux container |
| Scope | One configured container |
| Operator machine | Windows with Docker Desktop Linux containers, or native Linux |
| Connectivity | Local only |
| Control operations | Pause and unpause only |
| Product interface | Local CLI; later local read-only viewer |
| Evidence storage | Local filesystem |
| External services | None required |
| Internet dependency | None required after installation |

## Explicitly unsupported

- remote Docker daemon;
- TCP-exposed Docker API;
- public listener;
- Kubernetes;
- Docker Swarm;
- multiple monitored containers;
- Windows containers;
- rootless-mode compatibility claim before qualification;
- Docker contexts pointing to remote engines;
- cloud-managed container platforms;
- automatic container restart, stop, kill, remove, exec, update, or redeploy;
- secrets collection;
- unrestricted log collection.

## Version qualification rule

Stage 0 does not freeze a Docker version number.

Before an outside pilot, the product release record must state the exact tested:

- operating system;
- Docker Engine version;
- Docker Desktop version when applicable;
- Python version;
- container image digest;
- product package digest.

Compatibility may be claimed only for tested combinations or a precisely defined
version range supported by evidence.

## Security posture

v0.1 is a local prototype. It must not be represented as production-secure.

A future observer should use the narrowest available read access. A future
gateway will necessarily require authority to perform its two allowlisted
operations, but that authority must remain isolated from the observer, decision
core, receipt viewer, and untrusted input.

No component may expose the Docker socket to a web browser or copy unrestricted
Docker authority into the sidecar.
