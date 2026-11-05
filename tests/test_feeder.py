from pathlib import Path

import feedparser
import pytest

import feeder

FIXTURES = Path(__file__).parent / "fixtures"
ENV = {
    "FEED_ITEMS": "3",
    "FEED_ID": "urn:example:merged",
    "FEED_TITLE": "Merged",
    "FEED_SUBTITLE": "Merged test feed",
    "FEED_AUTHOR_NAME": "Test",
    "FEED_AUTHOR_EMAIL": "test@example.com",
    "FEED_LINK_ALTERNATE": "https://example.com/",
    "FEED_LINK_SELF": "https://example.com/feed.xml",
    "FEED_UPDATE_INTERVAL": "60",
}


@pytest.fixture
def config(tmp_path):
    urls = tmp_path / "urls.txt"
    urls.write_text(
        f"{FIXTURES / 'rss.xml'}\n\n# comment\n{FIXTURES / 'atom.xml'}\n{FIXTURES / 'rss.xml'}\n"
    )
    env = {**ENV, "URLS_FILE": str(urls), "OUTPUT_FILE": str(tmp_path / "out" / "feed.xml")}
    return feeder.load_config(env)


def test_missing_variables_are_reported():
    with pytest.raises(ValueError, match="FEED_TITLE"):
        feeder.load_config({k: v for k, v in ENV.items() if k != "FEED_TITLE"})


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        feeder.load_config({**ENV, "FEED_ITEMS": value})


def test_sources_skip_blank_lines_comments_and_duplicates(config):
    sources = feeder.load_sources(config.urls_file)
    assert sources == [str(FIXTURES / "rss.xml"), str(FIXTURES / "atom.xml")]


def test_entries_are_newest_first_unique_and_limited(config):
    sources = feeder.load_sources(config.urls_file)
    entries = feeder.select_entries(feeder.collect_entries(sources), config.items)
    assert [e["title"] for e in entries] == ["RSS newest", "Atom middle", "Duplicate title"]


def test_entries_without_date_do_not_break_sorting():
    entries = [
        {"title": "no date"},
        {"title": "dated", "updated_parsed": (2026, 1, 1, 0, 0, 0, 0, 1, 0)},
    ]
    assert [e["title"] for e in feeder.select_entries(entries, 5)] == ["dated", "no date"]


def test_unreadable_source_is_skipped(config, tmp_path):
    entries = feeder.collect_entries([str(tmp_path / "missing.xml"), str(FIXTURES / "atom.xml")])
    assert {e["title"] for e in entries} == {"Atom middle", "Duplicate title"}


def test_update_writes_a_valid_atom_feed(config):
    feeder.update(config)
    parsed = feedparser.parse(config.output_file.read_text())
    assert not parsed.bozo
    assert parsed.feed.title == "Merged"
    assert [e.title for e in parsed.entries] == ["RSS newest", "Atom middle", "Duplicate title"]
    assert parsed.entries[0].summary == "<p>HTML summary</p>"
    assert parsed.entries[1].author == "Jane"


def test_main_fails_without_configuration(monkeypatch):
    for name in feeder.REQUIRED_VARS:
        monkeypatch.delenv(name, raising=False)
    assert feeder.main() == 1
