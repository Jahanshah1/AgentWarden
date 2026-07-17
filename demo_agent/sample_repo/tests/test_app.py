from app import build_release_summary


def test_build_release_summary_uses_clean_slug_and_exact_reservation() -> None:
    summary = build_release_summary("  Launch Checklist  ", stock=3, requested=3, scores=[4, 5, 6])
    assert summary == {
        "slug": "launch-checklist",
        "reservation_ok": True,
        "average_score": 5.0,
    }
