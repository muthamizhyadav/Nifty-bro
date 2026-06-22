"""IST / NSE session helpers for candle bucketing."""

from datetime import datetime, timedelta, timezone
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN_MIN = 9 * 60 + 15   # 9:15 IST
MARKET_CLOSE_MIN = 15 * 60 + 30  # 3:30 PM IST


def ist_dt(epoch_sec: Optional[float] = None) -> datetime:
    if epoch_sec is None:
        return datetime.now(IST)
    return datetime.fromtimestamp(epoch_sec, IST)


def is_market_open(epoch_sec: Optional[float] = None) -> bool:
    dt = ist_dt(epoch_sec)
    if dt.weekday() >= 5:
        return False
    mins = dt.hour * 60 + dt.minute
    return MARKET_OPEN_MIN <= mins < MARKET_CLOSE_MIN


def candle_bucket_ts(epoch_sec: float, minutes: int) -> int:
    """
    NSE-aligned candle open time (epoch seconds).
    15m bars: 9:15, 9:30, … 15:15 IST.
    """
    dt = ist_dt(epoch_sec)
    total_min = dt.hour * 60 + dt.minute

    if minutes == 15:
        if total_min < MARKET_OPEN_MIN:
            bucket_min = (total_min // minutes) * minutes
        else:
            elapsed = total_min - MARKET_OPEN_MIN
            bucket_min = MARKET_OPEN_MIN + (elapsed // minutes) * minutes
    else:
        bucket_min = (total_min // minutes) * minutes

    bh, bm = divmod(bucket_min, 60)
    bucket = dt.replace(hour=bh, minute=bm, second=0, microsecond=0)
    return int(bucket.timestamp())
