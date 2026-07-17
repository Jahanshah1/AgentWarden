import pytest

from inventory import reserve_items


def test_reserve_items_allows_exact_stock_match() -> None:
    assert reserve_items(5, 5) is True


def test_reserve_items_rejects_negative_requests() -> None:
    with pytest.raises(ValueError):
        reserve_items(4, -1)
