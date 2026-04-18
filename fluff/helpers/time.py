from datetime import timezone, datetime, timedelta
import re

units = {
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }

def parse_duration(duration_str: str) -> tuple[int, int, str]:
    """Parses a duration string like 10m, 1d, 2h, 1w into a future epoch timestamp.
    Returns: a tuple of [the epoch timestamp when the user should be unbanned, the integer representing the amount of
    time the user should be banned for, and the unit used for the amount of time, e.g. [123456789, 4, days]
    """

    match = re.fullmatch(r'(\d+)([mhdw])', duration_str.strip().lower())
    if not match:
        raise ValueError(f"Invalid duration format: `{duration_str}`. Use `10m`, `1h`, `2d`, `3w`, etc.")

    amount, unit = int(match.group(1)), match.group(2)
    delta = timedelta(**{units[unit]: amount})
    future = datetime.now(timezone.utc) + delta
    return int(future.timestamp()), amount, units[unit]