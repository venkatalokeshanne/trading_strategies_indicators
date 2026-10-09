"""Batch-generate TrendSpider AI drafts for every Pine script — no Claude involved.

Drives TrendSpider's own "Build a new indicator using AI" box in the Custom Indicator
Editor with Playwright: for each Pine source it sends the fixed PROMPT + the source, waits
for the generated code, saves it to TrendSpider/ai_drafts/<indicators|strategies>/<stem>.ai.js
and then REJECTS the code in the editor — nothing is ever saved to the TrendSpider account.
The drafts are first drafts only; each is reviewed and fixed later (pine-to-trendspider skill,
reference/10-trendspider-ai-prompt.md).

    python tools/ts_ai_drafts.py                    # everything still missing, smallest first
    python tools/ts_ai_drafts.py --type strategies --limit 20
    python tools/ts_ai_drafts.py --ids 02KcJZxe 7qUtuiBt
    python tools/ts_ai_drafts.py --retry-failed
    python tools/ts_ai_drafts.py --profile "C:/path/to/logged-in/profile"

First run: a Chromium window opens; log in to TrendSpider yourself (the tool never types
credentials) and the run continues. The login is kept in the profile folder (.ts_profile/
by default, gitignored). Resumable: progress is in TrendSpider/ai_drafts/index.json.
Requires: pip install playwright && python -m playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "TrendSpider" / "ai_drafts"
INDEX = OUT / "index.json"
LOGS = REPO / "logs" / "ts_ai_drafts"          # screenshots of failures (gitignored)

PROMPT = ("Convert this TradingView Pine Script into a working TrendSpider custom JavaScript indicator\n"
          "that reproduces the Pine logic EXACTLY (same values, same signal bars), and map out the\n"
          "scanning and strategy signals.")

GEN_TIMEOUT_S = 600
STOP_AFTER_FAILURES = 3

# ── page-side helpers ───────────────────────────────────────────────────────
JS_CLICK = """([pattern]) => {
  const rx = new RegExp(pattern, 'i');
  const label = e => ((e.textContent || '').trim() + ' ' + (e.title || '') + ' ' + (e.getAttribute('aria-label') || '')).trim();
  const pick = sel => [...document.querySelectorAll(sel)]
    .filter(e => e.offsetWidth && rx.test(label(e)))
    .sort((a, b) => (a.textContent || '').length - (b.textContent || '').length)[0];
  const el = pick('button, [role=button], [role=tab]') || pick('a, div, span');   // real buttons before tooltips
  if (!el) return false;
  let t = el;
  for (let i = 0; i < 6 && t; i++) {
    const k = Object.keys(t).find(k => k.startsWith('__reactProps$'));
    if (k && t[k].onClick) { t[k].onClick({ preventDefault() {}, stopPropagation() {}, currentTarget: t, target: t }); return 'react'; }
    t = t.parentElement;
  }
  el.click(); return 'dom';
}"""

JS_STATE = """() => {
  const btn = rx => [...document.querySelectorAll('button')].some(b => b.offsetWidth && rx.test((b.textContent || '') + ' ' + (b.title || '') + ' ' + (b.getAttribute('aria-label') || '')));
  const cm = document.querySelector('.cm-content');
  const ta = [...document.querySelectorAll('textarea')].find(e => e.offsetWidth && /instructions or questions for the AI/.test(e.placeholder));
  let panel = '';
  if (ta) { let p = ta; for (let i = 0; i < 5 && p.parentElement; i++) p = p.parentElement; panel = p.innerText.slice(0, 600); }
  return {
    editor: !!cm,
    doc: cm ? cm.cmView.view.state.doc.toString() : '',
    aiBox: !!ta,
    thinking: btn(/AI is thinking/),
    accept: btn(/Accept code/),
    generate: btn(/^Generate Code/),
    chooser: /Open a workspace of yours/.test(document.body.innerText.slice(0, 3000)),
    loggedIn: !!document.querySelector('.cm-content') || /Strategy Tester/.test(document.body.innerText.slice(0, 20000)),
    panel,
  };
}"""

JS_FILL = """([text]) => {
  const ta = [...document.querySelectorAll('textarea')].find(e => e.offsetWidth && /instructions or questions for the AI/.test(e.placeholder));
  if (!ta) return -1;
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, text);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  return ta.value.length;
}"""


def load_index() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def save_index(idx: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(idx, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def queue(args, idx: dict) -> list[Path]:
    kinds = ["indicators", "strategies"] if args.type == "all" else [args.type]
    files = [f for k in kinds for f in (REPO / "TradingView" / k).glob("*.pine")]
    if args.ids:
        files = [f for f in files if f.stem.split("-")[0] in set(args.ids)]
    files.sort(key=lambda f: f.stat().st_size)
    out = []
    for f in files:
        rec = idx.get(f.stem.split("-")[0])
        if rec and rec["status"] == "ok" and not args.redo:
            continue
        if rec and rec["status"] != "ok" and not (args.retry_failed or args.ids or args.redo):
            continue
        out.append(f)
    return out[: args.limit] if args.limit else out


class Driver:
    def __init__(self, page, workspace: str):
        self.page, self.workspace = page, workspace

    def state(self) -> dict:
        return self.page.evaluate(JS_STATE)

    def click(self, pattern: str) -> bool:
        return bool(self.page.evaluate(JS_CLICK, [pattern]))

    def ready_editor(self) -> None:
        """Chart loaded, Custom Indicator Editor open, AI box empty and visible."""
        deadline = time.time() + 180
        while time.time() < deadline:
            s = self.state()
            if s["chooser"]:
                self.click("^" + self.workspace)
            elif not s["loggedIn"]:
                print("  waiting for you to log in to TrendSpider in the browser window ...", flush=True)
                self.page.wait_for_timeout(10_000)
                deadline = time.time() + 180               # logging in does not use up the budget
                continue
            elif s["accept"]:
                self.click("reject generated code")           # leave nothing in the editor
            elif not s["editor"]:
                self.click("^Custom Indicator Editor")
            elif not s["aiBox"]:
                self.click("Build a new indicator using AI")
            elif s["generate"]:
                return
            self.page.wait_for_timeout(2500)
        raise RuntimeError("could not reach the AI box (layout changed?)")

    def generate(self, text: str) -> tuple[str, str]:
        self.ready_editor()
        before = self.state()["doc"]
        box = self.page.locator("textarea[placeholder*='instructions or questions for the AI']").first
        box.fill(text)                                   # real input events (React sees them)
        n = len(box.input_value())
        if n != len(text):
            raise RuntimeError(f"prompt not accepted by the text box ({n} of {len(text)} chars)")
        gen = self.page.get_by_role("button", name="Generate Code", exact=True).first
        for _ in range(3):                               # real mouse click; confirm the AI started
            gen.click(timeout=10_000)
            self.page.wait_for_timeout(4000)
            if self.state()["thinking"] or self.state()["accept"]:
                break
        else:
            raise RuntimeError("Generate Code did not start the AI")
        t0 = time.time()
        while time.time() - t0 < GEN_TIMEOUT_S:
            self.page.wait_for_timeout(5000)
            s = self.state()
            if s["accept"] and not s["thinking"]:
                code = s["doc"]
                self.click("reject generated code")
                if not code.strip() or code == before:
                    raise RuntimeError("AI finished but the editor is empty")
                return code, ""
            if not s["thinking"] and s["generate"] and time.time() - t0 > 20:
                raise RuntimeError("AI stopped without code: " + " ".join(s["panel"].split())[:300])
        raise RuntimeError(f"no code after {GEN_TIMEOUT_S}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", choices=["all", "indicators", "strategies"], default="all")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--redo", action="store_true", help="regenerate even if a draft exists")
    ap.add_argument("--profile", default=str(REPO / ".ts_profile"))
    ap.add_argument("--workspace", default="Default Workspace")
    ap.add_argument("--headless", action="store_true", help="only once the profile is logged in")
    args = ap.parse_args()

    idx = load_index()
    todo = queue(args, idx)
    print(f"{len(todo)} scripts to draft; drafts in {OUT.relative_to(REPO)}", flush=True)
    if not todo:
        return 0

    from playwright.sync_api import sync_playwright
    LOGS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(args.profile, headless=args.headless,
                                                    viewport={"width": 1600, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://charts.trendspider.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        drv = Driver(page, args.workspace)
        fails = 0
        for n, f in enumerate(todo, 1):
            tv_id, kind = f.stem.split("-")[0], f.parent.name
            src = f.read_text(encoding="utf-8", errors="replace")
            t0 = time.time()
            try:
                code, _ = drv.generate(PROMPT + "\n\n" + src)
                dest = OUT / kind / (f.stem + ".ai.js")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(code, encoding="utf-8")
                idx[tv_id] = {"status": "ok", "file": dest.relative_to(REPO).as_posix(), "chars": len(code),
                              "pine": f.relative_to(REPO).as_posix(), "seconds": round(time.time() - t0),
                              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                fails = 0
                print(f"[{n}/{len(todo)}] ok    {tv_id} {kind:<10} {len(code):6d} chars {time.time() - t0:5.0f}s", flush=True)
            except Exception as e:
                fails += 1
                idx[tv_id] = {"status": "failed", "error": str(e)[:400], "pine": f.relative_to(REPO).as_posix(),
                              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                print(f"[{n}/{len(todo)}] FAIL  {tv_id}: {e}", flush=True)
                try:
                    page.screenshot(path=str(LOGS / f"{tv_id}.png"))
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_timeout(8000)
                except Exception:
                    pass
            save_index(idx)
            if fails >= STOP_AFTER_FAILURES:
                print(f"stopping: {fails} failures in a row (logged out? AI limit reached?) — "
                      f"see {LOGS.relative_to(REPO)} and the last errors in index.json", flush=True)
                break
        ctx.close()
    ok = sum(1 for r in idx.values() if r["status"] == "ok")
    print(f"done: {ok} drafts in total", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
