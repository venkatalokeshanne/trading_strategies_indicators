"""Foresight's repaint detector for every strategy x timeframe that traded. It runs the strategy twice - as
written, and seeing only confirmed (closed) higher-timeframe data - and diffs the trades, plus a static census
of repaint-capable constructs. Verdicts: 'repaints' = the historical trades depend on data not available at
the time (the backtest is fiction); 'vectors_present' = constructs that behave differently LIVE, but history
matched; 'clean'. Checked on SPY when the strategy traded there, else on its first traded ticker.
Output: repaint.jsonl (one line per strategy x timeframe). Resumable."""
import json, glob, sys, time
from pathlib import Path
from multiprocessing import Process
import runner

ROOT = runner.ROOT
OUT = ROOT / "repaint.jsonl"


def targets():
    traded = {}
    for f in glob.glob(str(ROOT / "results" / "*" / "*.jsonl")):
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            if r.get("t_n"): traded.setdefault((r["strategy"], r["tf"]), {})[r["ticker"]] = r["file"]
    done = set()
    if OUT.exists():
        for l in open(OUT, encoding="utf-8"):
            r = json.loads(l); done.add((r["strategy"], r["tf"]))
    out = []
    for (sid, tf), tks in sorted(traded.items()):
        if (sid, tf) in done: continue
        tk = "SPY" if "SPY" in tks else sorted(tks)[0]
        out.append((sid, tf, tk, tks[tk]))
    return out


def work(wid, port, jobs):
    eng = runner.Engine(port)
    sdir = Path(runner.STRATS[0]).parent
    with open(ROOT / f"repaint_w{wid}.jsonl", "a", encoding="utf-8") as fo:
        for n, (sid, tf, tk, fname) in enumerate(jobs):
            if n and n % 150 == 0: eng.start()
            rec = {"strategy": sid, "tf": tf, "ticker": tk}
            try:
                r = eng.fs.call("load_session", {"script_path": str(sdir / fname),
                                                 "data_path": str(ROOT / "data" / tf / f"{tk}.csv")}, timeout=300)
                if not isinstance(r, dict) or "error" in r: rec["error"] = str(r)[:200]
                else:
                    c = eng.fs.call("check_repaint", {}, timeout=600)
                    if not isinstance(c, dict) or "verdict" not in c: rec["error"] = str(c)[:200]
                    else:
                        d = c.get("diff", {})
                        rec.update({"verdict": c["verdict"],
                                    "vectors": sorted({x.get("vector") for x in c.get("census", {}).get("findings", [])}),
                                    "as_written": d.get("trades_as_written"), "confirmed": d.get("trades_confirmed"),
                                    "matched": d.get("matched"), "drifted": d.get("drifted")})
            except Exception as e:
                rec["error"] = f"timeout/crash: {type(e).__name__}"; eng.start()
            fo.write(json.dumps(rec) + "\n"); fo.flush()
    eng.stop()


if __name__ == "__main__":
    if sys.argv[1:] == ["merge"]:
        with open(OUT, "a", encoding="utf-8") as fo:
            for f in sorted(glob.glob(str(ROOT / "repaint_w*.jsonl"))):
                fo.write(open(f, encoding="utf-8").read()); Path(f).unlink()
        print(sum(1 for _ in open(OUT, encoding="utf-8")), "verdicts in", OUT); sys.exit()
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    T = targets(); print(len(T), "strategy x timeframe checks", flush=True)
    ps = [Process(target=work, args=(i, 17560 + i, T[i::nw])) for i in range(nw)]
    for p in ps: p.start(); time.sleep(2)
    for p in ps: p.join()
    print("REPAINT DONE", flush=True)
