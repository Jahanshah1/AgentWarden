from tags import parse_tags


def test_parse_tags_ignores_empty_entries() -> None:
    assert parse_tags("bug, fix, , release") == ["bug", "fix", "release"]
