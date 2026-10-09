"""
The strategy catalogue: converted scripts on disk + what can be read from the Pine source.

TradeSearcher shows, per strategy, the indicators it uses, its entry and exit criteria,
tags, and a repaint summary. The first three are derived here from the ORIGINAL Pine
source by rule (deterministic, explainable); the repaint summary combines the static
checks below with the replay checks in ``repaint.py``.
"""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = REPO / "python"
TV_DIR = REPO / "TradingView"
PROGRESS = REPO / "progress" / "progress.json"


@dataclass
class CatalogEntry:
    tv_id: str
    name: str
    path: Path                     # converted python file
    script_cls: type
    pine_path: Path | None
    meta: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────── discovery
def load_script(path: Path) -> type:
    """Import a converted script file (names like '7qUtuiBt-Buy-At-Open.py' are fine)."""
    from pinelib import Script
    spec = importlib.util.spec_from_file_location(f"conv_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    found = [v for v in vars(mod).values()
             if isinstance(v, type) and issubclass(v, Script) and v is not Script and v.__module__ == mod.__name__]
    if len(found) != 1:
        raise ValueError(f"{path.name}: expected exactly one Script subclass, found {len(found)}")
    return found[0]


def discover(kind: str = "strategies") -> list[CatalogEntry]:
    progress = _progress()
    out = []
    for p in sorted((PY / kind).glob("*.py")):
        if p.name.startswith("_"):
            continue
        cls = load_script(p)
        tv_id = (cls.SOURCE or {}).get("id") or p.stem.split("-")[0]
        prog = progress.get(tv_id, {})
        pine = REPO / prog["file"] if prog.get("file") else None
        out.append(CatalogEntry(tv_id=tv_id, name=cls.TITLE or prog.get("title", p.stem), path=p,
                                script_cls=cls, pine_path=pine if pine and pine.exists() else None,
                                meta=prog))
    return out


def _progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8")).get("scripts", {})
    return {}


# ─────────────────────────────────────────────────────────────── Pine source analysis
_INDICATORS = [
    (r"\b(?:ta\.)?rsi\s*\(", "RSI"), (r"\b(?:ta\.)?ema\s*\(", "EMA"), (r"\b(?:ta\.)?sma\s*\(", "SMA"),
    (r"\b(?:ta\.)?wma\s*\(", "WMA"), (r"\b(?:ta\.)?hma\s*\(", "Hull MA"), (r"\b(?:ta\.)?vwma\s*\(", "VWMA"),
    (r"\b(?:ta\.)?rma\s*\(", "RMA"), (r"\b(?:ta\.)?alma\s*\(", "ALMA"), (r"\b(?:ta\.)?macd\s*\(", "MACD"),
    (r"\b(?:ta\.)?bb\s*\(|bollinger", "Bollinger Bands"), (r"\b(?:ta\.)?kc\s*\(|keltner", "Keltner Channels"),
    (r"\b(?:ta\.)?supertrend\s*\(|supertrend", "Supertrend"), (r"\b(?:ta\.)?atr\s*\(", "ATR"),
    (r"\b(?:ta\.)?stoch\s*\(|stochastic", "Stochastic"), (r"\b(?:ta\.)?cci\s*\(", "CCI"),
    (r"\b(?:ta\.)?dmi\s*\(|\badx\b", "ADX / DMI"), (r"\b(?:ta\.)?vwap\b|\bvwap\s*\(", "VWAP"),
    (r"\b(?:ta\.)?sar\s*\(|parabolic", "Parabolic SAR"), (r"\b(?:ta\.)?mfi\s*\(", "MFI"),
    (r"\b(?:ta\.)?obv\b", "OBV"), (r"\b(?:ta\.)?wpr\s*\(|williams", "Williams %R"),
    (r"\b(?:ta\.)?tsi\s*\(", "TSI"), (r"\b(?:ta\.)?cmo\s*\(", "CMO"), (r"\b(?:ta\.)?roc\s*\(", "ROC"),
    (r"\b(?:ta\.)?mom\s*\(", "Momentum"), (r"\b(?:ta\.)?linreg\s*\(", "Linear Regression"),
    (r"\b(?:ta\.)?pivot(?:high|low)\s*\(", "Pivot Points"), (r"tenkan|kijun|senkou|ichimoku", "Ichimoku"),
    (r"heikin|heikinashi", "Heikin Ashi"), (r"\bdonchian|\b(?:ta\.)?highest\s*\(", "Donchian / Highest-Lowest"),
    (r"\bzigzag", "ZigZag"), (r"order\s*block|\bob\b", "Order Blocks"), (r"\bfvg\b|fair\s*value\s*gap", "Fair Value Gap"),
    (r"range\s*filter", "Range filter"), (r"ut\s*bot", "UT Bot"), (r"squeeze", "Squeeze"),
    (r"volume\s*profile|\bpoc\b", "Volume Profile"), (r"fibonacci|\bfib\b", "Fibonacci"),
    (r"lorentzian|knn|neural|machine\s*learning|kernel\s*regression", "Machine learning"),
]

_TAGS = [
    (r"\bai\b|machine\s*learning|\bml\b|neural|lorentzian|knn", "AI"),
    (r"scalp", "Scalping"), (r"swing", "Swing"), (r"trend", "Trend following"),
    (r"revers|mean\s*revert", "Mean reversion"), (r"breakout", "Breakout"), (r"momentum", "Momentum"),
    (r"\bsmc\b|smart\s*money|order\s*block|liquidity", "Smart money concepts"),
    (r"\bbtc|bitcoin|crypto|eth", "Crypto"), (r"forex|\bfx\b|eurusd|xauusd|gold", "Forex & gold"),
    (r"\bnq\b|\bes\b|futures|\bmnq\b", "Futures"), (r"grid", "Grid"), (r"\bdca\b", "DCA"),
]


def analyse_pine(src: str, title: str = "") -> dict:
    """Indicators, entry/exit criteria, tags and the static repaint checks of a Pine script."""
    code = _strip_comments(src)
    low = code.lower()
    hay = (title + " " + low).lower()
    indicators = [name for pat, name in _INDICATORS if re.search(pat, low)]
    entry, exit_ = [], []
    if re.search(r"\b(?:ta\.)?cross(?:over|under)?\s*\(", low):
        entry.append("Crossover")
    if re.search(r"\b(?:ta\.)?(?:highest|lowest)\s*\(", low) and re.search(r"close\s*[<>]", low):
        entry.append("Breakout")
    if re.search(r"(rsi|stoch|cci|mfi|wpr)\w*\s*[<>]=?\s*\d", low):
        entry.append("Oscillator threshold")
    if re.search(r"engulf|hammer|doji|pin\s*bar|inside\s*bar", low):
        entry.append("Candlestick pattern")
    if re.search(r"\b(?:request\.)?security\s*\(", low):
        entry.append("Multi-timeframe confirmation")
    if re.search(r"\btime\s*\(\s*timeframe|input\.session|session\s*=", low):
        entry.append("Time filter")
    if re.search(r"volume\s*[<>]|(?:ta\.)?sma\s*\(\s*volume", low):
        entry.append("Volume filter")
    if re.search(r"strategy\.exit\s*\([^)]*\b(stop|loss|limit|profit)\s*=", low, re.S):
        exit_.append("Stop loss or take profit")
    if re.search(r"trail_(points|offset|price)", low):
        exit_.append("Trailing stop")
    if re.search(r"strategy\.close(_all)?\s*\(", low):
        exit_.append("Exit signal")
    if re.search(r"strategy\.entry\s*\([^)]*strategy\.short", low) and re.search(r"strategy\.entry\s*\([^)]*strategy\.long", low):
        exit_.append("Opposite signal (stop and reverse)")
    if re.search(r"bar_index\s*-\s*\w*entry|barssince|strategy\.opentrades\.entry_bar_index", low):
        exit_.append("Time-based exit")
    tags = sorted({name for pat, name in _TAGS if re.search(pat, hay)})
    return {"indicators": indicators, "entryCriteria": entry or ["Custom condition"],
            "exitCriteria": exit_ or ["Custom condition"], "tags": tags,
            "staticChecks": static_repaint_checks(code)}


def static_repaint_checks(code: str) -> list[dict]:
    """Source-level repaint risks. Each: name, status (pass|warning|error), detail."""
    low = code.lower()
    checks = []
    bad_lookahead = []
    for m in re.finditer(r"(?:request\.)?security\s*\((.*?)\)\s*(?:$|\n)", code, re.S | re.I):
        args = m.group(1)
        if re.search(r"lookahead\s*=\s*(barmerge\.lookahead_on|true)", args, re.I) and not re.search(r"\[\s*1\s*\]", args):
            bad_lookahead.append(args.strip()[:80])
    checks.append({"name": "security_lookahead",
                   "status": "error" if bad_lookahead else "pass",
                   "detail": f"lookahead_on without a [1] offset: {bad_lookahead[:2]}" if bad_lookahead
                   else "no higher-timeframe look-ahead"})
    fut = [w for w in ("timenow", "last_bar_index", "last_bar_time") if re.search(rf"\b{w}\b", low)]
    checks.append({"name": "future_functions", "status": "warning" if fut else "pass",
                   "detail": f"uses {', '.join(fut)}" if fut else "no references to the last bar or wall clock"})
    rt = [w for w in ("varip", "calc_on_every_tick", "barstate.isrealtime", "barstate.isnew")
          if re.search(rf"\b{re.escape(w)}\b(?!\s*=\s*false)", low)]
    checks.append({"name": "realtime_only_logic", "status": "warning" if rt else "pass",
                   "detail": f"behaves differently in realtime: {', '.join(rt)}" if rt else "same logic historically and in realtime"})
    cof = re.search(r"calc_on_order_fills\s*=\s*true", low)
    checks.append({"name": "recalc_on_fills", "status": "warning" if cof else "pass",
                   "detail": "calc_on_order_fills=true: intrabar recalculation is approximated" if cof
                   else "no intrabar recalculation"})
    return checks


def _strip_comments(src: str) -> str:
    out, i, n, q = [], 0, len(src), None
    while i < n:
        ch = src[i]
        if q:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if ch == q or ch == "\n":
                q = None
            i += 1
        elif ch in "'\"":
            q = ch; out.append(ch); i += 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        else:
            out.append(ch); i += 1
    return "".join(out)


def classify_holding(avg_bars: float, tf_seconds: int) -> str:
    """TradeSearcher's strategy types from the average holding time."""
    if avg_bars != avg_bars:
        return ""
    hours = avg_bars * tf_seconds / 3600
    if hours < 24:
        return "intraday"
    if hours < 24 * 20:
        return "swing"
    return "longTerm"
