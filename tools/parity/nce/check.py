"""Neural Confluence Engine: compare core.js (the code that goes into TrendSpider) with Foresight, which runs the Pine
source unchanged. Foresight's series are dumped (dump_series, capture on) into validation/NCEqAlgo/fs/*.npy; the file
name's last number is the dump order, mapped to variable names below.

    python tools/parity/nce/check.py <dump dir> <chart.csv> <htf.csv | "agg240-utc" | "agg240-session">
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent
REPO = HERE.parents[2]
ORDER = ["bullScore", "bearScore", "vwapVal", "adxVal", "sqzMom", "htfEmaFast", "htfEmaSlow", "triggerBuyPlus",
         "triggerSellPlus", "rsiVal", "histLine", "wtTci", "atrVal", "tp1Hit", "slHit", "tradeDir", "ribbonFlipBull",
         "sqzFiring", "trailSL", "sqzOn"]
WARM = 150      # 3 x the longest recursive length (EMA 50) — seeding differences fade by then


def main(dump_dir, chart_csv, htf_csv):
    files = sorted((REPO / "validation" / "NCEqAlgo" / dump_dir).glob("*.npy"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    ref = {name: np.load(f) for name, f in zip(ORDER, files)}
    out = subprocess.run(["node", str(HERE / "run_core.js"), chart_csv, htf_csv], capture_output=True, text=True,
                         check=True).stdout
    mine = json.loads(out)
    n = len(ref["bullScore"])
    assert len(mine["bullScore"]) == n, (len(mine["bullScore"]), n)
    ok = True
    for name in ORDER:
        a = np.array([np.nan if v is None else float(v) for v in mine[name]])
        b = ref[name].astype(float)
        a, b = a[WARM:], b[WARM:]
        both = ~np.isnan(a) & ~np.isnan(b)
        na_diff = int((np.isnan(a) != np.isnan(b)).sum())
        d = np.abs(a[both] - b[both])
        tol = 1e-6 * max(1.0, float(np.nanmax(np.abs(b))) if both.any() else 1.0)
        bad = int((d > tol).sum())
        first = None
        if bad or na_diff:
            ok = False
            idx = np.where(((np.abs(a - b) > tol) & both) | (np.isnan(a) != np.isnan(b)))[0]
            first = [(int(i + WARM), None if np.isnan(a[i]) else round(float(a[i]), 6),
                      None if np.isnan(b[i]) else round(float(b[i]), 6)) for i in idx[:3]]
        print(f"{name:16s} bars {both.sum():6d}  max|diff| {d.max() if d.size else 0:.2e}  mismatches {bad}  na-diff {na_diff}"
              + (f"  first {first}" if first else ""))
        if name in ("triggerBuyPlus", "triggerSellPlus", "ribbonFlipBull", "sqzFiring"):
            print(f"{'':16s} events: core {int(np.nansum(a))}  foresight {int(np.nansum(b))}")
    print("ALL MATCH" if ok else "DIFFERENCES FOUND")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
