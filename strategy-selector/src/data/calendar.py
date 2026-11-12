import exchange_calendars as xc
import pandas as pd

_cal = xc.get_calendar("XNYS")


def sessions(start, end) -> pd.DataFrame:
    """Trading days in [start, end] with s_open/s_close as UTC timestamps (early closes included)."""
    s = _cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
    return pd.DataFrame({"day": s.date, "s_open": _cal.opens.loc[s].values, "s_close": _cal.closes.loc[s].values}
                        ).assign(s_open=lambda d: pd.to_datetime(d["s_open"], utc=True),
                                 s_close=lambda d: pd.to_datetime(d["s_close"], utc=True))
