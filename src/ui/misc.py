def parse_aspect_ratio(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    if ":" in text:
        num, denom = map(float, text.split(":"))
        if denom == 0:
            raise ValueError("Denominator cannot be zero")
        return num / denom
    return float(text)

def check_aspect_ratio_bounds(ratio: float, min_ratio=0.2, max_ratio=5) -> bool:
    return min_ratio <= ratio <= max_ratio
