from inventory import reserve_items
from math_utils import average
from text_utils import slugify


def build_release_summary(title: str, stock: int, requested: int, scores: list[int]) -> dict[str, object]:
    return {
        "slug": slugify(title),
        "reservation_ok": reserve_items(stock, requested),
        "average_score": average(scores),
    }
