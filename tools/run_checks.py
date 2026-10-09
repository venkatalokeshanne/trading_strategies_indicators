"""
Run the independent checks in python/checks/ (one file per conversion, ``check() -> (ok, detail)``).

    python tools/run_checks.py            # all
    python tools/run_checks.py k13xEYxZ   # one or more ids
Exit 1 if any check fails.
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "python"))


def main(ids: list[str]) -> int:
    files = sorted((ROOT / "python" / "checks").glob("*.py"))
    if ids:
        files = [f for f in files if f.stem.split("-")[0] in ids]
    bad = 0
    for f in files:
        spec = importlib.util.spec_from_file_location(f"chk_{f.stem}", f)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            ok, detail = mod.check()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}\n{traceback.format_exc()[-600:]}"
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {f.stem}: {detail}")
    print(f"\n{len(files) - bad}/{len(files)} pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
