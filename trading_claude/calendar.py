"""NYSE regular session schedule using an exchange calendar; fail closed."""
from datetime import datetime, timedelta, timezone
from .core import NY

def session(now):
    if now.tzinfo is None:
        raise ValueError("Timezone-aware timestamp required")
    try:
        import exchange_calendars as xcals
    except ImportError as exc:
        raise RuntimeError("Install requirements.txt for NYSE calendar") from exc
    cal = xcals.get_calendar("XNYS")
    day = now.astimezone(NY).date()
    if not cal.is_session(day.isoformat()):
        return None
    open_utc = cal.session_open(day.isoformat()).to_pydatetime()
    close_utc = cal.session_close(day.isoformat()).to_pydatetime()
    return open_utc, close_utc

def can_enter(now):
    times = session(now)
    if not times:
        return False
    opened, closed = times
    return opened + timedelta(minutes=16) <= now < closed - timedelta(minutes=30)

def should_flatten(now):
    times = session(now)
    if not times:
        return False
    _, closed = times
    return closed - timedelta(minutes=5) <= now < closed
