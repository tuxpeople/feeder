"""feeder: merge several RSS/Atom feeds into one Atom feed.

Reads the source URLs from URLS_FILE (one per line), fetches them every
FEED_UPDATE_INTERVAL minutes, keeps the newest FEED_ITEMS entries (one per
title) and writes them to OUTPUT_FILE.
"""

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import feedparser
from feedgen.feed import FeedGenerator

logger = logging.getLogger("feeder")

REQUIRED_VARS = [
    "FEED_ITEMS",
    "FEED_ID",
    "FEED_TITLE",
    "FEED_SUBTITLE",
    "FEED_AUTHOR_NAME",
    "FEED_AUTHOR_EMAIL",
    "FEED_LINK_ALTERNATE",
    "FEED_LINK_SELF",
    "FEED_UPDATE_INTERVAL",
]
VALID_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]


@dataclass
class Config:
    items: int
    feed_id: str
    title: str
    subtitle: str
    author_name: str
    author_email: str
    link_alternate: str
    link_self: str
    update_interval: int
    urls_file: Path
    output_file: Path


def load_config(env=os.environ):
    """Read the configuration from the environment, fail on missing values."""
    missing = [name for name in REQUIRED_VARS if not env.get(name)]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    try:
        items = int(env["FEED_ITEMS"])
        interval = int(env["FEED_UPDATE_INTERVAL"])
    except ValueError as err:
        raise ValueError("FEED_ITEMS and FEED_UPDATE_INTERVAL must be integers") from err
    if items < 1 or interval < 1:
        raise ValueError("FEED_ITEMS and FEED_UPDATE_INTERVAL must be at least 1")
    return Config(
        items=items,
        feed_id=env["FEED_ID"],
        title=env["FEED_TITLE"],
        subtitle=env["FEED_SUBTITLE"],
        author_name=env["FEED_AUTHOR_NAME"],
        author_email=env["FEED_AUTHOR_EMAIL"],
        link_alternate=env["FEED_LINK_ALTERNATE"],
        link_self=env["FEED_LINK_SELF"],
        update_interval=interval,
        urls_file=Path(env.get("URLS_FILE", "/app/config/urls.txt")),
        output_file=Path(env.get("OUTPUT_FILE", "/app/out/feed.xml")),
    )


def load_sources(path):
    """Source URLs, one per line; blank lines, comments and duplicates are skipped."""
    sources = []
    for line in Path(path).read_text().splitlines():
        url = line.strip()
        if url and not url.startswith("#") and url not in sources:
            sources.append(url)
    return sources


def collect_entries(sources, parse=feedparser.parse):
    entries = []
    for url in sources:
        logger.debug("Parsing %s", url)
        feed = parse(url)
        if feed.get("bozo") and not feed.get("entries"):
            logger.warning("Could not read %s: %s", url, feed.get("bozo_exception"))
            continue
        entries.extend(feed.get("entries", []))
    return entries


def _date(entry, field):
    """`updated` falls back to `published`. Read the raw dict: feedparser's
    own fallback from `updated` to `published` is deprecated."""
    return dict.get(entry, f"updated{field}") or dict.get(entry, f"published{field}")


def select_entries(entries, limit):
    """The newest `limit` entries, one per title. Entries without a date sort last."""
    dated = sorted(
        entries,
        key=lambda entry: tuple(_date(entry, "_parsed") or ()),
        reverse=True,
    )
    selected, titles = [], set()
    for entry in dated:
        title = entry.get("title")
        if not title or title in titles:
            continue
        titles.add(title)
        selected.append(entry)
        if len(selected) == limit:
            break
    return selected


def build_feed(entries, config):
    fg = FeedGenerator()
    fg.id(config.feed_id)
    fg.title(config.title)
    fg.subtitle(config.subtitle)
    fg.author({"name": config.author_name, "email": config.author_email})
    fg.link(href=config.link_alternate, rel="alternate")
    fg.link(href=config.link_self, rel="self")
    fg.language("en")
    for entry in entries:
        fe = fg.add_entry(order="append")
        fe.id(entry.get("id") or entry.get("link"))
        fe.title(entry["title"])
        if entry.get("link"):
            fe.link(href=entry["link"])
        fe.updated(_date(entry, ""))
        if entry.get("author"):
            fe.author(name=entry["author"])
        if entry.get("summary"):
            # If the summary contains HTML code, set its type
            summary_type = "html" if "<" in entry["summary"] else None
            fe.summary(summary=entry["summary"], type=summary_type)
        for tag in entry.get("tags", []):
            fe.category(term=tag.get("term"))
        if entry.get("content"):
            fe.content(content=entry["content"][0].value, type="html")
    return fg


def update(config):
    logger.info("Start parsing feeds")
    sources = load_sources(config.urls_file)
    entries = select_entries(collect_entries(sources), config.items)
    config.output_file.parent.mkdir(parents=True, exist_ok=True)
    build_feed(entries, config).atom_file(str(config.output_file))
    logger.info(
        "Wrote %d entries from %d sources to %s", len(entries), len(sources), config.output_file
    )


def setup_logging():
    level = os.environ.get("DEBUG_LEVEL", "INFO").upper()
    if level not in VALID_LEVELS:
        print(f"ERROR: Invalid debug level {level}, fallback to INFO.")
        level = "INFO"
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    )


def main():
    setup_logging()
    try:
        config = load_config()
    except ValueError as err:
        logger.error("%s", err)
        return 1
    logger.info("Update interval is set to %d minutes", config.update_interval)
    while True:
        try:
            update(config)
        except Exception:
            # Keep running: a broken source or a full disk must not stop the loop
            logger.exception("Update failed")
        time.sleep(config.update_interval * 60)


if __name__ == "__main__":
    sys.exit(main())
