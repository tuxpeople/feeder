# feeder: merge several RSS/Atom feeds into one Atom feed

# Build the virtualenv using Chainguard's Python dev image (pip, build tools)
# DL3007: Chainguard only publishes `latest` tags for free. The digest is
# pinned, so Renovate proposes base image updates as PRs that have to pass CI.
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest-dev@sha256:9f76d277ca81d3079eb3be24c742de3b6598f032fc9943fed6951ff99e581d02 AS build

# The venv lives in /opt/venv, not in /home/nonroot (mode 0700): Kubernetes
# may run the pod as a different UID (e.g. runAsUser: 65534), which must
# still be able to read it. A venv cannot be moved, so create it in place.
USER 0
RUN mkdir -p /opt/venv /app/out /app/config && chown nonroot:nonroot /opt/venv /app/out
USER nonroot

COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --disable-pip-version-check --no-cache-dir -r /tmp/requirements.txt && \
    # pip/setuptools are never used at runtime and would only add CVE findings
    /opt/venv/bin/pip uninstall --yes pip setuptools wheel

# Copy the virtualenv into the minimal distroless Chainguard Python runtime
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest@sha256:0ce856292cb65f45ee233c5ef7fcf55bd5210102af01a08efb392c3495195909

# OCI Labels
LABEL org.opencontainers.image.title="feeder"
LABEL org.opencontainers.image.description="Merges several RSS/Atom feeds into one Atom feed"
LABEL org.opencontainers.image.vendor="tuxpeople"
LABEL org.opencontainers.image.source="https://github.com/tuxpeople/feeder"

COPY --from=build /opt/venv /opt/venv
# Application files stay owned by root: the app only reads them
# Default locations: sources in /app/config/urls.txt, output /app/out/feed.xml
# (mount a writable volume to /app/out with a read-only root filesystem)
COPY --from=build /app /app
COPY feeder.py /app/

# PYTHONUNBUFFERED: log output straight to stdout/stderr
# PYTHONDONTWRITEBYTECODE: the root filesystem is read-only in Kubernetes
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Chainguard's nonroot user
USER 65532
WORKDIR /app
ENTRYPOINT ["/opt/venv/bin/python", "/app/feeder.py"]
