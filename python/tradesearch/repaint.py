"""
Repaint audit — 8 checks, as TradeSearcher's "No-repaint checks 8/8".

TradeSearcher's exact checks are not public; these are designed here and documented.

Replay (dynamic) — run the strategy on the data truncated at several cut points and
compare with the full run. A script that never looks ahead produces, for every bar before
the cut, the same trades and the same values either way:
  1 replay_entries   every entry before the cut identical (bar, direction, price)
  2 replay_exits     every exit before the cut identical
  3 replay_values    every plotted value before the cut identical
  4 intrabar_path    results with the intrabar path flipped (H/L order) — a WARNING when
                     they differ: the result depends on an assumption about unseen ticks
Static (source):
  5 security_lookahead   request.security with lookahead_on and no [1] offset   (error)
  6 future_functions     timenow / last_bar_index / last_bar_time                (warning)
  7 realtime_only_logic  varip, calc_on_every_tick, barstate.isrealtime/isnew    (warning)
  8 recalc_on_fills      calc_on_order_fills=true                                (warning)

``repainting`` is true when any check is an error.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from pinelib import run

CUTS = (0.55, 0.7, 0.85, 0.95)


def _trade_keys(broker, upto: int) -> tuple[list, list]:
    entries, exits = set(), set()
    for t in broker.closed:
        if t.entry_bar < upto:
            entries.add((t.entry_bar, t.direction, round(t.entry_price, 8), t.entry_id))
        if t.exit_bar < upto:
            exits.add((t.exit_bar, round(t.exit_price, 8), t.exit_id))
    for t in broker.open:
        if t.bar < upto:
            entries.add((t.bar, t.direction, round(t.price, 8), t.entry_id))
    return sorted(entries), sorted(exits)


def replay(script_cls, bars: pd.DataFrame, symbol, timeframe: str, params: dict | None = None,
           full=None, cuts=CUTS) -> list[dict]:
    full = full or run(script_cls, bars, params=params, symbol=symbol, timeframe=timeframe)
    n = len(bars)
    entry_diff, exit_diff, value_diff = [], [], []
    for frac in cuts:
        cut = int(n * frac)
        if cut < 50:
            continue
        part = run(script_cls, bars.iloc[:cut].reset_index(drop=True), params=params, symbol=symbol,
                   timeframe=timeframe)
        if full.broker is not None:
            # compare everything strictly before the truncated run's last bar: an order
            # placed ON the last bar fills on the next one, which the truncated run lacks
            fe, fx = _trade_keys(full.broker, cut - 1)
            pe, px = _trade_keys(part.broker, cut - 1)
            if fe != pe:
                entry_diff.append({"cut": cut, "full": len(fe), "truncated": len(pe),
                                   "first": _first_diff(fe, pe)})
            if fx != px:
                exit_diff.append({"cut": cut, "full": len(fx), "truncated": len(px),
                                  "first": _first_diff(fx, px)})
        for name, arr in full.outputs.plots.items():
            other = part.outputs.plots.get(name)
            if other is None:
                continue
            a, b = np.asarray(arr[:cut]), np.asarray(other[:cut])
            bad = ~((np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= 1e-9 * np.maximum(1, np.abs(a))))
            if bad.any():
                value_diff.append({"cut": cut, "plot": name, "firstBar": int(np.flatnonzero(bad)[0])})
                break
    checks = [
        {"name": "replay_entries", "status": "error" if entry_diff else "pass",
         "detail": entry_diff[:2] if entry_diff else f"entries identical at {len(cuts)} cut points"},
        {"name": "replay_exits", "status": "error" if exit_diff else "pass",
         "detail": exit_diff[:2] if exit_diff else f"exits identical at {len(cuts)} cut points"},
        {"name": "replay_values", "status": "error" if value_diff else "pass",
         "detail": value_diff[:2] if value_diff else "plotted values never change after the fact"},
    ]
    if full.broker is not None:
        flipped = run(script_cls, bars, params=params, symbol=symbol, timeframe=timeframe,
                      strategy_overrides={"path_mode": "reverse"})
        a = [(t.exit_bar, round(t.exit_price, 8)) for t in full.broker.closed]
        b = [(t.exit_bar, round(t.exit_price, 8)) for t in flipped.broker.closed]
        changed = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
        share = changed / max(1, len(a))
        checks.append({"name": "intrabar_path", "status": "warning" if share > 0.05 else "pass",
                       "detail": f"{changed} of {len(a)} exits change if the bar's high and low come in the "
                                 f"other order" if changed else "no exit depends on the intrabar order"})
    else:
        checks.append({"name": "intrabar_path", "status": "pass", "detail": "indicator: no fills"})
    return checks


def _first_diff(a: list, b: list) -> Any:
    sa, sb = set(a), set(b)
    only_a = sorted(sa - sb)[:1]
    only_b = sorted(sb - sa)[:1]
    return {"onlyFull": only_a, "onlyTruncated": only_b}


def audit(script_cls, bars, symbol, timeframe, pine_src: str | None, params=None, full=None) -> dict:
    from .catalog import static_repaint_checks, _strip_comments
    checks = replay(script_cls, bars, symbol, timeframe, params, full=full)
    checks += static_repaint_checks(_strip_comments(pine_src)) if pine_src else [
        {"name": n, "status": "pass", "detail": "no Pine source"} for n in
        ("security_lookahead", "future_functions", "realtime_only_logic", "recalc_on_fills")]
    errors = sum(1 for c in checks if c["status"] == "error")
    warnings = sum(1 for c in checks if c["status"] == "warning")
    return {"repainting": errors > 0, "totalChecks": len(checks),
            "passedChecks": sum(1 for c in checks if c["status"] == "pass"),
            "warningChecks": warnings, "errorChecks": errors, "isAutomatic": True, "tests": checks}
