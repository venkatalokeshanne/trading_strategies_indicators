# 03 — Time, sessions and inputs

Three numbering differences in this file produce code that runs perfectly and is wrong.

## Time units

| | Pine | TrendSpider |
|---|---|---|
| `time` | Unix **milliseconds** | Unix **seconds** [VERIFIED] |
| Any timestamp maths | ms | s |

Every literal in a Pine time calculation needs dividing by 1000 — `86400000` (a day in ms)
becomes `86400`. Watch for `time - time[1]` used to infer the bar duration, and for
`timestamp(2024, 1, 1)` literals, which return milliseconds.

## Calendar fields

TrendSpider: `time_of(timestamp)` → `{minutes, hours, dayOfWeek, dayOfMonth, dayOfYear,
weekOfYear, quarter, month, year}`, in the **exchange's timezone**. [VERIFIED]

| Pine | TrendSpider | Trap |
|---|---|---|
| `hour`, `minute` | `time_of(time[i]).hours`, `.minutes` | |
| `second` | not provided — derive from `time[i] % 60` | |
| `dayofmonth`, `year`, `weekofyear` | `.dayOfMonth`, `.year`, `.weekOfYear` | |
| **`dayofweek`** | `.dayOfWeek` | **Pine: 1 = Sunday … 7 = Saturday. TrendSpider: 1 = Monday … 7 = Sunday.** Convert with `pineDow = (tsDow % 7) + 1` |
| `dayofweek.monday` etc. | compare against the converted value, or use TrendSpider numbering consistently | never mix the two numberings in one script |
| **`month`** | `.month` | **Pine 1–12. TrendSpider 0–11.** Convert with `pineMonth = tsMonth + 1` |
| `hour(time, "UTC")` (explicit timezone) | `library('moment-timezone')` [VERIFIED whitelisted] | `time_of` is always exchange time |

## Bar time

| Pine | TrendSpider |
|---|---|
| `time` | `time[i]` (seconds) |
| `time_close` | `time[i] + barSeconds` — see `resolutionSeconds()` in `helpers.js` |
| `timenow` | **No equivalent.** The script has no wall clock; logic comparing bars to "now" must be rewritten against the last bar's time, or listed as a deviation |
| `last_bar_time` | `time[time.length - 1]` |

## Sessions

Pine session strings: `"0930-1600"`, with optional day filter `"0930-1600:23456"` (digits
are **Pine** days: 1 = Sunday, 2 = Monday, …), and overnight sessions such as `"1800-0930"`.
`time(timeframe.period, "0930-1600")` returns `na` outside the session.

Re-implement with minutes-of-day in exchange time:

```js
// "HHMM-HHMM[:days]" -> (i) => boolean.  Handles overnight wrap and Pine day digits.
const sessionFilter = spec => {
    const [range, days] = spec.split(':');
    const [a, b] = range.split('-');
    const start = +a.slice(0, 2) * 60 + +a.slice(2);
    const end   = +b.slice(0, 2) * 60 + +b.slice(2);
    // Pine day digits (1 = Sunday). An array, not a Set: `new` is banned in the sandbox.
    const allowed = days ? days.split('').map(Number) : null;
    return i => {
        const t = time_of(time[i]);
        const m = t.hours * 60 + t.minutes;
        const inRange = start <= end ? (m >= start && m < end) : (m >= start || m < end);
        if (!inRange) return false;
        if (!allowed) return true;
        return allowed.includes((t.dayOfWeek % 7) + 1);                // to Pine numbering
    };
};
```

Pine's session end is exclusive (`m < end`): a "0930-1600" session does not include a bar
stamped 16:00. [VERIFY on a 1-minute chart if the script's logic hinges on the last bar.]

Overnight sessions: a bar at 23:00 and one at 02:00 belong to the same session but fall on
different calendar days. Do not detect "new session" by a change of date for those — use
`bar_at(timestamp).sessionStartsAt` [VERIFIED to exist], or the session start minute.

| Pine | TrendSpider |
|---|---|
| `session.isfirstbar` | first bar where the session filter turns true, or a change in `sessionStartsAt` |
| `session.islastbar` | next bar starts a new session, or is the last bar |
| `session.ismarket` / `ispremarket` / `ispostmarket` | session filter against `current.session` / `current.ext_session_premarket` / `ext_session_postmarket` [VERIFIED names] |
| `ta.change(time("D"))` (new day) | date change for regular sessions; `sessionStartsAt` for overnight ones |

Whether extended-hours bars are present depends on the chart. `current.is_ext_hours` tells
you. [VERIFIED] A Pine script that assumes RTH-only data can produce different VWAPs and
opening ranges on an extended-hours TrendSpider chart — note it.

## Timeframe

| Pine | TrendSpider |
|---|---|
| `timeframe.period` | `current.resolution` — values such as `"15"`, `"60"`, `"D"` [VERIFIED]; `"W"`, `"M"` [VERIFY] |
| `timeframe.multiplier` | parse `current.resolution` |
| `timeframe.isintraday` / `isdaily` / `isweekly` / `ismonthly` | test `current.resolution` |
| `timeframe.in_seconds()` | `resolutionSeconds()` in `helpers.js` [VERIFY for W/M] |

## Symbol information

| Pine | TrendSpider |
|---|---|
| `syminfo.ticker`, `syminfo.tickerid` | `current.ticker` / `current.symbol` [VERIFIED] — format differs from TradingView's `"EXCHANGE:TICKER"` |
| `syminfo.type` | `current.assetType` [VERIFIED] |
| `syminfo.session`, `syminfo.timezone` | `current.session` → `{timezone, start, end, lengthMinutes, marketDays}` [VERIFIED] |
| `syminfo.mintick` | **[VERIFY]** no confirmed equivalent. Infer from price precision, or expose it as an input with a sensible default, and list it as a deviation |
| `syminfo.pointvalue`, `currency`, `basecurrency` | not confirmed — list as a deviation if used in calculations |

## Inputs

[VERIFIED]: `input.number(title, default, {min, max})`, `input.select(title, default,
options)`, `input.boolean`, `input.text`, `input.symbol`, `input.color`,
`input.anchor(defaultValue, defaultWindowSize)`, and the generic `input(title, default, options)`.

| Pine | TrendSpider | Notes |
|---|---|---|
| `input.int`, `input.float` | `input.number(title, default, {min, max})` | `step`, `tooltip`, `group`, `inline`, `confirm` have no confirmed equivalent — drop them [VERIFY] |
| `input.bool` | `input.boolean(title, default)` | |
| `input.string(..., options=[...])` | `input.select(title, default, options)` | |
| `input.string` (free text), `input.text_area` | `input.text(title, default)` | |
| `input.enum` (v6) | `input.select` with the enum's labels | |
| `input.source` | `input.select(title, 'close', constants.price_source_options)`, then `market[choice]` | [VERIFY the exact option values] |
| `input.timeframe` | `input.select(title, default, constants.time_frames)` | [VERIFY value format] |
| `input.symbol` | `input.symbol` | |
| `input.color` | `input.color` | |
| `input.session` | `input.text` holding `"0930-1600"` + `sessionFilter` | |
| `input.time`, `input.price` (interactive picks) | `input.anchor`, or a number input | semantics differ — list as a deviation |

Rules:
- Keep **input titles short** — an undocumented cap rejects long titles at run time
  (`input(): name is too lengthy`; a 35-character title failed). Stay under ~20 characters. [VERIFIED]
- **Preserve every Pine default value exactly.** Changed defaults change results silently.
- The input name **`offset`** (and `'<lineName>__offset'`) is reserved: it shifts painted
  lines by that many bars at the engine level. [VERIFIED] Use it to reproduce Pine's
  `plot(..., offset=n)`; don't use the name for anything else.
- Declare inputs unconditionally at the top of the script, in a fixed order. [VERIFY that
  conditional inputs break; assume they do]
