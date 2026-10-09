// lint: skip — browser-side helper for the TrendSpider live test (NOT a TrendSpider script).
// Paste this ONCE into the TrendSpider tab (javascript_exec) with the Custom Indicator Editor
// open. It installs window.__one(NAME, SRC): New indicator -> APPLY -> errors? -> Save ->
// verify the save through TrendSpider's own script list (never the search box, LESSONS L20).
// Then send batches built by tools/ts_batch_live.py (only their `R.push(...)` lines), e.g.
//   const one = window.__one; const R = []; R.push(await one("X_TV", "...")); R;
// Two scripts per call keeps it under the 45 s browser-call limit.
const sleep = ms => new Promise(r => setTimeout(r, ms));
const btn = t => [...document.querySelectorAll('button')].find(b => b.offsetWidth && b.textContent.trim() === t);
window.__saved = async () => {
  const r = await fetch('/authentication/1/api?key=&path=' + encodeURIComponent('/custom_scripting_webserver/1/scripts'), { credentials: 'include' });
  const j = await r.json(); const a = Array.isArray(j) ? j : (Object.values(j).find(Array.isArray) || []);
  return a.map(s => s.title);
};
window.__one = async (NAME, SRC) => {
  const out = { name: NAME };
  const before = (await window.__saved()).filter(t => t === NAME).length;
  if (before) { out.alreadySaved = before; return out; }               // never save twice
  const n = btn('New indicator') || btn('NEW INDICATOR'); if (n) { n.click(); await sleep(2500); }
  const yes = [...document.querySelectorAll('button')].find(b => b.offsetWidth && /^(yes|discard)$/i.test(b.textContent.trim()));
  if (yes) { yes.click(); await sleep(1500); }
  const view = document.querySelector('.cm-content').cmView.view;
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: SRC } });
  btn('Apply').click(); await sleep(6000);
  const pane = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Console');
  out.console = pane ? pane.closest('div').parentElement.innerText.replace(/^Console\s*/, '').slice(0, 300) : '';
  out.errors = [...document.querySelectorAll('[class*=error], [class*=Error], .cm-lintRange-error')]
    .filter(e => e.offsetWidth && e.innerText && e.innerText.trim()).map(e => e.innerText.trim().slice(0, 200)).slice(0, 3);
  if (view.state.doc.length === SRC.length && !out.errors.length && !/error/i.test(out.console)) {
    btn('Save').click(); await sleep(5000);
    out.saved = (await window.__saved()).filter(t => t === NAME).length;   // 0 = check again later, do NOT re-save
  }
  return out;
};
'helper installed';
