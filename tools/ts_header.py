"""Write a TrendSpider conversion with the standard header, from a body file + progress metadata.

    python tools/ts_header.py <id> <body.js> --placement overlay|"lower pane" [--status FULL]
        [--words "..."] [--dev "..."] [--notcarried "..."] [--from-ai]

The body must start with describe_indicator('<Title>_TV', ...). Output:
TrendSpider/<indicators|strategies>/<pine stem>.trendspider.js
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("body")
    ap.add_argument("--placement", required=True)
    ap.add_argument("--status", default="FULL")
    ap.add_argument("--words", default="")
    ap.add_argument("--dev", default="none.")
    ap.add_argument("--notcarried", default="none.")
    ap.add_argument("--from-ai", action="store_true")
    a = ap.parse_args()
    meta = json.loads((ROOT / "progress" / "progress.json").read_text(encoding="utf-8"))["scripts"][a.id]
    pine = ROOT / meta["file"]
    src = pine.read_text(encoding="utf-8", errors="replace")
    kind = "strategies" if pine.parent.name == "strategies" else "indicators"
    m = re.search(r"\b(?:indicator|strategy|study)\s*\(\s*(?:title\s*=\s*)?(['\"])(.*?)\1", src)
    title = m.group(2) if m else meta.get("title", a.id)
    ver = (re.search(r"//@version=(\d+)", src) or [None, "?"])[1]
    lic = "MPL 2.0" if "Mozilla Public License" in src else ("CC BY-NC-SA 4.0" if "creativecommons" in src.lower() else "not stated")
    body = Path(a.body).read_text(encoding="utf-8").strip() + "\n"
    ts_name = re.search(r"describe_indicator\s*\(\s*'([^']+)'", body).group(1)
    url = meta.get("url") or f"https://www.tradingview.com/script/{pine.stem}"
    url = re.sub(r"https://\w+\.tradingview\.com", "https://www.tradingview.com", url)

    def wrap(label: str, text: str) -> str:
        words, lines, cur = text.split(), [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 84:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        return f" * {label}" + "\n *   ".join(lines) + "\n"

    head = ("/*\n * ── Converted from TradingView Pine Script ─────────────────────────────\n"
            f" * Original     : {title}\n * Author       : {meta.get('author') or 'see Source URL'}\n"
            f" * Source URL   : {url}\n * Pine version : v{ver}\n * Licence      : {lic}\n"
            f" * Type         : {'strategy (signals)' if kind == 'strategies' else 'indicator'}\n"
            f" * Placement    : {a.placement}\n * Status       : {a.status}\n"
            f" * Converted    : {date.today().isoformat()} by Claude (pine-to-trendspider skill)"
            f"{', from a TrendSpider-AI draft' if a.from_ai else ''}\n * TrendSpider name : {ts_name}\n *\n")
    if a.words:
        head += wrap("The Pine original, in words: ", a.words) + " *\n"
    head += wrap("Deviations from the original: ", a.dev) + wrap("Not carried over: ", a.notcarried)
    head += " * ────────────────────────────────────────────────────────────────────────\n */\n"
    out = ROOT / "TrendSpider" / kind / f"{pine.stem}.trendspider.js"
    out.write_text(head + body, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), "|", ts_name)


if __name__ == "__main__":
    main()
