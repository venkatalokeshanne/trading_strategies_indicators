"""
Run a converted script through TrendSpider's OWN scripting engine, and optionally
compare its outputs with values exported from TradingView.

This is a validation tool, not a converter. It needs two things that live OUTSIDE this
repository and must never be committed to it:

  * the oracle runner from the quant-platform project (`run_batch.js`, `load_engine.js`)
  * TrendSpider's captured client-side engine bundle (proprietary)

Both default to the paths on the machine where they were built; override with the
TS_ORACLE_DIR and TS_BUNDLE environment variables.

Usage
-----
    python tools/oracle_run.py converted/X.trendspider.js --bars bars/AAPL_D.csv
    python tools/oracle_run.py converted/X.trendspider.js --bars tv_export.csv \\
        --compare "Basis=Basis,Upper=Upper" --warmup 200
    python tools/oracle_run.py converted/X.trendspider.js --bars spy.csv \\
        --history "QQQ|D=qqq.csv" --inputs '{"length": 20}' --resolution 15
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows consoles default to cp1252; never let a print() of "§" or "—" fail or garble.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_ORACLE_DIR = "C:/Users/annev/Downloads/quant-platform-full/backend/tools/ts_store/oracle"
DEFAULT_BUNDLE = ("C:/Users/annev/Downloads/trendspider-automation/data/extraction/"
                  "runtime_bundle/00_pretty.js")
ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- bars
def _to_epoch_seconds(raw: str) -> int:
    raw = raw.strip()
    try:
        v = float(raw)
        return int(v / 1000) if v > 1e11 else int(v)        # accept ms or s
    except ValueError:
        pass
    text = raw.replace("Z", "+00:00")
    stamp = dt.datetime.fromisoformat(text)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=dt.timezone.utc)
    return int(stamp.timestamp())


def read_bars(path: Path) -> tuple[dict, list[dict]]:
    """OHLCV for the engine, plus every raw row (TradingView exports carry plot columns)."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path}: no rows")
    cols = {c.lower().strip(): c for c in rows[0]}
    tcol = cols.get("time") or cols.get("date") or cols.get("datetime") or next(iter(rows[0]))
    need = ["open", "high", "low", "close"]
    missing = [c for c in need if c not in cols]
    if missing:
        sys.exit(f"{path}: missing columns {missing} (have {list(rows[0])})")

    def num(r, c, default=0.0):
        v = r.get(cols[c]) if c in cols else None
        try:
            return float(v) if v not in (None, "", "NaN") else default
        except ValueError:
            return default

    bars = {"time": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
    for r in rows:
        bars["time"].append(_to_epoch_seconds(r[tcol]))
        for c in need:
            bars[c].append(num(r, c))
        bars["volume"].append(num(r, "volume", 0.0))
    return bars, rows


# --------------------------------------------------------------------------- oracle
def run_oracle(script: Path, bars: dict, args) -> dict:
    oracle = Path(os.environ.get("TS_ORACLE_DIR", DEFAULT_ORACLE_DIR))
    bundle = os.environ.get("TS_BUNDLE", DEFAULT_BUNDLE)
    runner = oracle / "run_batch.js"
    if not runner.exists():
        sys.exit(f"Oracle runner not found at {runner}.\n"
                 "The engine oracle exists only on the machine that captured TrendSpider's "
                 "bundle. Set TS_ORACLE_DIR, or validate at the tv-parity level instead.")
    if not Path(bundle).exists():
        sys.exit(f"TrendSpider engine bundle not found at {bundle}. Set TS_BUNDLE.")

    histories = {}
    for spec in args.history or []:
        key, _, csv_path = spec.partition("=")
        histories[key], _ = read_bars(Path(csv_path))

    job = {"id": "run", "script": str(script.resolve()), "bars": bars,
           "inputs": json.loads(args.inputs) if args.inputs else {},
           "ticker": args.ticker, "resolution": args.resolution, "histories": histories}

    with tempfile.TemporaryDirectory() as tmp:
        jobs, results = Path(tmp) / "jobs.json", Path(tmp) / "results.json"
        jobs.write_text(json.dumps([job]), encoding="utf-8")
        env = {**os.environ, "TS_BUNDLE": bundle, "TZ": os.environ.get("TZ", "America/New_York")}
        proc = subprocess.run(["node", str(runner), str(jobs), str(results)],
                              capture_output=True, text=True, env=env, timeout=600)
        if proc.returncode != 0 or not results.exists():
            sys.exit(f"oracle failed:\n{proc.stderr[-2000:]}")
        return json.loads(results.read_text(encoding="utf-8"))[0]


def _decode(v):
    if isinstance(v, dict):
        if "__num" in v:
            return float(v["__num"])
        if "__undef" in v:
            return None
    return v


# --------------------------------------------------------------------------- compare
def compare(ours: list, theirs: list, warmup: int, tol: float) -> dict:
    diffs, first_bad = [], None
    for i in range(warmup, min(len(ours), len(theirs))):
        a, b = ours[i], theirs[i]
        if a is None or b is None or (isinstance(a, float) and math.isnan(a)) \
                or (isinstance(b, float) and math.isnan(b)):
            continue
        d = abs(float(a) - float(b))
        diffs.append((d, d / max(abs(float(b)), 1e-12)))
        if first_bad is None and d > tol * max(1.0, abs(float(b))):
            first_bad = i
    if not diffs:
        return {"compared": 0}
    return {"compared": len(diffs), "max_abs": max(x[0] for x in diffs),
            "max_rel": max(x[1] for x in diffs), "first_divergence_bar": first_bad}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("--bars", type=Path, required=True)
    ap.add_argument("--history", action="append", help='"TICKER|RES=path.csv" (repeatable)')
    ap.add_argument("--inputs", help="JSON object of input overrides, keyed by input id")
    ap.add_argument("--ticker", default="AAPL")
    ap.add_argument("--resolution", default="D", help='e.g. "D", "60", "15"')
    ap.add_argument("--compare", help='"OurPaintName=TradingViewColumn,..."')
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--tol", type=float, default=1e-6, help="relative tolerance for 'divergence'")
    args = ap.parse_args()

    bars, raw_rows = read_bars(args.bars)
    result = run_oracle(args.script, bars, args)

    out_dir = ROOT / "validation" / args.script.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"script : {args.script}")
    print(f"bars   : {len(bars['time'])} from {args.bars}")
    if result.get("error"):
        print(f"\nENGINE ERROR: {result['error']}")
        (out_dir / "oracle_error.txt").write_text(str(result["error"]), encoding="utf-8")
        sys.exit(1)

    appearance = result.get("appearance") or {}
    titles = {sid: (meta or {}).get("title") or sid for sid, meta in appearance.items()}
    series = {titles.get(sid, sid): [_decode(v) for v in vals]
              for sid, vals in (result.get("series") or {}).items()}
    signals = sorted(t for sid, t in titles.items() if (appearance.get(sid) or {}).get("isSignalSeries"))

    with (out_dir / "oracle_output.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        names = list(series)
        w.writerow(["time", *names])
        for i, t in enumerate(bars["time"]):
            w.writerow([t, *[(series[n][i] if i < len(series[n]) else None) for n in names]])

    print(f"\noutputs ({len(series)}): {', '.join(series) or '-'}")
    print(f"signals ({len(signals)}): {', '.join(signals) or '-'}")
    for name in signals:
        vals = series.get(name) or []
        print(f"   {name}: true on {sum(1 for v in vals if v)} bars")
    print(f"written: {out_dir / 'oracle_output.csv'}")

    if args.compare:
        print(f"\nCOMPARISON with TradingView (after {args.warmup} warm-up bars)")
        report = {}
        for pair in args.compare.split(","):
            ours, _, theirs = (p.strip() for p in pair.partition("="))
            if ours not in series:
                print(f"   {ours}: not among our outputs"); continue
            col = next((c for c in raw_rows[0] if c.strip() == theirs), None)
            if col is None:
                print(f"   {theirs}: not a column in {args.bars}"); continue
            tv = []
            for r in raw_rows:
                try:
                    tv.append(float(r[col]) if r[col] not in ("", "NaN") else None)
                except ValueError:
                    tv.append(None)
            rep = compare(series[ours], tv, args.warmup, args.tol)
            report[ours] = rep
            if rep.get("compared"):
                print(f"   {ours:20} vs {theirs:20} n={rep['compared']:>5}  max|d|={rep['max_abs']:.6g}  "
                      f"max rel={rep['max_rel']:.3g}  first divergence bar: {rep['first_divergence_bar']}")
            else:
                print(f"   {ours}: nothing comparable after warm-up")
        (out_dir / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
