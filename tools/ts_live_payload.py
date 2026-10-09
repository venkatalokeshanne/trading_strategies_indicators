"""
Build the JavaScript snippets for the live TrendSpider test (reference/09-trendspider-live.md).

The converted script is embedded as a JSON string, so it reaches the editor byte-for-byte —
no hand copying, no escaping by eye (LESSONS L15). Each snippet is pasted into the browser
tool's javascript_exec on charts.trendspider.com and returns a small JSON report.

    python tools/ts_live_payload.py apply  TrendSpider/strategies/X.trendspider.js   > apply.js
    python tools/ts_live_payload.py find   TrendSpider/strategies/X.trendspider.js   # is the _TV name already saved?
    python tools/ts_live_payload.py remove TrendSpider/strategies/X.trendspider.js   # take it off the chart after the test
    python tools/ts_live_payload.py tester TrendSpider/strategies/X.trendspider.js   # strategies: wire signals, run Tester

The lint must be clean first; `apply` refuses a file that has lint errors.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]

APPLY = r"""// apply: put the script in the Custom Indicator Editor and run it (does NOT save)
const SRC = __SRC__;
const NAME = __NAME__;
const view = document.querySelector('.cm-content') && document.querySelector('.cm-content').cmView.view;
if (!view) throw new Error('Custom Indicator Editor is not open — open it first (reference/09 step 2)');
const current = view.state.doc.toString();
const currentName = (current.match(/describe_indicator\s*\(\s*['"]([^'"]+)/) || [])[1] || null;
let result;
const isExample = /Example colored MA/.test(current) || current.trim() === '';
if (!isExample && currentName !== NAME) {
  // the editor holds some other script; don't overwrite it — start a new one first
  result = ({ refused: true, editorHolds: currentName, action: 'click "New indicator" (or NEW INDICATOR) and re-run' });
} else {
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: SRC } });
  const btn = t => [...document.querySelectorAll('button')].find(b => b.offsetWidth && b.textContent.trim() === t);
  btn('Apply').click();
  await new Promise(r => setTimeout(r, 5000));
  const consolePane = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Console');
  const consoleText = consolePane ? consolePane.closest('div').parentElement.innerText : '';
  const errorLike = [...document.querySelectorAll('[class*=error], [class*=Error], .cm-lintRange-error')]
    .filter(e => e.offsetWidth && e.innerText && e.innerText.trim()).map(e => e.innerText.trim().slice(0, 200));
  result = ({
    loaded: view.state.doc.length === SRC.length,
    previewLegend: [...document.querySelectorAll('[class*="legend-item--custom_script"]')].filter(e => e.offsetWidth)
      .map(e => e.innerText.trim().replace(/\s+/g, ' ').slice(0, 80)),
    errors: errorLike.slice(0, 5),
    console: consoleText.replace(/^Console\s*/, '').slice(0, 600),
  });
}
result;
"""

FIND = r"""// find: is this _TV name already in the "Yours" list?
const NAME = __NAME__;
const inp = document.querySelector('input[placeholder="Search for custom indicators"]');
if (!inp) throw new Error('open the Custom Indicator Editor first');
const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
set.call(inp, NAME); inp.dispatchEvent(new Event('input', { bubbles: true }));
await new Promise(r => setTimeout(r, 1500));
const rows = inp.closest('div').parentElement.parentElement.innerText.split('\n').map(s => s.trim());
set.call(inp, ''); inp.dispatchEvent(new Event('input', { bubbles: true }));
({ name: NAME, saved: rows.includes(NAME), matches: rows.filter(r => r.includes(NAME)) });
"""

REMOVE = r"""// remove: take the saved indicator off the chart. Matches the legend row by its OWN text —
// never pick a remove button by search alone; it can belong to the user's other indicators.
const SHORT = __SHORT__;
// legend text is "BOSC\n522.197" — normalise whitespace before matching (LESSONS L17)
const norm = e => e.innerText.replace(/\s+/g, ' ').trim();
const rows = () => [...document.querySelectorAll('.chart-indicators-list__indicator')].filter(e => e.offsetWidth);
const mine = rows().filter(e => { const t = norm(e); return t === SHORT || t.startsWith(SHORT + ' '); });
let result;
const before = rows().map(e => norm(e).slice(0, 40));
if (mine.length !== 1) {
  result = ({ removed: false, reason: `expected exactly one legend row starting with "${SHORT}", found ${mine.length}`, legends: before });
} else {
  const x = mine[0].querySelector('[title="Remove this indicator from your charts"]');
  if (x) x.click();
  await new Promise(r => setTimeout(r, 1500));
  result = ({ removed: !!x, before, after: rows().map(e => norm(e).slice(0, 40)) });
}
result;
"""

TESTER = r"""// tester: wire the _TV signals into a NEW Strategy Tester strategy and run it on 10,000 candles.
// Prerequisites (reference/09 §8): the Strategy Tester tab is open, "New strategy" clicked,
// "skip to point&click editor" clicked, panel maximised. Uses DOM clicks only — coordinate
// clicks race the menu animations. Does NOT save the strategy.
const NAME = __NAME__, ENTRY = __ENTRY__, EXIT = __EXIT__;
const wait = ms => new Promise(r => setTimeout(r, ms));
const vis = sel => [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
const near = (list, rect) => list.sort((a, b) => {
  const d = e => { const r = e.getBoundingClientRect(); return Math.abs(r.y - rect.bottom) + Math.abs(r.x - rect.x); };
  return d(a) - d(b); })[0];
const log = [];
async function pickSignal(addBtn, signal) {
  addBtn.click(); await wait(900);
  const cond = near(vis('button.md-button, md-menu-item button').filter(b => b.textContent.trim() === 'Condition'), addBtn.getBoundingClientRect());
  cond.click(); await wait(1200);
  vis('.picker-menu__item').find(e => e.innerText.trim().split('\n')[0].trim() === 'Indicator').click(); await wait(1500);
  const want = `${NAME}, ${signal} (on chart)`;
  const row = vis('.picker-menu__item').find(e => e.innerText.trim() === want);
  if (!row) throw new Error('signal not in picker: ' + want + ' — is the _TV indicator on the chart?');
  row.click(); await wait(1500);
  vis('.picker-menu__item').find(e => e.innerText.trim() === 'Signal emerged').click(); await wait(1200);
  log.push('wired ' + signal);
}
// entry: the left panel's "Add a condition"
await pickSignal(vis('button').filter(b => b.textContent.trim() === 'Add a condition').sort((a, b) => a.getBoundingClientRect().x - b.getBoundingClientRect().x)[0], ENTRY);
// exit: "Add an exit condition…" → Script (NOT "List of signals": that is raw timestamps)
const addExit = vis('button').find(b => b.textContent.trim().startsWith('Add an exit condition'));
addExit.click(); await wait(900);
near(vis('button.md-button, md-menu-item button').filter(b => b.textContent.trim() === 'Script'), addExit.getBoundingClientRect()).click(); await wait(1500);
await pickSignal(vis('button').filter(b => b.textContent.trim() === 'Add a condition').sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x)[0], EXIT);
document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await wait(500);
// backtest length: the "N candles" MUI button → slider to max → APPLY
const rangeEl = [...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().width > 0 && /^\d+ candles$/.test(e.textContent.trim())).pop();
let t = rangeEl; for (let i = 0; i < 6 && t; i++) { const k = Object.keys(t).find(k => k.startsWith('__reactProps$')); if (k && t[k].onClick) { t[k].onClick({ preventDefault(){}, stopPropagation(){}, currentTarget: t, target: t, nativeEvent: {} }); break; } t = t.parentElement; }
await wait(1200);
const s = vis('input[type=range]')[0];
Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(s, s.max);
s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); await wait(600);
const pop = vis('.MuiPaper-root').filter(e => /Define your backtest/.test(e.innerText)).pop();
[...pop.querySelectorAll('button')].find(b => b.textContent.trim().toUpperCase() === 'APPLY').click(); await wait(1500);
// run
const run = vis('button').find(b => b.textContent.trim() === 'Run');
const rk = Object.keys(run).find(k => k.startsWith('__reactProps$'));
rk && run[rk].onClick ? run[rk].onClick({ preventDefault(){}, stopPropagation(){}, currentTarget: run, target: run, nativeEvent: {} }) : run.click();
await wait(15000);
const txt = document.body.innerText;
const stat = label => ((txt.match(new RegExp(label + '\\n([^\\n]+)')) || [])[1] || null);
({ log, candles: [...document.querySelectorAll('button')].map(b => b.textContent.trim()).find(x => /candles$/.test(x)),
   market: stat('Market'), netPerf: stat('Net Perf, all'), assetPerf: stat('Asset Perf.'), positions: stat('Positions'),
   wins: stat('Wins'), maxDD: stat('Max DD') });
"""


def describe(src: str) -> tuple[str, str]:
    m = re.search(r"describe_indicator\s*\(\s*(['\"])(.*?)\1(.*?)\)\s*;", src, re.S)
    if not m:
        sys.exit("no describe_indicator(...) found")
    name = m.group(2)
    short = re.search(r"shortName\s*:\s*(['\"])(.*?)\1", m.group(3))
    return name, short.group(2) if short else name


def signals(src: str) -> tuple[str, str]:
    """The script's entry and exit signal names (register_signal literals)."""
    names = re.findall(r"register_signal\s*\([^;]*?,\s*(['\"])(.*?)\1\s*\)", src)
    names = [n for _, n in names]
    entry = next((n for n in names if n.endswith("Entry")), None)
    exit_ = next((n for n in names if n.endswith("Exit")), None)
    if not (entry and exit_):
        sys.exit(f"need one signal ending 'Entry' and one ending 'Exit'; found {names}")
    return entry, exit_


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("apply", "find", "remove", "tester"):
        sys.exit(__doc__)
    mode, path = sys.argv[1], Path(sys.argv[2])
    src = path.read_text(encoding="utf-8")
    name, short = describe(src)
    if mode == "apply":
        lint = subprocess.run([sys.executable, str(ROOT / "tools" / "lint_trendspider.py"), str(path)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        if lint.returncode != 0:
            sys.exit("lint has errors — fix them before the live test:\n" + lint.stdout)
        print(APPLY.replace("__SRC__", json.dumps(src)).replace("__NAME__", json.dumps(name)))
    elif mode == "find":
        print(FIND.replace("__NAME__", json.dumps(name)))
    elif mode == "tester":
        entry, exit_ = signals(src)
        print(TESTER.replace("__NAME__", json.dumps(name)).replace("__ENTRY__", json.dumps(entry))
              .replace("__EXIT__", json.dumps(exit_)))
    else:
        print(REMOVE.replace("__SHORT__", json.dumps(short)))


if __name__ == "__main__":
    main()
