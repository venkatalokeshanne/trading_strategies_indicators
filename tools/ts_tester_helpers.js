// Paste once per page load into the browser tool's javascript_exec on charts.trendspider.com
// (after tools/ts_live_helper.js). Installs the faster Strategy Tester loop, reference/09 §8b:
//   window.__openSearch(NAME)   open Manage Indicators and type NAME (then: real clicks on the dialog title (420,68),
//                               the row (440,190) and APPLY (1146,664))
//   window.__openTester()       click the Strategy Tester tab and the "skip to point&click editor" link
//                               (then a real click on the maximise button (1432,474))
//   window.__tester(NAME, ENTRY, EXIT)   wire two signals into the new strategy, 10,000 candles, Run
//   window.__results()          read the Tester summary ~11 s after Run
//   window.__next()             click YES in "lose unsaved changes" and open a fresh tester
//   window.__remove(SHORT)      take every legend row starting with SHORT off the chart
//   window.__cleanup([names])   YES + remove each name + return the legend (must equal the user's original list)
//   window.__legend()           the chart legend rows
window.__legend = () => [...document.querySelectorAll('.chart-indicators-list__indicator')].filter(e => e.offsetWidth).map(e => e.innerText.replace(/\s+/g, ' ').trim().slice(0, 34));
window.__openSearch = async (NAME) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const vis = sel => [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
  let inp = null;
  for (let a = 0; a < 3 && !inp; a++) {
    const mb = vis('button[title="Manage Indicators"]').find(b => !b.textContent.trim());
    if (!mb) return 'no manage button';
    mb.click(); await wait(2200);
    inp = vis('input').find(i => /search/i.test(i.placeholder || '') && i.getBoundingClientRect().y > 80 && i.getBoundingClientRect().x > 300);
  }
  if (!inp) return 'dialog did not open';
  inp.focus(); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, NAME);
  inp.dispatchEvent(new Event('input', { bubbles: true })); await wait(1500);
  return 'ok';
};
window.__openTester = async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const tab = [...document.querySelectorAll('*')].filter(e => e.offsetWidth && e.children.length === 0 && e.textContent.trim() === 'Strategy Tester' && e.getBoundingClientRect().y > 300)[0];
  if (tab) { (tab.closest('button,a,[role=tab]') || tab).click(); await wait(4000); }
  const skip = [...document.querySelectorAll('*')].filter(e => e.offsetWidth && e.children.length === 0 && /skip to point/i.test(e.textContent))[0];
  if (skip) { (skip.closest('button,a') || skip).click(); await wait(2500); }
  return { tab: !!tab, skip: !!skip };
};
window.__tester = async (NAME, ENTRY, EXIT) => {
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
    const tail = `, ${signal} (on chart)`;
    const isRow = txt => txt.startsWith(NAME) && txt.endsWith(tail) && /^( \(.*\))?$/.test(txt.slice(NAME.length, txt.length - tail.length));
    const row = vis('.picker-menu__item').find(e => isRow(e.innerText.trim()));
    if (!row) throw new Error('signal not in picker: ' + NAME + tail + ' — is the _TV indicator on the chart?');
    row.click(); await wait(1500);
    vis('.picker-menu__item').find(e => e.innerText.trim() === 'Signal emerged').click(); await wait(1200);
    log.push('wired ' + signal);
  }
  await pickSignal(vis('button').filter(b => b.textContent.trim() === 'Add a condition').sort((a, b) => a.getBoundingClientRect().x - b.getBoundingClientRect().x)[0], ENTRY);
  const addExit = vis('button').find(b => b.textContent.trim().startsWith('Add an exit condition'));
  addExit.click(); await wait(900);
  near(vis('button.md-button, md-menu-item button').filter(b => b.textContent.trim() === 'Script'), addExit.getBoundingClientRect()).click(); await wait(1500);
  await pickSignal(vis('button').filter(b => b.textContent.trim() === 'Add a condition').sort((a, b) => b.getBoundingClientRect().x - a.getBoundingClientRect().x)[0], EXIT);
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await wait(500);
  const rangeEl = [...document.querySelectorAll('*')].filter(e => e.getBoundingClientRect().width > 0 && /^\d+ candles$/.test(e.textContent.trim())).pop();
  let t = rangeEl; for (let i = 0; i < 6 && t; i++) { const k = Object.keys(t).find(k => k.startsWith('__reactProps$')); if (k && t[k].onClick) { t[k].onClick({ preventDefault(){}, stopPropagation(){}, currentTarget: t, target: t, nativeEvent: {} }); break; } t = t.parentElement; }
  await wait(1200);
  const s = vis('input[type=range]')[0];
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(s, s.max);
  s.dispatchEvent(new Event('input', { bubbles: true })); s.dispatchEvent(new Event('change', { bubbles: true })); await wait(600);
  const pop = vis('.MuiPaper-root').filter(e => /Define your backtest/.test(e.innerText)).pop();
  [...pop.querySelectorAll('button')].find(b => b.textContent.trim().toUpperCase() === 'APPLY').click(); await wait(1500);
  const run = vis('button').find(b => b.textContent.trim() === 'Run');
  const rk = Object.keys(run).find(k => k.startsWith('__reactProps$'));
  rk && run[rk].onClick ? run[rk].onClick({ preventDefault(){}, stopPropagation(){}, currentTarget: run, target: run, nativeEvent: {} }) : run.click();
  log.push('run clicked');
  return log;
};
window.__results = () => { const txt = document.body.innerText; const stat = label => ((txt.match(new RegExp(label + '\\n([^\\n]+)')) || [])[1] || null);
  return ({ candles: [...document.querySelectorAll('button')].map(b => b.textContent.trim()).find(x => /candles$/.test(x)), market: stat('Market'), netPerf: stat('Net Perf, all'), assetPerf: stat('Asset Perf.'), beta: stat('Beta \\(vs Asset\\)'), positions: stat('Positions'), wins: stat('Wins'), maxDD: stat('Max DD'), entry: (txt.match(/Entry Conditions:[\s\S]{0,110}/) || [''])[0].replace(/\n/g, ' | ') }); };
window.__remove = async (SHORT) => { const norm = e => e.innerText.replace(/\s+/g, ' ').trim(); const rows = () => [...document.querySelectorAll('.chart-indicators-list__indicator')].filter(e => e.offsetWidth); let n = 0; for (let k = 0; k < 4; k++) { const mine = rows().filter(e => { const t = norm(e); return t === SHORT || t.startsWith(SHORT + ' '); }); if (!mine.length) break; const x = mine[0].querySelector('[title="Remove this indicator from your charts"]'); if (!x) break; x.click(); n++; await new Promise(r => setTimeout(r, 1500)); } return { removed: n }; };
window.__next = async () => { const wait = ms => new Promise(r => setTimeout(r, ms)); const yes = [...document.querySelectorAll('button, div, span')].filter(e => e.offsetWidth && /^yes$/i.test(e.textContent.trim()) && e.children.length === 0); yes.forEach(e => e.click()); await wait(2500); const r = await window.__openTester(); return { yes: yes.length, ...r }; };
window.__cleanup = async (names) => { const wait = ms => new Promise(r => setTimeout(r, ms)); const out = {};
  const yes = [...document.querySelectorAll('button, div, span')].filter(e => e.offsetWidth && /^yes$/i.test(e.textContent.trim()) && e.children.length === 0); yes.forEach(e => e.click()); await wait(2500); out.yes = yes.length;
  out.removed = []; for (const n of names) { const r = await window.__remove(n); out.removed.push(n + ':' + r.removed); }
  out.legend = window.__legend(); return out; };
'tester helpers installed';
