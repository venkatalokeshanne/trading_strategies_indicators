/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Moving Averages
 * Author       : alecnia
 * Source URL   : https://www.tradingview.com/script/hzrHWs86-Multi-EMA-SMA-2-EMA-4-SMA
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Multi EMA & SMA (2 EMA, 4 SMA)_TV
 *
 * The Pine original, in words: EMA 8 and 21, SMA 50, 100, 150 and 200 of the close.
 *
 * Deviations from the original: TrendSpider name uses the listing title (the Pine title 'Moving Averages' is
 *   generic); cross/position signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Multi EMA & SMA (2 EMA, 4 SMA)_TV', 'price');

// ─── Inputs (mirrors the Pine Script inputs) ───
const myEmaRow1 = input.row();
const myLenEma1 = myEmaRow1.number('EMA 1 Length', 8, { min: 1, max: 500 });
const myLenEma2 = myEmaRow1.number('EMA 2 Length', 21, { min: 1, max: 500 });

const mySmaRow1 = input.row();
const myLenSma1 = mySmaRow1.number('SMA 1 Length', 50, { min: 1, max: 1000 });
const myLenSma2 = mySmaRow1.number('SMA 2 Length', 100, { min: 1, max: 1000 });

const mySmaRow2 = input.row();
const myLenSma3 = mySmaRow2.number('SMA 3 Length', 150, { min: 1, max: 1000 });
const myLenSma4 = mySmaRow2.number('SMA 4 Length', 200, { min: 1, max: 1000 });

// --- Calculations (same math as ta.ema / ta.sma) ---
const myEma1 = ema(close, myLenEma1);
const myEma2 = ema(close, myLenEma2);

const mySma1 = sma(close, myLenSma1);
const mySma2 = sma(close, myLenSma2);
const mySma3 = sma(close, myLenSma3);
const mySma4 = sma(close, myLenSma4);

// --- Plotting (same lines as original Pine plots) ---
paint(myEma1, { name: 'EMA 8', color: 'gray', thickness: 1 });
paint(myEma2, { name: 'EMA 21', color: 'blue', thickness: 1 });

paint(mySma1, { name: 'SMA 50', color: 'white', thickness: 1 });
paint(mySma2, { name: 'SMA 100', color: 'red', thickness: 1 });
paint(mySma3, { name: 'SMA 150', color: 'aqua', thickness: 1 });
paint(mySma4, { name: 'SMA 200', color: 'purple', thickness: 1 });

// --- Scanning / Strategy signals ---
// Golden/Death cross style signals between the two EMAs and
// between the fast/slow SMA groups, usable in Scanners/Alerts/Strategies.
const myEmaBullCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _i) => _i > 0 && _e2 !== null && myEma2[_i - 1] !== null && _e1 > _e2 && myEma1[_i - 1] <= myEma2[_i - 1]);
const myEmaBearCross = for_every(myEma1, myEma2, (_e1, _e2, _prev, _i) => _i > 0 && _e2 !== null && myEma2[_i - 1] !== null && _e1 < _e2 && myEma1[_i - 1] >= myEma2[_i - 1]);

const mySmaBullCross = for_every(mySma1, mySma2, (_s1, _s2, _prev, _i) => _i > 0 && _s2 !== null && mySma2[_i - 1] !== null && _s1 > _s2 && mySma1[_i - 1] <= mySma2[_i - 1]);
const mySmaBearCross = for_every(mySma1, mySma2, (_s1, _s2, _prev, _i) => _i > 0 && _s2 !== null && mySma2[_i - 1] !== null && _s1 < _s2 && mySma1[_i - 1] >= mySma2[_i - 1]);

const myPriceAboveAllMAs = for_every(close, myEma1, myEma2, mySma1, (_c, _e1, _e2, _s1, _prev, _i) => mySma4[_i] !== null && _c > _e1 && _c > _e2 && _c > _s1 && _c > mySma2[_i] && _c > mySma3[_i] && _c > mySma4[_i]);
const myPriceBelowAllMAs = for_every(close, myEma1, myEma2, mySma1, (_c, _e1, _e2, _s1, _prev, _i) => mySma4[_i] !== null && _c < _e1 && _c < _e2 && _c < _s1 && _c < mySma2[_i] && _c < mySma3[_i] && _c < mySma4[_i]);

register_signal(myEmaBullCross, 'EMA Bullish Cross');
register_signal(myEmaBearCross, 'EMA Bearish Cross');
register_signal(mySmaBullCross, 'SMA Bullish Cross');
register_signal(mySmaBearCross, 'SMA Bearish Cross');
register_signal(myPriceAboveAllMAs, 'Price Above All MAs');
register_signal(myPriceBelowAllMAs, 'Price Below All MAs');
