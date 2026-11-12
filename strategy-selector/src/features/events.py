"""Event flags per symbol-day: FOMC decision, CPI, jobs report, options expiry, month-end (market-wide, config/events.yaml + calendar)
and earnings (per symbol, Twelve Data /earnings, cached). Everything here is known before the open of the day it flags."""
import json
import os
import re
from datetime import date

import pandas as pd
import requests
import yaml

from src import config
from src.data import calendar
from src.data.twelvedata import Keys, _request

EVENTS_YAML = config.ROOT / "config/events.yaml"
FED_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])}
BEFORE, AFTER = ("pre", "before"), ("after", "post")


def parse_fomc(html: str) -> list[str]:
    """Decision day (last day of each scheduled meeting) from the Fed's calendar page."""
    out = []
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"Released\s+\w+\s+\d{1,2},\s*\d{4}", " ", text)        # minutes release dates look like meeting days
    for m in re.finditer(r"(\d{4}) FOMC Meetings", text):
        year = int(m.group(1))
        nxt = re.search(r"\d{4} FOMC Meetings", text[m.end():])
        block = text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]
        mon = "|".join(MONTHS) + "|" + "|".join(m[:3] for m in MONTHS)
        # a meeting row: month label (or "Jan/Feb"), then "30-31" / "31-1" / "19-20*" (a range) or a lone day followed by the Statement link
        for m1, m2, a, b in re.findall(r"\b(" + mon + r")(?:/(" + mon + r"))?\s+(\d{1,2})(?:\s*-\s*(\d{1,2})|(?=\s*\*?\s*Statement:))", block):
            mo = next(v for k, v in MONTHS.items() if k.startswith((m2 or m1)[:3]))
            out.append(date(year, mo, int(b or a)).isoformat())
    out = sorted(set(out))
    return [d for k, d in enumerate(out) if k + 1 == len(out) or (date.fromisoformat(out[k + 1]) - date.fromisoformat(d)).days > 7]     # a stray day next to a meeting row


def refresh_fomc() -> list[str]:
    """Download the Fed calendar and store the decision days in config/events.yaml (keeps cpi / jobs lists untouched)."""
    r = requests.get(FED_URL, timeout=60)
    r.raise_for_status()
    dates = parse_fomc(r.text)
    ev = yaml.safe_load(EVENTS_YAML.read_text()) if EVENTS_YAML.exists() else {}
    ev["fomc"] = dates
    ev.setdefault("cpi", [])
    ev.setdefault("jobs", [])
    EVENTS_YAML.write_text("# fomc: decision days from federalreserve.gov (cli events refresh-fomc). cpi / jobs: BLS release dates, add by hand (bls.gov blocks automated access).\n"
                           + yaml.safe_dump({k: ev[k] for k in ("fomc", "cpi", "jobs")}, default_flow_style=None, width=140))
    return dates


def earnings(cfg, symbol: str, refresh: bool = False) -> list[dict] | None:
    """[{date, time}] for the symbol, or None when no source has it (flags are then NaN, never a silent 0).
    Sources: config/earnings.csv (symbol,date,time - wins), else Twelve Data /earnings (free plan covers only a few symbols), cached."""
    csv = config.ROOT / "config/earnings.csv"
    if csv.exists():
        c = pd.read_csv(csv, dtype=str).fillna("")
        c = c[c["symbol"].str.upper() == symbol]
        if len(c):
            return [dict(date=r.date, time=r.time) for r in c.itertuples()]
    f = cfg["paths"]["cache"].parent / "earnings" / f"{symbol}.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text())
    keys = Keys([k.strip() for k in os.environ["TWELVEDATA_API_KEYS"].split(",") if k.strip()])
    try:
        j = _request(keys, dict(symbol=symbol, start_date="2020-01-01", end_date=str(date.today())), url="https://api.twelvedata.com/earnings")
        rows = [dict(date=e["date"], time=e.get("time") or "") for e in j.get("earnings", [])]
    except RuntimeError as e:
        if "plan" not in str(e):
            raise
        rows = None
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rows))
    return rows


def market_flags(days: pd.DatetimeIndex) -> pd.DataFrame:
    """fomc / cpi / jobs / opex / month_end per trading day (0/1)."""
    ev = yaml.safe_load(EVENTS_YAML.read_text()) if EVENTS_YAML.exists() else {}
    out = pd.DataFrame(index=days)
    for k in ("fomc", "cpi", "jobs"):
        out[k] = days.isin(pd.to_datetime(ev.get(k) or [])).astype(int)
    ses = pd.DatetimeIndex(calendar.sessions(days.min() - pd.Timedelta(days=45), days.max() + pd.Timedelta(days=45))["day"])
    ym = pd.Series(ses.to_period("M"), index=ses)
    out["month_end"] = days.isin(ses[ym.ne(ym.shift(-1)).to_numpy()]).astype(int)
    third_fri = [d for d in pd.date_range(ses.min(), ses.max()) if d.dayofweek == 4 and 15 <= d.day <= 21]
    opex = [ses[ses <= d].max() for d in third_fri]       # a holiday Friday expires on the Thursday before
    out["opex"] = days.isin(pd.DatetimeIndex(opex)).astype(int)
    return out


def symbol_flags(cfg, symbol: str, days: pd.DatetimeIndex) -> pd.DataFrame:
    """earn_day (report date), earn_tonight (after-close report that day), earn_reaction (first session trading on the report)."""
    ses = pd.DatetimeIndex(calendar.sessions(days.min() - pd.Timedelta(days=10), days.max() + pd.Timedelta(days=10))["day"])
    out = pd.DataFrame(0.0, index=days, columns=["earn_day", "earn_tonight", "earn_reaction"])
    rows = earnings(cfg, symbol)
    if rows is None:
        return out * float("nan")
    for e in rows:
        d = pd.Timestamp(e["date"])
        t = e["time"].lower()
        nxt = ses[ses > d].min()
        out.loc[out.index == d, "earn_day"] = 1
        if any(w in t for w in AFTER):
            out.loc[out.index == d, "earn_tonight"] = 1
            out.loc[out.index == nxt, "earn_reaction"] = 1
        elif any(w in t for w in BEFORE):
            out.loc[out.index == d, "earn_reaction"] = 1
        else:                                              # time not supplied: either session could react
            out.loc[out.index.isin([d, nxt]), "earn_reaction"] = 1
    return out


def build(cfg, symbols, days: pd.DatetimeIndex) -> pd.DataFrame:
    m = market_flags(days)
    rows = []
    for s in symbols:
        f = symbol_flags(cfg, s, days).join(m)
        f.insert(0, "symbol", s)
        rows.append(f.rename_axis("day").reset_index())
    return pd.concat(rows, ignore_index=True)
