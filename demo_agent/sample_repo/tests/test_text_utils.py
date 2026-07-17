from text_utils import slugify


def test_slugify_trims_edges_and_collapses_spaces() -> None:
    assert slugify("  Hello   Build Week  ") == "hello-build-week"
