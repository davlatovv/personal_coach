import re


def validate_time(time_str: str) -> bool:
    """Validate time string in HH:MM format."""
    pattern = r"^([01]\d|2[0-3]):([0-5]\d)$"
    return bool(re.match(pattern, time_str.strip()))


def normalize_time(time_str: str) -> str:
    """Normalize time string to HH:MM format."""
    time_str = time_str.strip()
    if re.match(r"^\d:\d{2}$", time_str):
        return f"0{time_str}"
    return time_str
