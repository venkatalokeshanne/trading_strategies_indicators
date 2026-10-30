import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def pine_repo() -> Path:
    return (ROOT / os.environ.get("PINE_REPO_PATH", "..")).resolve()


def setup_pinelib() -> None:
    # the TV repo's pyproject is not pip-installable, so import pinelib from its python/ dir
    p = str(pine_repo() / "python")
    if p not in sys.path:
        sys.path.insert(0, p)


def load(db: str | None = None, cost_mult: float = 1.0) -> dict:
    load_env()
    cfg = yaml.safe_load((ROOT / "config/default.yaml").read_text())
    wl = yaml.safe_load((ROOT / "config/watchlists.yaml").read_text())
    cfg["watchlists"] = wl
    cfg["universe"] = sorted({s for v in wl.values() for s in v})
    cfg["paths"] = {k: ROOT / v for k, v in cfg["paths"].items()}
    if db:                                              # a second store (e.g. the x2-cost run) next to the main one
        cfg["paths"]["db"] = ROOT / db
    if cost_mult != 1.0:                                # stress: scale commission and slippage (part of the result cache key)
        for c in cfg["costs"].values():
            c["commission_per_share"] *= cost_mult
            c["slippage_bps"] *= cost_mult
    return cfg


def tier(cfg: dict, symbol: str) -> str:
    for t, syms in cfg["tiers"].items():
        if isinstance(syms, list) and symbol in syms:
            return t
    return cfg["tiers"]["default"]
