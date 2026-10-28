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


def load() -> dict:
    load_env()
    cfg = yaml.safe_load((ROOT / "config/default.yaml").read_text())
    wl = yaml.safe_load((ROOT / "config/watchlists.yaml").read_text())
    cfg["watchlists"] = wl
    cfg["universe"] = sorted({s for v in wl.values() for s in v})
    cfg["paths"] = {k: ROOT / v for k, v in cfg["paths"].items()}
    return cfg


def tier(cfg: dict, symbol: str) -> str:
    for t, syms in cfg["tiers"].items():
        if isinstance(syms, list) and symbol in syms:
            return t
    return cfg["tiers"]["default"]
