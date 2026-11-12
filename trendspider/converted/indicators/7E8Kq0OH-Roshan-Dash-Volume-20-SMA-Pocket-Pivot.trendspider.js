/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Volume + 20 SMA + Pocket Pivot
 * Author       : realRoshanDash
 * Source URL   : https://www.tradingview.com/script/7E8Kq0OH-Roshan-Dash-Volume-20-SMA-Pocket-Pivot
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Volume + 20 SMA + Pocket Pivot_TV
 *
 * The Pine original, in words: volume columns (teal up day, red down day), SMA 20 of volume, and a pocket pivot
 *   marker: an up day whose volume beats the highest down-day volume of the previous 10
 *   bars.
 *
 * Deviations from the original: input titles shortened (TrendSpider limit).
 * Not carried over: the marker on the price chart (a TrendSpider indicator draws in one pane only);
 *   alertcondition — use the Pocket Pivot Signal.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Volume + 20 SMA + Pocket Pivot_TV', 'lower');

// ---------- Inputs ----------
const myMaLen = input.number('Volume SMA length', 20, { min: 1, max: 500 });
const myPpLookback = input.number('Pocket pivot lookback', 10, { min: 1, max: 200 });
const myCompareAll = input.boolean('Compare vs ALL days', false);
const myUsePriceMA = input.boolean('Require close > SMA10', false);

// ---------- Volume + moving average ----------
const myVolSma = sma(volume, myMaLen);
const myPrevClose = shift(close, 1);
const myUpDay = for_every(close, myPrevClose, (_c, _pc) => _pc !== null && _c > _pc);

// ---------- Pocket pivot logic ----------
// Volume counted only on down days (0 on up days)
const myDownDayVol = for_every(close, myPrevClose, volume, (_c, _pc, _v) => _c < _pc ? _v : 0);

// Highest down-day volume over the PRIOR lookback bars (today excluded)
const myMaxDownVol = highest(shift(myDownDayVol, 1), myPpLookback);

// Highest volume of ALL prior lookback bars (up + down days)
const myMaxAllVol = highest(shift(volume, 1), myPpLookback);

// Threshold: classic PP compares vs down days only; toggle to compare vs every day
const myVolThresh = myCompareAll ? myMaxAllVol : myMaxDownVol;

// Optional trend filter (part of the classic Morales/Kacher definition)
const mySma10 = sma(close, 10);
const myPriceOk = for_every(close, mySma10, (_c, _s) => !myUsePriceMA || _c > _s);

const myPocketPivot = for_every(myUpDay, volume, myVolThresh, myPriceOk, (_up, _v, _thresh, _ok) => _thresh !== null && _up && _v > _thresh && _ok);

// ---------- Plots ----------
const myVolumeColor = for_every(myUpDay, _up => _up ? 'teal' : 'red');
paint(volume, { name: 'Volume', style: 'column', color: myVolumeColor });
paint(myVolSma, { name: 'Volume 20 SMA', color: 'orange', thickness: 2 });

// Marker just above the volume bar on pocket pivot days
const myPpVolumeMarker = for_every(myPocketPivot, volume, (_pp, _v) => _pp ? constants.icons.triangle_down : null);
paint(myPpVolumeMarker, { name: 'Pocket Pivot Marker', style: 'labels_above', color: 'yellow' });

// Optional marker on the main price chart (triangle under the PP day's candle)

// ---------- Signal for scanners, alerts, strategies ----------
register_signal(myPocketPivot, 'Pocket Pivot Signal');
