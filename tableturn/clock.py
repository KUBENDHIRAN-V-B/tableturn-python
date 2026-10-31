from datetime import datetime, timedelta, timezone

class Clock:
    def now(self) -> datetime:
        raise NotImplementedError

class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

class FixedClock(Clock):
    def __init__(self, at: datetime):
        self._at = at
    def now(self) -> datetime:
        return self._at
    def set(self, at: datetime) -> None:
        self._at = at
    def advance(self, **delta) -> datetime:
        self._at = self._at + timedelta(**delta)
        return self._at

def get_clock() -> Clock:
    return SystemClock()

def as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

def minutes_between(start: datetime, end: datetime) -> int:
    return int((as_utc(end) - as_utc(start)).total_seconds() // 60)
