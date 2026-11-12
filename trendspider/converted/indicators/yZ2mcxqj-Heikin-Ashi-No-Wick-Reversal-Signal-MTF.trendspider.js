/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Heikin Ashi No Wick Reversal Signal MTF
 * Author       : smino2
 * Source URL   : https://www.tradingview.com/script/yZ2mcxqj-Heikin-Ashi-No-Wick-Reversal-Signal-MTF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Heikin Ashi No Wick Reversal Signal MTF_TV
 *
 * The Pine original, in words: Heikin Ashi no-wick reversal (see TYFu4gzk) computed on a chosen signal timeframe
 *   and shown on the chart.
 *
 * Deviations from the original: no look-ahead: a signal-timeframe signal appears at the start of the next
 *   signal-timeframe bar (Pine: on that bar's last chart bar, one chart bar earlier).
 *   Heikin Ashi computed from the timeframe's normal candles.
 * Not carried over: alertconditions — use the signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Heikin Ashi No Wick Reversal Signal MTF_TV', 'price');

const mySignalTF = input.select('Signal Timeframe', '5', ['1', '3', '5', '15', '30', '60', '240', 'D']);
const myH = await request.history(current.ticker, mySignalTF);
assert(!myH.error, 'Error fetching ' + mySignalTF + ' data: ' + myH.error);

// Heikin Ashi candles of the signal timeframe (as ticker.heikinashi).
const n = myH.close.length;
const haC = myH.close.map((c, i) => (myH.open[i] + myH.high[i] + myH.low[i] + c) / 4);
const haO = [], haH = [], haL = [];
for (let i = 0; i < n; i++) {
    haO[i] = i === 0 ? (myH.open[0] + myH.close[0]) / 2 : (haO[i - 1] + haC[i - 1]) / 2;
    haH[i] = Math.max(myH.high[i], haO[i], haC[i]);
    haL[i] = Math.min(myH.low[i], haO[i], haC[i]);
}
const myLong = [], myShort = [];
let waitBull = false, waitBear = false;
for (let i = 0; i < n; i++) {
    const bull = haC[i] > haO[i], bear = haC[i] < haO[i];
    const pBull = i > 0 && haC[i - 1] > haO[i - 1], pBear = i > 0 && haC[i - 1] < haO[i - 1];
    if (bull && pBear) { waitBull = true; waitBear = false; }
    if (bear && pBull) { waitBear = true; waitBull = false; }
    const lg = waitBull && bull && haL[i] === haO[i];
    const sh = waitBear && bear && haH[i] === haO[i];
    if (lg) waitBull = false;
    if (sh) waitBear = false;
    myLong[i] = lg; myShort[i] = sh;
}
// No look-ahead: a signal-timeframe bar is only known at its close, so show it at the start of
// the NEXT signal-timeframe bar (the Pine shows it on that bar's last chart bar).
const myNextTimes = myH.time.slice(1);
const myLongLanded = land_points_onto_series(myNextTimes, myLong.slice(0, n - 1), time, 'le');
const myShortLanded = land_points_onto_series(myNextTimes, myShort.slice(0, n - 1), time, 'le');
const myLongSig = myLongLanded.map(v => v === true);
const myShortSig = myShortLanded.map(v => v === true);
paint(myLongSig.map(v => v ? 'LONG' : null), { name: 'Long label', style: 'labels_below', color: 'green' });
paint(myShortSig.map(v => v ? 'SHORT' : null), { name: 'Short label', style: 'labels_above', color: 'red' });
register_signal(myLongSig, 'HA Long No Wick MTF');
register_signal(myShortSig, 'HA Short No Wick MTF');
