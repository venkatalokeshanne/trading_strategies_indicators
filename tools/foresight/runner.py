"""Plain backtests of every TradingView strategy (.pine, run as-is by Foresight) on every watchlist
ticker x timeframe. Each strategy runs with its own default inputs and strategy() settings, over the full
history; the last 30% of bars is scored again separately (an 'unseen part' check, no tuning anywhere).

N workers, each with its own headless Foresight (--serve --port). Work unit = one data file
(timeframe/ticker); a worker claims it with a lock file, loads the data once, then start_run's every
strategy against it. Results: results/<tf>/<TICKER>.jsonl (one line per strategy). Resumable."""
import os, sys, json, time, glob, socket, subprocess, traceback
from pathlib import Path
from multiprocessing import Process

ROOT = Path(__file__).parent
EXE = r"C:\Program Files\Foresight\Foresight.exe"
STRATS = sorted(glob.glob(r"C:\Users\annev\workspace\trading_strategies_indicators\TradingView\strategies\*.pine"))
TF_ORDER = ["daily", "1h", "15m", "5m"]
STRATS = STRATS[:int(os.environ.get("LIMIT", 10**6))]
RES = os.environ.get("RESULTS", "results")
OOS_FRAC = 0.7
KEEP = ["ntrade", "total_trades", "total_return_pct", "profit_all", "profit_factor", "win_rate_all", "sharpe", "sortino",
        "mdd", "expectancy", "expectancy_tstat", "sqn", "trades_per_month", "cagr", "buyhold_return_pct", "alpha_vs_buyhold",
        "avg_win", "avg_loss", "payoff_ratio", "max_consec_wins", "max_consec_losses", "time_in_market", "winning_months",
        "profit_buy", "profit_sell", "win_rate_buy", "win_rate_sell", "total_commission"]
OOS_KEEP = ["ntrade", "total_return_pct", "profit_all", "profit_factor", "win_rate_all", "sharpe", "mdd", "expectancy"]
sys.path.insert(0, str(ROOT))
from fsmcp import FS


def port_open(p):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", p)) == 0


class Engine:
    def __init__(self, port):
        self.port = port; self.srv = None; self.fs = None; self.start()

    def start(self):
        self.stop()
        env = dict(os.environ, FORESIGHT_THREADS="1")
        log = open(ROOT / "logs" / f"serve{self.port}.log", "ab")
        self.srv = subprocess.Popen([EXE, "--serve", "--port", str(self.port)], stdout=log, stderr=log, env=env,
                                    cwd=r"C:\Program Files\Foresight")
        for _ in range(240):
            if port_open(self.port): break
            time.sleep(0.5)
        self.fs = FS(port=self.port)
        self.fs.call("set_detail", {"level": "full"})

    def stop(self):
        for p in (getattr(self.fs, "p", None), self.srv):
            if p and p.poll() is None:
                p.kill()
                try: p.wait(10)
                except Exception: pass


def claim(tf, sym):
    lock = ROOT / RES / tf / f"{sym}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd); return True
    except FileExistsError:
        return False


def _agg(rets, bars, prefix):
    import statistics as st
    out = {prefix + "n": len(rets)}
    if not rets: return out
    pos = [r for r in rets if r > 0]; neg = [-r for r in rets if r <= 0]
    out.update({prefix + "win": round(100 * len(pos) / len(rets), 2), prefix + "avg": round(st.fmean(rets), 4),
                prefix + "med": round(st.median(rets), 4), prefix + "sum": round(sum(rets), 3),
                prefix + "pf": round(sum(pos) / sum(neg), 4) if sum(neg) > 0 else None,
                prefix + "avgwin": round(st.fmean(pos), 4) if pos else None,
                prefix + "avgloss": round(-st.fmean(neg), 4) if neg else None,
                prefix + "bars": round(st.fmean(bars), 1)})
    return out


def trade_stats(fs, handle, oos_bar):
    """Per-trade NET % return = pl / (entry_price * size): commission included, position size cancels out,
    so strategies with different sizing are comparable. Split at oos_bar by entry bar."""
    trades, off = [], 0
    while True:
        r = fs.call("get_trades", {"handle": handle, "offset": off, "limit": 1000}, timeout=180)
        if not isinstance(r, dict) or not r.get("trades"): break
        trades += r["trades"]; off += r["count"]
        if off >= r.get("total", 0): break
    rows = []
    for t in trades:
        den = (t.get("entry_price") or 0) * abs(t.get("size") or 0)
        if den <= 0 or t.get("exit_bar") is None: continue
        rows.append((t["entry_bar"], 100 * t["pl"] / den, t["exit_bar"] - t["entry_bar"], t["type"]))
    out = _agg([r for _, r, _, _ in rows], [b for _, _, b, _ in rows], "t_")
    out.update(_agg([r for e, r, _, _ in rows if e < oos_bar], [b for e, _, b, _ in rows if e < oos_bar], "is_"))
    out.update(_agg([r for e, r, _, _ in rows if e >= oos_bar], [b for e, _, b, _ in rows if e >= oos_bar], "oos_"))
    out["t_long"] = sum(1 for *_, d in rows if d == "buy"); out["t_short"] = len(rows) - out["t_long"]
    return out


def pick(val, keys):
    return {k: val.get(k) for k in keys} if isinstance(val, dict) else None


def worker(wid, port):
    eng = Engine(port)
    bad = json.loads((ROOT / "bad_strategies.json").read_text()) if (ROOT / "bad_strategies.json").exists() else {}
    while True:
        job = None
        for tf in TF_ORDER:
            for csv in sorted((ROOT / "data" / tf).glob("*.csv")):
                sym = csv.stem
                if (ROOT / RES / tf / f"{sym}.done").exists(): continue
                (ROOT / RES / tf).mkdir(parents=True, exist_ok=True)
                if claim(tf, sym): job = (tf, sym, csv); break
            if job: break
        if not job:
            if (ROOT / "fetch.finished").exists(): break
            time.sleep(60); continue
        tf, sym, csv = job
        out = ROOT / RES / tf / f"{sym}.jsonl"
        done = set()
        if out.exists():
            for line in out.read_text(encoding="utf-8").splitlines():
                try: done.add(json.loads(line)["strategy"])
                except Exception: pass
        nbars = sum(1 for _ in open(csv)) - 1
        oos_bar = int(nbars * OOS_FRAC)
        t0 = time.time(); n = 0
        try:
            r = eng.fs.call("load_session", {"script_path": str(ROOT / "loader.pine"), "data_path": str(csv)}, timeout=300)
            if not isinstance(r, dict) or "error" in r: raise RuntimeError(str(r)[:200])
        except Exception as e:
            print(f"w{wid} {tf} {sym}: data load failed {e}", flush=True)
            eng.start(); (ROOT / RES / tf / f"{sym}.lock").unlink(missing_ok=True); continue
        with open(out, "a", encoding="utf-8") as fo:
            for sp in STRATS:
                sid = Path(sp).name.split("-")[0].split(".")[0]
                if sid in done or bad.get(sid, 0) >= 3: continue
                rec = {"strategy": sid, "file": Path(sp).name, "ticker": sym, "tf": tf, "bars": nbars}
                try:
                    full = eng.fs.call("start_run", {"script_path": sp, "detail": "full"}, timeout=180)
                    if not isinstance(full, dict) or "ntrade" not in full:
                        rec["error"] = str(full)[:300]
                    else:
                        rec.update(pick(full, KEEP)); rec["family"] = full.get("family")
                        rec["from"] = full.get("scope", {}).get("from_date"); rec["to"] = full.get("scope", {}).get("to_date")
                        if (full.get("total_trades") or 0) > 0:
                            rec.update(trade_stats(eng.fs, full.get("handle", ""), oos_bar))
                        eng.fs.call("release_run", {"handle": full.get("handle", "")}, timeout=60)
                except Exception as e:          # hang or crash: restart this engine, count it against the strategy
                    rec["error"] = f"timeout/crash: {type(e).__name__}"
                    bad[sid] = bad.get(sid, 0) + 1
                    eng.start()
                    eng.fs.call("load_session", {"script_path": str(ROOT / "loader.pine"), "data_path": str(csv)}, timeout=300)
                fo.write(json.dumps(rec) + "\n"); fo.flush(); n += 1
        (ROOT / RES / tf / f"{sym}.done").write_text(f"{n} runs in {time.time() - t0:.0f}s by w{wid}")
        print(f"w{wid} {tf} {sym}: {n} runs, {time.time() - t0:.0f}s", flush=True)
    eng.stop()


if __name__ == "__main__":
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    (ROOT / "logs").mkdir(exist_ok=True)
    for f in (ROOT / RES).glob("*/*.lock"):        # stale locks from an interrupted run
        if not f.with_suffix(".done").exists(): f.unlink()
    ps = [Process(target=worker, args=(i, 17410 + i)) for i in range(nw)]
    for p in ps: p.start(); time.sleep(3)
    for p in ps: p.join()
    print("ALL DONE", flush=True)
