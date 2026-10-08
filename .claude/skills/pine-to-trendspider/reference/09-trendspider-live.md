# 09 — Live test and save in the user's TrendSpider (mandatory for every script)

Every conversion is run, saved under its `_TV` name, and checked in the user's real
TrendSpider account before it is marked done. The lint and the oracle prove the code is
valid; only the live editor proves it **runs, draws and saves** in TrendSpider today.

Procedure verified end to end on 2026-10-08 with `templates/indicator.js`
("Bollinger Bands_TV"): APPLY drew the bands, Save returned HTTP 200, the name appeared in
the "Yours" list, and the chart was returned to its previous state.

## Ground rules

- The user is **already logged in** in Chrome. Use **Claude in Chrome**
  (`mcp__claude-in-chrome__*`; load them with one ToolSearch call). Never type a password or
  log in; if the page shows a login screen, stop and ask the user to log in.
- Saving the converted `_TV` script to the account is authorised by the user's standing
  instruction. **Nothing else** is: never delete, rename or edit any other indicator,
  strategy or workspace. The plan is at its 10-workspace cap — never create or delete one.
- After the test the chart must look as it did before. Remove only the indicator you
  added, identified by **its own legend row** (step 7).
- Prefer DOM-level JavaScript (`javascript_tool`) over coordinate clicks; screenshots at
  `scale: 0.6` for proof.

## Steps

### 0. Prepare (local)
```bash
python tools/lint_trendspider.py converted/<file>.trendspider.js      # must be clean of ERRORs
python tools/ts_live_payload.py apply  converted/<file>.trendspider.js > <scratch>/apply.js
python tools/ts_live_payload.py find   converted/<file>.trendspider.js > <scratch>/find.js
python tools/ts_live_payload.py remove converted/<file>.trendspider.js > <scratch>/remove.js
```
Read each generated file and paste its text into `javascript_exec` unchanged. The script is
embedded as a JSON string, so it arrives byte-for-byte (LESSONS L15).

### 1. Open the chart
`tabs_context_mcp` → `navigate` to `https://charts.trendspider.com/`. If the workspace
chooser appears, `find` "Default Workspace" and click that ref. Set the symbol/timeframe
the script is meant for if it matters (an intraday script on a daily chart proves little).

### 2. Open the Custom Indicator Editor
The tab is a React button — `.click()` is not enough:
```js
// lint: skip — browser-side helper, not a TrendSpider script
const b = [...document.querySelectorAll('button, [role=tab], div, span')]
  .find(e => e.textContent.trim() === 'Custom Indicator Editor' && e.offsetWidth);
let t = b; for (let i = 0; i < 5 && t; i++) {
  const k = Object.keys(t).find(k => k.startsWith('__reactProps$'));
  if (k && t[k].onClick) { t[k].onClick({ preventDefault(){}, stopPropagation(){}, currentTarget: t, target: t }); break; }
  t = t.parentElement;
}
```
Wait ~2.5 s; `document.querySelector('.cm-content')` must exist.

### 3. Is the name already saved?
Run `find.js`. If `saved: true`, this is an **update**: open that saved script from the
"Yours" list first, so Save overwrites it instead of creating a duplicate
[VERIFY the update flow on the first re-save]. Never open or overwrite a script whose name
is not this script's `_TV` name.

### 4. APPLY (runs the script, does not save)
Run `apply.js`. It refuses if the editor holds some other non-example script — then click
**New indicator** and run it again. Pass criteria, from its report:
- `loaded: true` (the editor holds exactly the file);
- `errors` empty and `console` free of errors;
- `previewLegend` shows the script's short name — it drew.

Take a screenshot as proof. If APPLY shows an error, it is a **code** problem: fix the
file, re-lint, add a LESSONS entry if it is a new kind of mistake, and repeat.

### 5. Save
Call `read_network_requests` once **before** clicking (tracking starts on first call),
click **Save**, wait ~2.5 s, then read requests filtered by `custom_scripting`:
- `POST …/custom_scripting_webserver/1/scripts` → **200**: saved.
- **5xx**: TrendSpider's server, not the code (LESSONS L12, `07` §12). Record
  `--ts-saved no --ts-save-error "HTTP 5xx"` and retry in a later session.
- **4xx** with a message: a code or naming problem — read it and fix.

The saved name is the `describe_indicator` title — the `_TV` name.

### 6. Confirm the artefact
Run `find.js` again: `saved: true` with the exact `_TV` name. A 200 alone is not proof
(LESSONS L9).

### 7. Restore the chart
Saving turns the preview into a real chart indicator. Close the bottom panel (`find`
"Close" button of the bottom panel), then run `remove.js`: it removes **only** the legend
row whose text starts with the script's `shortName`, and refuses if it finds zero or
several. Its `before`/`after` lists must differ by exactly that one row.

> Trap seen 2026-10-08: `find("remove button for BB")` returned the remove button of the
> user's **EMA 8** instead. Never click a remove/delete control chosen by search alone —
> match it through its own legend row's text.

### 8. Strategies: a Strategy Tester run
Open **Strategy Tester** (React tab, same click as step 2). Build a new strategy:
- Entry: `Add a condition` → `Condition` → `Indicator` → search the `_TV` indicator →
  its `… Entry` signal → **Signal emerged**.
- Exit: `Add an exit condition…` → **Script** (not "List of signals" — that is raw
  timestamps) → `Add a condition` → `Condition` → `Indicator` → the `… Exit` signal →
  **Signal emerged**. Add the native stop/target only if the header's Tester section says so.
- Backtest range: the "N candles" button → slider to the maximum → its own Apply → **Run**.
- Record trades count and net result: `--tester-run "TICKER:RES trades=N net=X%"`.
- Confirm the selected signal's **indicator prefix** is the `_TV` script — built-ins can
  have signals with the same display name (`07` §13).

Don't save the Tester strategy unless the user asks — it can't be undone cleanly and isn't
part of the conversion. Close the Tester without saving.

### 9. Record
```bash
python tools/progress.py set <id> --ts-name "<Title>_TV" --live-tested TICKER:RES --ts-saved yes \
       [--tester-run "TICKER:RES trades=N"] --status FULL|PARTIAL
```
`progress.py` refuses FULL/PARTIAL unless lint is clean, the `_TV` name matches the
file, the live test is recorded, the save (or the save error) is recorded and, for
strategies, the Tester run is recorded. Then fill the header's `Live tested` line, commit
and push.

## Naming

- `describe_indicator('<Original Title>_TV', …)` — the original TradingView title, then
  `_TV`. Keep it under ~60 characters; trim the title, never the suffix.
- Two scripts with the same title: `'<Title> <id>_TV'` (id from `progress.json`).
- A strategy split by direction: `'<Title> LONG_TV'` and `'<Title> SHORT_TV'`.
- A script split by placement: `'<Title> OVERLAY_TV'` and `'<Title> LOWER_TV'`.
- The same string goes in the header's `TrendSpider name` line and in `progress.json`
  (`--ts-name`). The lint and `progress.py` both enforce this (LESSONS L14).
