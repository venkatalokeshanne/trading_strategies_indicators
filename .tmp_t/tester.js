const NAME = "55 20 Wilders MACD Trend_TV", ENTRY = "MA2CrossLE Long Entry", EXIT = "MA2CrossSE Short Entry";
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
  const isRow = txt => txt.startsWith(NAME) && txt.endsWith(tail)
    && /^( \(.*\))?$/.test(txt.slice(NAME.length, txt.length - tail.length));
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
log.push('run clicked — now wait ~15 s and run: ts_live_payload.py results');
log;