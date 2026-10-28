"""Static triage of the TV repo's Pine strategies -> data/catalog.json. Regex only; no script is read by a model."""
import json
import re
from collections import Counter

import pandas as pd

from src import config

NON_US = r"btc|eth|sol|usdt|usd[tc]?\b|crypto|forex|\bfx\b|eurusd|gbpusd|xau|gold\b|silver|oil\b|nifty|banknifty|sensex|\bmcx\b|\bnse\b|fcpo|delta exchange|alice blue|\bnq\b|\bmnq\b|\bes\b|\bmes\b|futures|bitcoin|ethereum|\bgc\b|\bcl\b|dax|ger\d+|uk100|jp225|ftse|nikkei"
US = r"\bspy\b|\bqqq\b|nasdaq|nyse|\bstocks?\b|\bs&p|aapl|tsla|nvda|\bmsft\b|\bamd\b|us equit"
INTRA = r"scalp|intraday|day.?trad|opening range|\borb\b|\bvwap\b|\b(?:1|2|3|5|10|15|30)\s?-?\s?m(?:in)?\b|\b(?:1|2|3|5|10|15|30)m\b"
DAILY = r"\bdaily\b|\bweekly\b|\bmonthly\b|swing|\b1d\b|\b1w\b|\b4h\b|position trad|long.?term|investing"
BAD_REQ = r"request\.(financial|earnings|dividends|splits|economic|seed|quandl)"
DEAD = r"deprecated|withdrawn|do not use|placeholder"


def strip_comments(src: str) -> str:
    return "\n".join(re.sub(r"//.*", "", ln) for ln in src.splitlines())


def tf_hint(text: str) -> str:
    m = re.search(r"\b(1|2|3|5|10|15|30|45)\s?-?\s?m(?:in(?:ute)?s?)?\b", text, re.I)
    if m:
        return f"{m.group(1)}m"
    m = re.search(r"\b(1|2|4)\s?-?\s?h(?:our)?s?\b", text, re.I)
    if m:
        return f"{m.group(1)}h"
    return "D" if re.search(r"\bdaily\b|\b1d\b", text, re.I) else ("W" if re.search(r"\bweekly\b|\b1w\b", text, re.I) else "")


def features(title: str, raw: str) -> dict:
    src = strip_comments(raw)
    low = (title + "\n" + raw[:800]).lower()       # title + header comments hold the author's stated market/timeframe
    n = lambda p: len(re.findall(p, src))
    lines = sum(1 for ln in src.splitlines() if ln.strip())
    longs, shorts = n(r"strategy\.long\b"), n(r"strategy\.short\b")
    f = dict(lines=lines, tf_hint=tf_hint(title + "\n" + raw[:1500]),
             security=n(r"request\.security|security\s*\("), lookahead_on=n(r"lookahead\s*=\s*barmerge\.lookahead_on"),
             varip=n(r"\bvarip\b"), lib_import=n(r"^\s*import\s+\w", ) + len(re.findall(r"(?m)^\s*import\s+\S+/\S+/\d+", src)),
             arrays=n(r"\b(array|matrix|map)\.\w+"), udt=n(r"(?m)^\s*(type|method)\s+\w+"),
             loops=n(r"\b(for|while)\b"), draw=n(r"\b(line|label|box|table|polyline)\.new"),
             bad_req=n(BAD_REQ), entries=n(r"strategy\.(entry|order)\s*\("), exits=n(r"strategy\.(exit|close|close_all)\s*\("),
             has_sl_tp=n(r"strategy\.exit\s*\(") > 0 or bool(re.search(r"\b(stop|sl|tp|take_?profit|stop_?loss)\b", src, re.I)),
             longs=longs, shorts=shorts, direction="both" if longs and shorts else "long" if longs else "short" if shorts else "?",
             calc_tick=bool(re.search(r"calc_on_every_tick\s*=\s*true", src)), magnifier=bool(re.search(r"use_bar_magnifier\s*=\s*true", src)),
             non_us=bool(re.search(NON_US, low)), us=bool(re.search(US, low)), intraday=bool(re.search(INTRA, low)),
             daily_only=bool(re.search(DAILY, low)), dead=bool(re.search(DEAD, title.lower())) or lines < 8 or (n(r"strategy\.(entry|order)\s*\(") == 0))
    return f


def convertibility(f: dict) -> str:
    if f["dead"] or f["bad_req"] or f["entries"] == 0:
        return "skip"
    cx = (f["lines"] / 40 + 2 * (f["arrays"] > 0) + 3 * (f["udt"] > 0) + 2 * (f["security"] > 0) + 5 * (f["lib_import"] > 0)
          + (f["loops"] > 3) + (f["draw"] > 0) + (f["varip"] > 0))
    f["complexity"] = round(cx, 1)
    return "easy" if cx <= 4 else "medium" if cx <= 9 else "hard"


def priority(f: dict, conv: str) -> float:
    if conv == "skip":
        return 0.0
    p = 40 + {"easy": 20, "medium": 8, "hard": -10}[conv]
    p += 15 if f["intraday"] and not f["daily_only"] else -20 if f["daily_only"] and not f["intraday"] else 0
    p += -25 if f["non_us"] else 5 if f["us"] else 0
    p += 5 if f["direction"] == "both" else 0
    p += 10 if f["lines"] < 60 else 5 if f["lines"] < 150 else -10 if f["lines"] > 400 else 0
    p += 5 if f["security"] == 0 else -10 if f["lookahead_on"] else 0
    p += 3 if f["has_sl_tp"] else 0
    p -= 5 * (f["calc_tick"] or f["magnifier"] or f["varip"] > 0)
    return max(0.0, round(min(100.0, p) - f["lines"] / 1000, 2))   # lines/1000 breaks ties toward shorter scripts


def norm_tokens(raw: str) -> list[str]:
    s = re.sub(r"\"[^\"]*\"|'[^']*'", "S", strip_comments(raw))
    s = re.sub(r"\d+(\.\d+)?", "N", s.lower())
    return re.findall(r"[a-z_.]+|[^\sa-z_.]", s)


def dedupe(tokens: dict[str, list[str]], thr: float = 0.9) -> dict[str, str]:
    """id -> canonical id for near-duplicates (Jaccard of token 5-gram shingles >= thr); canonical = smallest id."""
    sh = {k: {hash(tuple(t[i:i + 5])) for i in range(max(1, len(t) - 4))} for k, t in tokens.items()}
    idx: dict[int, list[str]] = {}
    for k, s in sh.items():
        for h in s:
            idx.setdefault(h, []).append(k)
    ids, dup = sorted(sh), {}
    for k in ids:
        if k in dup:
            continue
        cand = Counter(o for h in sh[k] for o in idx[h] if o > k and o not in dup)
        for o, c in cand.items():
            if c / (len(sh[k]) + len(sh[o]) - c) >= thr:
                dup[o] = k
    return dup


def build(cfg) -> pd.DataFrame:
    repo = config.pine_repo()
    scripts = json.loads((repo / "progress/progress.json").read_text())["scripts"]
    py_ids = {p.name.split("-")[0].removesuffix(".py") for p in (repo / "python/strategies").glob("*.py")}
    rows, toks = [], {}
    for sid, m in scripts.items():
        if m["type"] != "strategy":
            continue
        raw = (repo / m["file"]).read_text(errors="ignore")
        f = features(m["title"], raw)
        conv = convertibility(f)
        toks[sid] = norm_tokens(raw)
        st = m.get("python_status") or ("FULL" if sid in py_ids else "pending")
        rows.append(dict(id=sid, file=m["file"], title=m["title"], pine_version=m["pine_version"], status=st,
                         convertibility=conv, priority=priority(f, conv), **{k: v for k, v in f.items() if k not in ("dead",)}))
    df = pd.DataFrame(rows).set_index("id")
    dup = dedupe(toks)
    df["dup_of"] = pd.Series(dup).reindex(df.index).fillna("")
    df.loc[df["dup_of"] != "", "priority"] = (df["priority"] * 0.3).round(1)
    return df.sort_values("priority", ascending=False)
