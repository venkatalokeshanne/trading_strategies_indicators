/*
 * ── Original indicator (not a conversion) ──────────────────────────────
 * Name         : INFQ Day Guide_TV
 * Built for    : INFQ (Infleqtion), 5-minute or 15-minute chart, regular hours
 * Placement    : overlay
 * Built        : 2026-10-10 by Claude, from research on all INFQ 5m/15m bars since
 *                listing (2026-02-17 → 2026-10-09, Twelve Data), split train/test at 2026-07-16.
 *
 * What the research found (72 candidate signals × 3 holding periods, net of 0.15% cost):
 *  • INFQ does NOT follow through. Breakouts, EMA/MACD crosses, squeeze releases, volume surges,
 *    new highs and "sector is ripping" entries all lost money in one or both periods.
 *  • What works is fading a REJECTED extreme: a bar that makes the high of day and is pushed
 *    back (long upper wick, or a red bar closing under the prior bar's low). Short from the next
 *    open, stop just above the high, hold to the close → profit factor ~2 in both periods.
 *  • Buying is harder. The mirror long (rejection at the low of day) was unstable — good in one
 *    period, bad in the other, bad on 15m — so it is OFF by default (input "Buy at rejected lows").
 *    The buy that held up: on a WIDE day (opening range 09:30–10:00 at least half of the 10-day
 *    average daily range), fade the first close BELOW the range (stop half a range lower, target
 *    the range high). Same on the short side above the range.
 *  • Backtest of exactly these rules, 5m (train || test): PF 1.37 || 1.73, avg +0.39% || +0.47%
 *    per trade, ~40–48% winners; 15m: PF 1.15 || 1.80.
 *
 * How to read it: the panel tells you the day type, whether there is a setup NOW, and while a
 * trade is open: its stop and where it ends (stop, target, or the 15:55 close). Signals print on
 * the bar close; the trade is assumed to start at the next bar's open.
 * This is analysis from past bars, not advice — the edge is small, losses are frequent
 * (roughly half the short setups lose), and it can stop working.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('INFQ Day Guide_TV', 'price');

const UPC = '#22C55E', DNC = '#EF4444', MUTE = '#94A3B8', INK = '#F1F5F9', GOLD = '#F59E0B', BLUE = '#38BDF8';

const tS = input.tab('Setups');
const myShorts = tS.boolean('Short at rejected highs', true);
const myLongs = tS.boolean('Buy at rejected lows (wide days)', false);
const myOrFade = tS.boolean('Fade range break (wide days)', true);
const myWideCut = tS.number('Wide day: range vs ADR', 0.5, { min: 0.2, max: 1.5, step: 0.05 });
const myStopPct = tS.number('Rejection stop beyond bar (%)', 0.3, { min: 0, max: 3, step: 0.1 });
const myMaxDay = tS.number('Max setups per day', 2, { min: 1, max: 5 });
const tV = input.tab('Visuals');
const myShowBands = tV.boolean('VWAP and 2-sigma bands', true);
const myShowRange = tV.boolean('Opening range lines', true);
const myShowPanel = tV.boolean('Guide panel', true);

const myN = close.length;
const myFmt = _v => (_v === null || !isFinite(_v)) ? '—' : _v.toFixed(2);

// ── per-bar session facts (exchange time)
const myVwap = series_of(null), myUpB = series_of(null), myLoB = series_of(null);
const myOrH = series_of(null), myOrL = series_of(null), myOrM = series_of(null);
const myShort = series_of(false), myBuy = series_of(false), myExit = series_of(false), myWide = series_of(false);
const myStopLine = series_of(null), myShortLbl = series_of(null), myBuyLbl = series_of(null), myExitLbl = series_of(null);
const mySide = series_of(0);

const dayRanges = [];
let dayKey = null, dHi = null, dLo = null, hod = null, lod = null;
let pv = 0, vv = 0, pv2 = 0, orH = null, orL = null, orDone = false, adr = null, wide = false;
let cnt = 0, orFaded = false;
let side = 0, stop = null, tgt = null, entryPx = null, pending = 0, pStop = null, pTgt = null;
let lastBarOfDay = false;

for (let i = 0; i < myN; i++) {
    const t = time_of(time[i]);
    const mod = t.hours * 60 + t.minutes;
    if (mod < 570 || mod >= 960) continue;                    // regular hours only
    const key = t.year * 1000 + t.dayOfYear;
    if (key !== dayKey) {                                     // new session
        if (dayKey !== null && dHi !== null) dayRanges.push(dHi - dLo);
        const last10 = dayRanges.slice(-10);
        adr = last10.length >= 5 ? last10.reduce((a, b) => a + b, 0) / last10.length : null;
        dayKey = key; dHi = high[i]; dLo = low[i]; hod = null; lod = null;
        pv = 0; vv = 0; pv2 = 0; orH = null; orL = null; orDone = false; wide = false;
        cnt = 0; orFaded = false; side = 0; stop = null; tgt = null; pending = 0;
    }
    const prevHod = hod, prevLod = lod;
    dHi = Math.max(dHi, high[i]); dLo = Math.min(dLo, low[i]);
    hod = hod === null ? high[i] : Math.max(hod, high[i]);
    lod = lod === null ? low[i] : Math.min(lod, low[i]);

    // session VWAP (hlc3) and volume-weighted standard deviation
    const tp = (high[i] + low[i] + close[i]) / 3, vol = Math.max(volume[i] || 0, 0);
    pv += tp * vol; vv += vol; pv2 += tp * tp * vol;
    const vw = vv > 0 ? pv / vv : tp;
    const sd = vv > 0 ? Math.sqrt(Math.max(pv2 / vv - vw * vw, 0)) : 0;
    myVwap[i] = vw; myUpB[i] = vw + 2 * sd; myLoB[i] = vw - 2 * sd;

    // opening range 09:30–10:00, known from the first bar at/after 10:00
    if (mod < 600) {
        orH = orH === null ? high[i] : Math.max(orH, high[i]);
        orL = orL === null ? low[i] : Math.min(orL, low[i]);
    } else if (!orDone && orH !== null) {
        orDone = true;
        wide = adr !== null && (orH - orL) >= myWideCut * adr;
    }
    if (orDone) { myOrH[i] = orH; myOrL[i] = orL; myOrM[i] = (orH + orL) / 2; myWide[i] = wide; }

    // a pending entry fills at this bar's open
    if (pending !== 0) { side = pending; stop = pStop; tgt = pTgt; entryPx = open[i]; pending = 0; }

    // manage an open trade (stop first, then target, then the last bar of the day)
    const nextT = i + 1 < myN ? time_of(time[i + 1]) : null;
    lastBarOfDay = nextT === null || (nextT.year * 1000 + nextT.dayOfYear) !== key || (nextT.hours * 60 + nextT.minutes) >= 960;
    if (side !== 0) {
        let why = null;
        if (side === -1 && high[i] >= stop) why = 'EXIT stop';
        else if (side === 1 && low[i] <= stop) why = 'EXIT stop';
        else if (tgt !== null && side === -1 && low[i] <= tgt) why = 'EXIT target';
        else if (tgt !== null && side === 1 && high[i] >= tgt) why = 'EXIT target';
        else if (lastBarOfDay) why = 'EXIT close';
        myStopLine[i] = stop; mySide[i] = side;
        if (why) { myExit[i] = true; myExitLbl[i] = why; side = 0; stop = null; tgt = null; }
    }

    // setups: only when flat, 10:00–15:00, within the daily cap, next bar in the same session
    if (side === 0 && pending === 0 && orDone && mod <= 900 && cnt < myMaxDay && !lastBarOfDay && i > 0) {
        const rg = high[i] - low[i];
        const upW = high[i] - Math.max(open[i], close[i]), loW = Math.min(open[i], close[i]) - low[i];
        const sameDay = time_of(time[i - 1]).dayOfYear === t.dayOfYear;
        const atHigh = prevHod !== null && high[i] >= prevHod;
        const atLow = prevLod !== null && low[i] <= prevLod;
        const rejTop = atHigh && rg > 0 && (upW / rg >= 0.5 || (close[i] < open[i] && sameDay && close[i] < low[i - 1]));
        const rejBot = atLow && rg > 0 && (loW / rg >= 0.5 || (close[i] > open[i] && sameDay && close[i] > high[i - 1]));
        const w = orH - orL;
        const brkUp = !orFaded && mod <= 870 && close[i] > orH, brkDn = !orFaded && mod <= 870 && close[i] < orL;
        if (brkUp || brkDn) orFaded = true;                    // only the FIRST close outside counts
        if (myShorts && rejTop) {
            pending = -1; pStop = high[i] * (1 + myStopPct / 100); pTgt = null;
            myShortLbl[i] = 'SHORT · stop ' + myFmt(pStop); myShort[i] = true; cnt++;
        } else if (myLongs && wide && rejBot) {
            pending = 1; pStop = low[i] * (1 - myStopPct / 100); pTgt = null;
            myBuyLbl[i] = 'BUY · stop ' + myFmt(pStop); myBuy[i] = true; cnt++;
        } else if (myOrFade && wide && brkUp) {
            pending = -1; pStop = orH + 0.5 * w; pTgt = orL;
            myShortLbl[i] = 'SHORT fade · stop ' + myFmt(pStop) + ' · tgt ' + myFmt(pTgt); myShort[i] = true; cnt++;
        } else if (myOrFade && wide && brkDn) {
            pending = 1; pStop = orL - 0.5 * w; pTgt = orH;
            myBuyLbl[i] = 'BUY fade · stop ' + myFmt(pStop) + ' · tgt ' + myFmt(pTgt); myBuy[i] = true; cnt++;
        }
    }
}

// ── drawing
paint(myShowBands ? myVwap : series_of(null), { name: 'VWAP line', color: GOLD, thickness: 2 });
paint(myShowBands ? myUpB : series_of(null), { name: 'Upper band', color: 'rgba(239,68,68,0.55)', thickness: 1 });
paint(myShowBands ? myLoB : series_of(null), { name: 'Lower band', color: 'rgba(34,197,94,0.55)', thickness: 1 });
const myWideCol = myWide.map(wd => wd ? BLUE : MUTE);
paint(myShowRange ? myOrH : series_of(null), { name: 'Range high', color: myWideCol, thickness: 1 });
paint(myShowRange ? myOrL : series_of(null), { name: 'Range low', color: myWideCol, thickness: 1 });
paint(myShowRange ? myOrM : series_of(null), { name: 'Range middle', color: 'rgba(148,163,184,0.5)', thickness: 1 });
paint(myStopLine, { name: 'Trade stop', color: mySide.map(s => s === -1 ? DNC : UPC), thickness: 2 });
paint(myShortLbl, { name: 'Short labels', style: 'labels_above', color: DNC });
paint(myBuyLbl, { name: 'Buy labels', style: 'labels_below', color: UPC });
paint(myExitLbl, { name: 'Exit labels', style: 'labels_below', color: MUTE });

// ── guide panel (state at the last bar)
const L = myN - 1;
let lastSig = -1;
for (let i = L; i >= 0 && lastSig < 0; i--) if (myShort[i] || myBuy[i]) lastSig = i;
const inTrade = mySide[L] !== 0 && !myExit[L];
const fresh = myShort[L] || myBuy[L];
const tL = time_of(time[L]); const modL = tL.hours * 60 + tL.minutes;
const stretchedUp = myUpB[L] !== null && close[L] > myUpB[L];
const stretchedDn = myLoB[L] !== null && close[L] < myLoB[L];
let nowTx, nowCol;
if (fresh) { nowTx = myShort[L] ? 'SHORT setup on this bar — entry next open' : 'BUY setup on this bar — entry next open'; nowCol = myShort[L] ? DNC : UPC; }
else if (inTrade) { nowTx = (mySide[L] === -1 ? 'IN SHORT' : 'IN LONG') + ' · stop ' + myFmt(myStopLine[L]) + ' · out by 15:55'; nowCol = mySide[L] === -1 ? DNC : UPC; }
else if (modL < 600) { nowTx = 'WAIT — opening range still forming (till 10:00)'; nowCol = MUTE; }
else if (modL > 900) { nowTx = 'No new setups after 15:00'; nowCol = MUTE; }
else if (stretchedUp) { nowTx = 'Do NOT chase — stretched above VWAP + 2σ'; nowCol = GOLD; }
else if (stretchedDn) { nowTx = 'Do NOT short here — stretched below VWAP − 2σ'; nowCol = GOLD; }
else { nowTx = 'WAIT — no setup'; nowCol = MUTE; }
const dayTx = myOrH[L] === null ? 'Day type at 10:00' : myWide[L] ? 'WIDE day — fades work both ways' : 'NORMAL day — shorts at rejected highs only';
paint_overlay('INFQ guide panel', { position: 'top_right' }, {
    rows: myShowPanel ? [
        { cells: [{ text: 'INFQ Day Guide', color: INK }, { text: myFmt(close[L]), color: INK }] },
        { cells: [{ text: 'Now', color: MUTE }, { text: nowTx, color: nowCol }] },
        { cells: [{ text: 'Day', color: MUTE }, { text: dayTx, color: myWide[L] ? BLUE : MUTE }] },
        { cells: [{ text: 'VWAP · bands', color: MUTE }, { text: myFmt(myVwap[L]) + ' · ' + myFmt(myLoB[L]) + ' – ' + myFmt(myUpB[L]), color: INK }] },
        { cells: [{ text: 'Range hi · lo', color: MUTE }, { text: myFmt(myOrH[L]) + ' · ' + myFmt(myOrL[L]), color: INK }] },
        { cells: [{ text: 'Rule of thumb', color: MUTE }, { text: 'never buy a new high · sell the push that fails', color: MUTE }] }
    ] : []
});

// ── signals for alerts and scanners
register_signal(myShort, 'Short setup');
register_signal(myBuy, 'Buy setup');
register_signal(myExit, 'Exit trade');
register_signal(myWide, 'Wide day');
