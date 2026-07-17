def parse_tags(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part]
