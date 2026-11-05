# feeder

Merges several RSS/Atom feeds into one Atom feed. Every `FEED_UPDATE_INTERVAL` minutes it fetches the sources, keeps the newest `FEED_ITEMS` entries (one per title) and writes them to `/app/out/feed.xml`. Serve that file with any web server, e.g. an nginx sidecar sharing the volume.

## Usage

```bash
mkdir -p config out && chmod 777 out
printf 'https://example.com/feed.xml\nhttps://example.org/rss\n' > config/urls.txt

docker run -d --name feeder --read-only \
  -v "$PWD/config:/app/config:ro" -v "$PWD/out:/app/out" \
  -e FEED_ITEMS=50 -e FEED_UPDATE_INTERVAL=30 \
  -e FEED_ID=urn:example:merged -e FEED_TITLE="Merged feed" -e FEED_SUBTITLE="All my feeds" \
  -e FEED_AUTHOR_NAME="Jane" -e FEED_AUTHOR_EMAIL=jane@example.com \
  -e FEED_LINK_ALTERNATE=https://example.com/ -e FEED_LINK_SELF=https://example.com/feed.xml \
  ghcr.io/tuxpeople/feeder:latest
```

### Configuration

| Variable | Required | Description |
|---|---|---|
| `FEED_ITEMS` | ✅ | Number of entries in the merged feed |
| `FEED_UPDATE_INTERVAL` | ✅ | Minutes between updates |
| `FEED_ID`, `FEED_TITLE`, `FEED_SUBTITLE` | ✅ | Metadata of the merged feed |
| `FEED_AUTHOR_NAME`, `FEED_AUTHOR_EMAIL` | ✅ | Author of the merged feed |
| `FEED_LINK_ALTERNATE`, `FEED_LINK_SELF` | ✅ | Links of the merged feed |
| `URLS_FILE` | | Source list, one URL per line, `#` comments allowed (default `/app/config/urls.txt`) |
| `OUTPUT_FILE` | | Output file (default `/app/out/feed.xml`) |
| `DEBUG_LEVEL` | | `DEBUG`, `INFO` (default), `WARNING`, `ERROR` |

Missing or invalid settings stop the container with an error. A source that cannot be read is skipped with a warning.

## Image

- Distroless Chainguard Python, runs as non-root (any UID works), read-only root filesystem
- Tags: `X.Y.Z`, `X.Y`, `X`, `latest`; Cosign-signed with signed provenance and SBOM
- Built with the pipeline from [tuxpeople/template-python-app](https://github.com/tuxpeople/template-python-app)

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
ruff check . && ruff format --check . && pytest
```

## History

Until 0.0.1 feeder was built in [tuxpeople/containers](https://github.com/tuxpeople/containers). Since its own repository: configuration and logic are testable functions, the unmaintained `timeloop` dependency is gone, blank lines and comments in `urls.txt` are ignored, entries without a date no longer crash the sorting, and unreadable sources are skipped.
