"""List the next TrendSpider-AI drafts to review, Pine source beside the draft:  python tools/ts_next_drafts.py [N] [indicators|strategies]
Run from the repo root with PYTHONIOENCODING=utf-8."""
import json, sys
from pathlib import Path
n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
kind = sys.argv[2] if len(sys.argv) > 2 else "indicators"
d = json.load(open("TrendSpider/ai_drafts/index.json", encoding="utf-8"))
p = json.load(open("progress/progress.json", encoding="utf-8"))["scripts"]
ok = [(k, v) for k, v in d.items() if v["status"] == "ok" and f"/{kind}/" in v["file"]
      and p.get(k, {}).get("status", "pending") == "pending" and not (p.get(k, {}).get("notes") or "").startswith("AI draft used")]
for k, v in sorted(ok, key=lambda x: x[1]["chars"])[:n]:
    pine = next(Path(f"TradingView/{kind}").glob(k + "*.pine")).read_text(encoding="utf-8", errors="replace")
    draft = Path(v["file"]).read_text(encoding="utf-8")
    strip = lambda s: "\n".join(l for l in s.splitlines() if l.strip() and not l.strip().startswith("//"))
    print(f"########## {k} | {p.get(k, {}).get('title')}\n{strip(pine)}\n---- draft\n{strip(draft)}")
