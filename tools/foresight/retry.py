"""Re-run the runs that failed for ENGINE reasons, not the script's: Foresight's 'drawing replay mutation crossed
runtime contexts' and 'engine's response was not valid JSON'. Both only happen when the strategy runs as a side
handle (start_run); run as the session script (load_session + run) they work. Same statistics code as runner.py.
Results replace the failed lines in results/<tf>/<TICKER>.jsonl (originals kept in results_before_retry/)."""
import json, glob, sys, time, shutil
from pathlib import Path
from multiprocessing import Process
import runner

ROOT = runner.ROOT
ENGINE_ERRORS = ("crossed runtime contexts", "not valid JSON")


def targets():
    out = []
    for f in sorted(glob.glob(str(ROOT / "results" / "*" / "*.jsonl"))):
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            if any(e in str(r.get("error", "")) for e in ENGINE_ERRORS):
                out.append((r["tf"], r["ticker"], r["strategy"], r["file"]))
    return out


def work(wid, port, jobs):
    eng = runner.Engine(port)
    strat_dir = Path(runner.STRATS[0]).parent
    with open(ROOT / f"retry_w{wid}.jsonl", "a", encoding="utf-8") as fo:
        for n, (tf, sym, sid, fname) in enumerate(jobs):
            if n and n % 150 == 0: eng.start()                        # bound memory, as in runner.py
            csv = ROOT / "data" / tf / f"{sym}.csv"
            dates = [line.split(",", 3)[1] for line in open(csv)][1:]
            nbars = len(dates); oos_bar = int(nbars * runner.OOS_FRAC)
            rec = {"strategy": sid, "file": fname, "ticker": sym, "tf": tf, "bars": nbars, "retried": "session"}
            try:
                r = eng.fs.call("load_session", {"script_path": str(strat_dir / fname), "data_path": str(csv)}, timeout=300)
                if not isinstance(r, dict) or "error" in r:
                    rec["error"] = str(r)[:300]
                else:
                    full = eng.fs.call("run", {}, timeout=300)          # full range (load_session scores in-sample only)
                    if not isinstance(full, dict) or "ntrade" not in full:
                        rec["error"] = str(full)[:300]
                    else:
                        rec.update(runner.pick(full, runner.KEEP)); rec["family"] = full.get("family")
                        rec["from"] = full.get("scope", {}).get("from_date"); rec["to"] = full.get("scope", {}).get("to_date")
                        if (full.get("total_trades") or 0) > 0:
                            rec.update(runner.trade_stats(eng.fs, "", oos_bar, nbars, dates))
            except Exception as e:
                rec["error"] = f"timeout/crash: {type(e).__name__}"; eng.start()
            fo.write(json.dumps(rec) + "\n"); fo.flush()
    eng.stop()


def merge():
    new = {}
    for f in glob.glob(str(ROOT / "retry_w*.jsonl")):
        for l in open(f, encoding="utf-8"):
            r = json.loads(l); new[(r["tf"], r["ticker"], r["strategy"])] = l.rstrip("\n")
    bak = ROOT / "results_before_retry"
    replaced = 0
    for f in sorted(glob.glob(str(ROOT / "results" / "*" / "*.jsonl"))):
        lines = open(f, encoding="utf-8").read().splitlines(); changed = False
        for i, l in enumerate(lines):
            r = json.loads(l); k = (r["tf"], r["ticker"], r["strategy"])
            if k in new and "error" in r: lines[i] = new[k]; changed = True; replaced += 1
        if changed:
            dst = bak / Path(f).parent.name; dst.mkdir(parents=True, exist_ok=True)
            if not (dst / Path(f).name).exists(): shutil.copy2(f, dst / Path(f).name)
            open(f, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("replaced", replaced, "of", len(new), "retried runs")


if __name__ == "__main__":
    if sys.argv[1:] == ["merge"]: merge(); sys.exit()
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    T = targets(); print(len(T), "runs to retry", flush=True)
    ps = [Process(target=work, args=(i, 17520 + i, T[i::nw])) for i in range(nw)]
    for p in ps: p.start(); time.sleep(2)
    for p in ps: p.join()
    print("RETRY DONE", flush=True)
