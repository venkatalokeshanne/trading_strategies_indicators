"""
Port of TrendSpider's "ORB Trading Strategy Indicator" (TrendSpider Team).

Unlike the other custom scripts the ported strategies use, this one's
publisher made its source available (`sourceCodeAvailable: true` in the
account's script subscriptions), so this is a line-for-line port of the
real logic, not a reconstruction. Pass numbers below match the source.

Semantics that decide exact trades, all taken from the source:
  * The opening range (OR) is built from the first `or_window` minutes of
    the session. With "Auto" (what the strategies use) that window equals
    the chart's own bar size, and only 1/5/10/15/30/60-minute bars are
    allowed -- on any other interval the script asserts and produces no
    signals at all.
  * OR levels carry forward until the next session locks a new range.
  * ONE entry per session: close crossing above ORH (long) or below ORL
    (short), long checked first. Whichever fires first ends the session's
    entries -- so a short breakout blocks the long for that day.
  * Stop (long): low crosses from >= ORL to < ORL. Target nR: high
    crosses from < ORH + n*range to >= it. Both are bar-to-bar crossings.
  * Session exit fires on the first in-session bar at/after
    (session end - bar size), plus the first bar outside the session.
  * "Safe entry window": OR locked, in session, and before
    session end - floor(3.5 * or_window).
"""

from __future__ import annotations

import pandas as pd

from app.strategies.trendspider.indicator_map import UnsupportedIndicator

SESSIONS = {
    "New York (9:30 AM ET)": (9, 30, 16, 0),
    "London (3:00 AM ET)": (3, 0, 12, 0),
    "Asian (7:00 PM ET)": (19, 0, 4, 0),
    "Globex (6:00 PM ET)": (18, 0, 17, 0),
}
SUPPORTED_AUTO_MINUTES = (1, 5, 10, 15, 30, 60)


def _bar_minutes(index: pd.DatetimeIndex) -> int:
    """The chart resolution, i.e. the typical spacing between bars."""
    diffs = index.to_series().diff().dropna()
    if diffs.empty:
        raise UnsupportedIndicator("ORB needs at least two bars")
    return int(round(diffs.mode().iloc[0].total_seconds() / 60))


def compute_orb(df: pd.DataFrame, inputs: dict) -> dict[str, pd.Series]:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise UnsupportedIndicator("ORB requires a DatetimeIndex (bar start times, US/Eastern)")

    chart_tf = _bar_minutes(df.index)
    override = str(inputs.get("or_window", "Auto"))
    if override == "Auto":
        if chart_tf not in SUPPORTED_AUTO_MINUTES:
            # Mirrors the script's own assert: it refuses to run here, so
            # TrendSpider produces no ORB signals on this interval.
            raise ValueError(
                f"ORB (Auto OR window) supports 1/5/10/15/30/60-minute bars only; got {chart_tf}m"
            )
        or_window = chart_tf
    else:
        or_window = int(override)

    session = inputs.get("session", "New York (9:30 AM ET)")
    if session not in SESSIONS:
        raise UnsupportedIndicator(f"ORB session {session!r} not supported")
    sh, sm, eh, em = SESSIONS[session]
    start_min, end_min = sh * 60 + sm, eh * 60 + em
    crosses_midnight = end_min <= start_min

    idx = df.index
    n = len(df)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    minutes = (idx.hour * 60 + idx.minute).to_numpy()

    def in_session(m: int) -> bool:
        if crosses_midnight:
            return m >= start_min or m < end_min
        return start_min <= m < end_min

    # Session "day key": for sessions crossing midnight, the early-morning
    # part belongs to the previous day's session.
    dates = idx.normalize()
    day_key = [
        (dates[i] - pd.Timedelta(days=1)) if (crosses_midnight and minutes[i] < end_min) else dates[i]
        for i in range(n)
    ]

    # ---- PASS 1: OR levels ------------------------------------------------
    rth = [False] * n
    locked_today = [False] * n
    orh = [None] * n
    orl = [None] * n
    up = {r: [None] * n for r in (0.5, 1, 2, 3)}
    dn = {r: [None] * n for r in (0.5, 1, 2, 3)}

    current_day = None
    or_start = or_end = None
    s_high = s_low = None
    s_locked = False
    c_orh = c_orl = None
    c_up = {r: None for r in up}
    c_dn = {r: None for r in dn}

    for i in range(n):
        ts = idx[i]
        if day_key[i] != current_day:
            current_day = day_key[i]
            or_start = current_day + pd.Timedelta(hours=sh, minutes=sm)
            or_end = or_start + pd.Timedelta(minutes=or_window)
            s_high = s_low = None
            s_locked = False

        in_rth = in_session(minutes[i])
        rth[i] = in_rth
        within = or_start <= ts < or_end
        past = ts >= or_end

        if within and in_rth:
            s_high = high[i] if s_high is None else max(s_high, high[i])
            s_low = low[i] if s_low is None else min(s_low, low[i])
        elif past and in_rth and not s_locked and s_high is not None and s_low is not None:
            s_locked = True
            locked_today[i] = True
            rng = s_high - s_low
            c_orh, c_orl = s_high, s_low
            for r in c_up:
                c_up[r] = c_orh + rng * r if rng > 0 else None
                c_dn[r] = c_orl - rng * r if rng > 0 else None
        elif s_locked:
            locked_today[i] = in_rth

        orh[i], orl[i] = c_orh, c_orl
        for r in up:
            up[r][i] = c_up[r]
            dn[r][i] = c_dn[r]

    # ---- PASS 2: entries, one per session -----------------------------------
    long_entry = [False] * n
    short_entry = [False] * n
    had_entry = False
    cur = None
    for i in range(1, n):
        if day_key[i] != cur:
            cur, had_entry = day_key[i], False
        if not had_entry and orh[i] is not None and orl[i] is not None and locked_today[i]:
            if close[i - 1] <= orh[i] < close[i]:
                long_entry[i], had_entry = True, True
            elif close[i - 1] >= orl[i] > close[i]:
                short_entry[i], had_entry = True, True

    # ---- PASS 4: stop hits (bar-to-bar crossings) ----------------------------
    long_stop = [False] * n
    short_stop = [False] * n
    for i in range(1, n):
        if orl[i] is not None and low[i - 1] >= orl[i] > low[i]:
            long_stop[i] = True
        if orh[i] is not None and high[i - 1] <= orh[i] < high[i]:
            short_stop[i] = True

    # ---- PASS 5: target hits --------------------------------------------------
    long_t = {r: [False] * n for r in up}
    short_t = {r: [False] * n for r in dn}
    for i in range(1, n):
        for r in up:
            lvl = up[r][i]
            if lvl is not None and high[i - 1] < lvl <= high[i]:
                long_t[r][i] = True
            lvl = dn[r][i]
            if lvl is not None and low[i - 1] > lvl >= low[i]:
                short_t[r][i] = True

    # ---- PASS 6: session exit -------------------------------------------------
    session_exit = [False] * n
    exit_min = end_min - chart_tf
    if crosses_midnight and exit_min < 0:
        exit_min += 24 * 60
    fired = False
    cur = None
    for i in range(n):
        if day_key[i] != cur:
            cur, fired = day_key[i], False
        m = minutes[i]
        if crosses_midnight:
            if exit_min >= start_min:
                past_exit = m >= exit_min or m < end_min
            else:
                past_exit = exit_min <= m < end_min
        else:
            past_exit = m >= exit_min
        if rth[i] and not fired and past_exit:
            session_exit[i], fired = True, True
    for i in range(1, n):
        if rth[i - 1] and not rth[i]:
            session_exit[i] = True

    # ---- PASS 7: safe entry window -----------------------------------------
    cutoff = end_min - (or_window * 7) // 2  # floor(or_window * 3.5)
    if crosses_midnight and cutoff < 0:
        cutoff += 24 * 60
    safe = [False] * n
    for i in range(n):
        m = minutes[i]
        if crosses_midnight:
            if cutoff >= start_min:
                before = start_min <= m < cutoff
            else:
                before = m >= start_min or m < cutoff
        else:
            before = m < cutoff
        safe[i] = locked_today[i] and rth[i] and before

    def s(values):
        return pd.Series(values, index=idx, dtype=float)

    out = {
        "entry__long__strategy_": s(long_entry),
        "entry__short__strategy_": s(short_entry),
        "safe_entry_window": s(safe),
        "session_exit": s(session_exit),
        "stop__long": s(long_stop),
        "stop__short": s(short_stop),
    }
    labels = {0.5: "0_5r", 1: "1r", 2: "2r", 3: "3r"}
    for r, label in labels.items():
        out[f"target__long_{label}"] = s(long_t[r])
        out[f"target__short_{label}"] = s(short_t[r])
    return out
