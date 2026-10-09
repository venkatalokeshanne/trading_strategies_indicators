"""
Check a Python conversion: run it on synthetic bars and on cached real data, report what it
produced, and run the repaint replay. Any exception is a failure.

Usage:  python tools/py_check.py python/strategies/<id>-<slug>.py [--tf 60] [--symbol BTCUSDT]
Exit 1 on failure.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "python"))
sys.path.insert(0, str(REPO / "python" / "tests"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--tf", default="60")
    ap.add_argument("--symbol", default="BTCUSDT")
    a = ap.parse_args()

    from conftest import make_bars
    from pinelib import SymbolInfo, metrics, run
    from tradesearch import catalog, data, repaint

    path = Path(a.file).resolve()
    cls = catalog.load_script(path)
    ok = True
    runs = [("synthetic D", make_bars(n=1500), SymbolInfo.make("TEST:SYNTH", "crypto"), "D")]
    ref = data.find_symbol(a.symbol)
    cached = data.load_cached(ref, a.tf) if ref else None
    if cached is not None:
        from tradesearch.pipeline import _symbolinfo
        from dataclasses import asdict
        runs.append((f"{ref.tickerid} {a.tf}", cached.tail(5000).reset_index(drop=True), _symbolinfo(asdict(ref)), a.tf))
    else:
        print(f"(no cached {a.symbol} {a.tf} data — run the pipeline once to populate the cache)")
    for label, bars, sym, tf in runs:
        t0 = time.perf_counter()
        try:
            res = run(cls, bars, symbol=sym, timeframe=tf)
        except Exception as e:
            ok = False
            print(f"FAIL  {label}: {type(e).__name__}: {e}")
            continue
        dt = time.perf_counter() - t0
        line = f"ok    {label}: {len(bars)} bars in {dt:.2f}s; plots {len(res.outputs.plots)}, shapes {len(res.outputs.shapes)}"
        if res.broker is not None:
            m = metrics.compute(res)
            line += (f"; trades {m['totalTrades']} (+{m['openTrades']} open), net {m['netProfitPercent']:.2f}%, "
                     f"PF {m['profitFactor'] if m['profitFactor'] == m['profitFactor'] else 'na'}")
        print(line)
        if label.startswith("synthetic"):
            src = None
            prog = catalog._progress().get(path.stem.split("-")[0], {})
            if prog.get("file") and (REPO / prog["file"]).exists():
                src = (REPO / prog["file"]).read_text(encoding="utf-8", errors="ignore")
            audit = repaint.audit(cls, bars, sym, tf, src, full=res)
            bad = [t for t in audit["tests"] if t["status"] != "pass"]
            print(f"      repaint: {audit['passedChecks']}/{audit['totalChecks']} pass"
                  + ("".join(f"\n        {t['status']}: {t['name']} — {t['detail']}" for t in bad)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
