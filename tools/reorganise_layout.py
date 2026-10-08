"""
One-off move (2026-10-08) to the owner's layout:

    TradingView/indicators/   original Pine indicators      (was pine/tradingview_pine, mixed)
    TradingView/strategies/   original Pine strategies      (was pine/tradingview_strategies + strategies found in the above)
    TradingView/_meta/        the extractor's results/summary files
    TrendSpider/indicators/   converted indicators
    TrendSpider/strategies/   converted strategies

Placement follows the script's own declaration (strategy() vs indicator()/study()), read
from the whole file, not from which TradingView listing it was collected from.
Updates progress/progress.json paths and types. Safe to re-run: moves only what is left.
"""

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "pine"
TV = ROOT / "TradingView"
TS = ROOT / "TrendSpider"
DECL = re.compile(r"^\s*(strategy|indicator|study)\s*\(", re.M)


def kind_of(text: str) -> str:
    m = DECL.search(text)
    return "strategy" if m and m.group(1) == "strategy" else "indicator" if m else "library/other"


def main() -> None:
    for d in (TV / "indicators", TV / "strategies", TV / "_meta", TS / "indicators", TS / "strategies"):
        d.mkdir(parents=True, exist_ok=True)
    for d in (TS / "indicators", TS / "strategies"):
        (d / ".gitkeep").touch()

    prog_path = ROOT / "progress" / "progress.json"
    prog = json.loads(prog_path.read_text(encoding="utf-8"))
    by_file = {s["file"]: sid for sid, s in prog["scripts"].items()}

    moved = {"indicator": 0, "strategy": 0, "library/other": 0}
    if OLD.exists():
        for src_dir in sorted(p for p in OLD.iterdir() if p.is_dir()):
            for f in sorted(src_dir.glob("*.pine")):
                text = f.read_text(encoding="utf-8", errors="ignore")
                kind = kind_of(text)
                dest_dir = TV / ("strategies" if kind == "strategy" else "indicators")
                dest = dest_dir / f.name
                if dest.exists():
                    raise SystemExit(f"name clash: {dest}")
                shutil.move(str(f), dest)
                moved[kind] += 1
                sid = by_file.get(f.relative_to(ROOT).as_posix())
                if sid:
                    prog["scripts"][sid]["file"] = dest.relative_to(ROOT).as_posix()
                    prog["scripts"][sid]["type"] = kind
            for meta in src_dir.glob("*.json"):
                shutil.move(str(meta), TV / "_meta" / f"{src_dir.name}.{meta.name}")
            src_dir.rmdir()
        OLD.rmdir()
    old_conv = ROOT / "converted"
    if old_conv.exists() and not any(old_conv.iterdir()):
        old_conv.rmdir()

    prog_path.write_text(json.dumps(prog, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    missing = [s["file"] for s in prog["scripts"].values() if not (ROOT / s["file"]).exists()]
    print("moved:", moved)
    print("indicators:", len(list((TV / "indicators").glob("*.pine"))),
          "strategies:", len(list((TV / "strategies").glob("*.pine"))))
    print("progress entries pointing at a missing file:", len(missing))


if __name__ == "__main__":
    main()
