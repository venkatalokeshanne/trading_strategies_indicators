"""
Conversion backlog tracker — the shared state that lets any session or Claude account
continue where the last one stopped. It is bookkeeping, not a converter.

    python tools/progress.py sync      # add any new pine/*.pine files as `pending`
    python tools/progress.py stats     # counts by status, type and validation level
    python tools/progress.py next [N]  # the next N pending scripts, in queue order
    python tools/progress.py set <id> --status PARTIAL --validation oracle --notes "..."
    python tools/progress.py set <id> --ts-name "RSI Divergence_TV" --live-tested AAPL:D                                       --ts-saved yes            # or: --ts-saved no --ts-save-error "HTTP 500"
    python tools/progress.py check <id>  # the done-gates for one script (also run by `set --status`)

Queue order: strategies before indicators, and within each, shortest source first — the
simpler conversions come first and harden the reference files before the hard ones.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):           # Windows consoles default to cp1252
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "pine"
PROGRESS = ROOT / "progress" / "progress.json"
STATUSES = ("pending", "in_progress", "FULL", "PARTIAL", "NOT CONVERTIBLE")
LEVELS = ("none", "static", "syntax", "oracle", "tv-parity", "live")
DONE = ("FULL", "PARTIAL")
# Where the script lives in TrendSpider. Filled by the live test (reference/09).
TS_FIELDS = {
    "trendspider_name": None,       # the describe_indicator title, ending in _TV
    "live_tested": None,            # "YYYY-MM-DD TICKER:RES" — APPLY ran with no console error
    "trendspider_saved": None,      # True once it shows in the editor's "Yours" list
    "trendspider_save_error": None, # e.g. "HTTP 500" when the save failed server-side (LESSONS L12)
    "tester_run": None,             # strategies: "YYYY-MM-DD TICKER:RES trades=N"
    "parity_evidence": None,        # path/summary of the TradingView comparison (LESSONS L10)
}


def load() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {"schema": 1, "scripts": {}}


def save(data: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    PROGRESS.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def metadata() -> dict:
    """Title / author / URL from the extractor's results.json files, keyed by script id."""
    meta = {}
    for results in PINE.rglob("results.json"):
        try:
            for r in json.loads(results.read_text(encoding="utf-8")):
                f = r.get("file")
                if f:
                    meta[Path(f).stem.split("-")[0]] = r
        except (ValueError, OSError):
            pass
    return meta


def classify(text: str) -> tuple[str, str]:
    head = text[:6000]
    kind = ("strategy" if re.search(r"^\s*strategy\s*\(", head, re.M) else
            "indicator" if re.search(r"^\s*(indicator|study)\s*\(", head, re.M) else "library/other")
    m = re.search(r"//@version\s*=\s*(\d+)", head)
    return kind, (f"v{m.group(1)}" if m else "unknown")


def cmd_sync(_args) -> None:
    data = load()
    meta = metadata()
    added = 0
    for f in sorted(PINE.rglob("*.pine")):
        sid = f.stem.split("-")[0]
        if sid in data["scripts"]:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        kind, version = classify(text)
        m = meta.get(sid, {})
        data["scripts"][sid] = {
            "file": f.relative_to(ROOT).as_posix(),
            "title": m.get("name") or f.stem,
            "author": m.get("author"),
            "url": m.get("url"),
            "type": kind,
            "pine_version": version,
            "source_chars": len(text),
            "status": "pending",
            "validation": "none",
            "converted_file": None,
            "deviations": [],
            "notes": "",
            **TS_FIELDS,
        }
        added += 1
    save(data)
    print(f"added {added}; tracking {len(data['scripts'])} scripts")


def queue(data: dict) -> list:
    rank = {"strategy": 0, "indicator": 1}
    items = [(sid, s) for sid, s in data["scripts"].items() if s["status"] in ("pending", "in_progress")]
    return sorted(items, key=lambda kv: (kv[1]["status"] != "in_progress",
                                         rank.get(kv[1]["type"], 2), kv[1]["source_chars"]))


def cmd_next(args) -> None:
    for sid, s in queue(load())[: args.n]:
        print(f"{sid}  [{s['type']}, {s['pine_version']}, {s['source_chars']:,} chars]  {s['title']}")
        print(f"    file: {s['file']}")
        print(f"    url : {s['url']}")


def cmd_stats(_args) -> None:
    data = load()
    s = list(data["scripts"].values())
    print(f"scripts tracked: {len(s)}   (updated {data.get('updated', '-')})")
    for field, values in (("status", STATUSES), ("type", ("strategy", "indicator", "library/other")),
                          ("validation", LEVELS)):
        counts = {v: sum(1 for x in s if x.get(field) == v) for v in values}
        print(f"  {field:11} " + "  ".join(f"{k}: {v}" for k, v in counts.items() if v))
    print(f"  trendspider saved: {sum(1 for x in s if x.get('trendspider_saved') is True)}   "
          f"save failed (retry): {sum(1 for x in s if x.get('trendspider_save_error') and x.get('trendspider_saved') is not True)}")


def gates(sid: str, s: dict) -> list[str]:
    """Reasons this script may NOT be marked FULL/PARTIAL. Empty list = all gates pass."""
    fails = []
    f = s.get("converted_file")
    path = ROOT / f if f else None
    if not path or not path.exists():
        fails.append(f"converted file missing: {f}")
    else:
        lint = subprocess.run([sys.executable, str(ROOT / "tools" / "lint_trendspider.py"), str(path)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if lint.returncode != 0:
            fails.append("lint has errors:\n" + "\n".join(l for l in lint.stdout.splitlines() if "ERROR" in l))
        title = re.search(r"describe_indicator\s*\(\s*(['\"])(.*?)\1", path.read_text(encoding="utf-8"))
        if title and s.get("trendspider_name") != title.group(2):
            fails.append(f"trendspider_name {s.get('trendspider_name')!r} != describe_indicator title "
                         f"{title.group(2)!r}")
    if not (s.get("trendspider_name") or "").endswith("_TV"):
        fails.append("trendspider_name must end with _TV")
    if not s.get("live_tested"):
        fails.append("no live TrendSpider test recorded (--live-tested), reference/09")
    if s.get("trendspider_saved") is not True and not s.get("trendspider_save_error"):
        fails.append("not saved in TrendSpider and no save error recorded (--ts-saved / --ts-save-error)")
    if s.get("type") == "strategy" and not s.get("tester_run"):
        fails.append("strategy without a Strategy Tester run (--tester-run)")
    if s.get("validation") == "tv-parity" and not s.get("parity_evidence"):
        fails.append("validation tv-parity claimed without --parity-evidence (LESSONS L10)")
    return fails


def cmd_check(args) -> None:
    data = load()
    s = data["scripts"].get(args.id) or sys.exit(f"unknown id {args.id}")
    fails = gates(args.id, {**TS_FIELDS, **s})
    print(f"{args.id}: " + ("all gates pass" if not fails else "BLOCKED"))
    for x in fails:
        print("  - " + x)
    sys.exit(1 if fails else 0)


def cmd_set(args) -> None:
    data = load()
    s = data["scripts"].get(args.id)
    if s is None:
        sys.exit(f"unknown id {args.id}")
    if args.status:
        if args.status not in STATUSES:
            sys.exit(f"status must be one of {STATUSES}")
        s["status"] = args.status
    if args.validation:
        if args.validation not in LEVELS:
            sys.exit(f"validation must be one of {LEVELS}")
        s["validation"] = args.validation
    if args.converted_file:
        s["converted_file"] = args.converted_file
    if args.deviation:
        s["deviations"].extend(args.deviation)
    if args.notes is not None:
        s["notes"] = args.notes
    for k, v in TS_FIELDS.items():
        s.setdefault(k, v)
    if args.ts_name:
        s["trendspider_name"] = args.ts_name
    if args.live_tested:
        s["live_tested"] = f"{dt.date.today().isoformat()} {args.live_tested}"
    if args.ts_saved:
        s["trendspider_saved"] = args.ts_saved == "yes"
        if s["trendspider_saved"]:
            s["trendspider_save_error"] = None
    if args.ts_save_error:
        s["trendspider_save_error"] = f"{dt.date.today().isoformat()} {args.ts_save_error}"
    if args.tester_run:
        s["tester_run"] = f"{dt.date.today().isoformat()} {args.tester_run}"
    if args.parity_evidence:
        s["parity_evidence"] = args.parity_evidence
    if s["status"] in DONE:
        fails = gates(args.id, s)
        if fails:
            sys.exit(f"{args.id}: cannot be {s['status']} yet —\n  - " + "\n  - ".join(fails))
    s["last_change"] = dt.date.today().isoformat()
    save(data)
    print(f"{args.id}: {s['status']} / {s['validation']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync").set_defaults(fn=cmd_sync)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    p = sub.add_parser("next"); p.add_argument("n", nargs="?", type=int, default=5); p.set_defaults(fn=cmd_next)
    p = sub.add_parser("set")
    p.add_argument("id")
    p.add_argument("--status"); p.add_argument("--validation"); p.add_argument("--converted-file")
    p.add_argument("--deviation", action="append"); p.add_argument("--notes")
    p.add_argument("--ts-name"); p.add_argument("--live-tested", metavar="TICKER:RES")
    p.add_argument("--ts-saved", choices=("yes", "no")); p.add_argument("--ts-save-error")
    p.add_argument("--tester-run", metavar='"TICKER:RES trades=N"'); p.add_argument("--parity-evidence")
    p.set_defaults(fn=cmd_set)
    p = sub.add_parser("check"); p.add_argument("id"); p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
