"""Compare the JS simulation's trades with Foresight's recorded trades (pine_screen/archive) for iz6acv9B."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\annev\workspace\pine_screen")
import extras
HERE = Path(__file__).parent
SID = "iz6acv9B"


def foresight(tf, tk):
    meta, c = extras.load("tv", tf, tk)
    s0, n = meta["index"][SID]; T = meta["text"]
    out = []
    for i in range(s0, s0 + n):
        if c["exit_bar"][i] < 0: continue
        out.append((c["entry_bar"][i], c["exit_bar"][i], -1 if c["short"][i] else 1, int(c["size"][i]),
                    round(c["entry_price"][i], 6), round(c["exit_price"][i], 6), T["exit_id"][c["exit_id"][i]] or T["exit_comment"][c["exit_comment"][i]]))
    return sorted(out)


def sim(tf, tk):
    csv = Path(r"C:\Users\annev\workspace\pine_screen\data") / tf / f"{tk}.csv"
    t = json.loads(subprocess.run(["node", str(HERE / "run_sim.js"), str(csv)], capture_output=True, text=True, check=True).stdout)
    return sorted((x["entryBar"], x["exitBar"], x["dir"], int(x["qty"]), round(x["entryPx"], 6), round(x["exitPx"], 6), x["exitId"] or x["comment"]) for x in t)


if __name__ == "__main__":
    cases = [a.split(":") for a in sys.argv[1:]] or [("daily", "NVDA")]
    for tf, tk in cases:
        f, s = foresight(tf, tk), sim(tf, tk)
        same = sum(1 for a, b in zip(f, s) if a == b)
        first = next(((a, b) for a, b in zip(f, s) if a != b), None)
        print(f"{tf} {tk}: foresight {len(f)} trades, sim {len(s)}, identical {same}" + ("" if first is None else f"\n   first difference:\n   F {first[0]}\n   S {first[1]}"))
