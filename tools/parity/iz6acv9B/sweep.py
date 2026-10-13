"""Every archived stock x timeframe: the simulation's trades against Foresight's (Foresight's extra end-of-data close
of the still-open position is not counted)."""
import json, collections
from pathlib import Path
import compare
A = Path(r"C:\Users\annev\workspace\pine_screen\archive\tv")
tot = collections.Counter(); bad = []
for f in sorted(A.glob("*/*.check.json")):
    tf, tk = f.parent.name, f.name.split(".")[0]
    try:
        F, S = compare.foresight(tf, tk), compare.sim(tf, tk)
    except KeyError:
        continue                                    # strategy not in this dataset (no trades there)
    except TypeError as e:
        bad.append((tf, tk, "NaN in sim", str(e)[:40])); continue
    extra = len(F) - len(S)
    same = sum(1 for a, b in zip(F, S) if a == b)
    tot["sets"] += 1; tot["trades"] += len(S); tot["identical"] += same
    if same != len(S) or extra not in (0, 1): bad.append((tf, tk, len(F), len(S), same))
print(dict(tot)); print("sets with any difference:", len(bad)); print(bad[:20])
