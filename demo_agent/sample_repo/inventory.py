def reserve_items(stock: int, requested: int) -> bool:
    if requested < 0:
        raise ValueError("requested must be non-negative")
    return stock > requested
