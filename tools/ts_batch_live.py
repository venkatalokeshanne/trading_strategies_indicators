"""Compact live-test batch: python mkbatch.py OUT file1 file2 ...  (helper once, short headers)"""
import json, re, sys
from pathlib import Path
HELPER = r"""const sleep = ms => new Promise(r => setTimeout(r, ms));
const btn = t => [...document.querySelectorAll('button')].find(b => b.offsetWidth && b.textContent.trim() === t);
const inp = document.querySelector('input[placeholder="Search for custom indicators"]');
const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
const listed = async N => { set.call(inp, N); inp.dispatchEvent(new Event('input', { bubbles: true })); await sleep(1500);
  const rows = inp.closest('div').parentElement.parentElement.innerText.split('\n').map(s => s.trim());
  set.call(inp, ''); inp.dispatchEvent(new Event('input', { bubbles: true })); return rows.includes(N); };
const one = async (NAME, SRC) => { const out = { name: NAME };
  if (await listed(NAME)) { out.alreadySaved = true; return out; }
  let view = document.querySelector('.cm-content').cmView.view; const cur = view.state.doc.toString();
  const curName = (cur.match(/describe_indicator\s*\(\s*['"]([^'"]+)/) || [])[1] || '';
  const blank = /Example colored MA/.test(cur) || cur.trim() === '';
  if (!blank && !/_TV$/.test(curName)) { out.refused = 'editor holds ' + curName; return out; }
  if (!blank) { const n = btn('New indicator') || btn('NEW INDICATOR'); if (n) n.click(); await sleep(2500);
    const yes = [...document.querySelectorAll('button')].find(b => b.offsetWidth && /^(yes|discard)$/i.test(b.textContent.trim())); if (yes) { yes.click(); await sleep(1500); }
    view = document.querySelector('.cm-content').cmView.view; }
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: SRC } });
  btn('Apply').click(); await sleep(6000);
  const pane = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Console');
  out.console = pane ? pane.closest('div').parentElement.innerText.replace(/^Console\s*/, '').slice(0, 300) : '';
  out.errors = [...document.querySelectorAll('[class*=error], [class*=Error], .cm-lintRange-error')].filter(e => e.offsetWidth && e.innerText && e.innerText.trim()).map(e => e.innerText.trim().slice(0, 200)).slice(0, 3);
  out.legend = [...document.querySelectorAll('[class*="legend-item--custom_script"]')].filter(e => e.offsetWidth).map(e => e.innerText.trim().replace(/\s+/g, ' ').slice(0, 60));
  if (view.state.doc.length === SRC.length && !out.errors.length && !/error/i.test(out.console)) { btn('Save').click(); await sleep(4000); out.saved = await listed(NAME); }
  return out; };
"""
out, files = sys.argv[1], sys.argv[2:]
calls = []
for f in files:
    src = Path(f).read_text(encoding="utf-8")
    url = re.search(r"Source URL\s*:\s*(\S+)", src).group(1)
    body = re.sub(r"\A/\*.*?\*/\s*", "", src, flags=re.S)
    body = "\n".join(l for l in body.splitlines() if l.strip() and not l.strip().startswith("//")) + "\n"
    short = f"// Converted from TradingView Pine Script: {url}\n// Full header and notes: github.com/venkatalokeshanne/trading_strategies_indicators\n" + body
    name = re.search(r"describe_indicator\s*\(\s*'([^']+)'", body).group(1)
    calls.append(f"R.push(await one({json.dumps(name)}, {json.dumps(short)}));")
Path(out).write_text(HELPER + "const R = [];\n" + "\n".join(calls) + "\nR;\n", encoding="utf-8")
print(out, len(Path(out).read_text(encoding='utf-8')), "chars")
