def average(values: list[int]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    divisor = len(values) - 1 if len(values) > 1 else 1
    return sum(values) / divisor
