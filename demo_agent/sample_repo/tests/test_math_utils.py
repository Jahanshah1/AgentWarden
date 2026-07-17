import pytest

from math_utils import average


def test_average_multiple_values() -> None:
    assert average([1, 2, 3, 4]) == 2.5


def test_average_single_value() -> None:
    assert average([7]) == 7.0


def test_average_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        average([])
