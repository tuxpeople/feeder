# CLAUDE.md

feeder merges several RSS/Atom feeds into one Atom feed (`feeder.py`), packaged as a distroless Chainguard Python image. Created from [tuxpeople/template-python-app](https://github.com/tuxpeople/template-python-app).

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check . && pytest
docker build -t feeder:test .
```

## Rules

- **Security first:** treat feed content as untrusted input; never execute or render it. Add regression tests for fixes.
- **Ruff S rules** (flake8-bandit) are enabled on purpose; fix findings instead of ignoring them.
- **Image:** the venv lives in `/opt/venv` (readable by any UID); the root filesystem is read-only in Kubernetes, `/app/out` must be a writable volume.
- **Behaviour:** configuration errors stop the process (exit 1); errors during an update are logged and the loop continues.
- **Commits:** Conventional Commits; they drive release-please (`feat` → minor, `fix` → patch, `!` → major, `deps` → patch). Use `chore`/`ci`/`docs` for changes that should not produce a release.
- **release-as** in `release-please-config.json` is only for the first release; remove it afterwards.
- **Actions** are pinned by commit SHA (`@<sha> # vX.Y.Z`); Renovate keeps them up to date.
