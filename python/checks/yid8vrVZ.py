"""Independent check — XAUUSD Quant SMC, 10-minute short title (yid8vrVZ): the script is the same as qWRZMcV0 (only the short title differs); this runs the shared independent reference (qWRZMcV0.py) on 10-minute and 15-minute charts of this id."""
from qWRZMcV0 import make, one


def check():
    msgs, allok = [], True
    for seed, n, freq, tf in ((6, 40000, "10min", "10"), (7, 30000, "15min", "15")):
        ok, m = one(make(seed, n, freq), tf, "yid8vrVZ")
        allok &= ok
        msgs.append(m)
    return allok, " | ".join(msgs)
