/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA Convergence (10/20/89 vs EMA200)
 * Author       : Chandok99
 * Source URL   : https://www.tradingview.com/script/HXGhFm0f-EMA-Convergence-10-20-89-vs-EMA200
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA Convergence (10/20/89 vs EMA200)_TV
 *
 * The Pine original, in words: EMA 10/20/89/200; BUY on the first bar where EMA 10, 20 and 89 are within 1 % of
 *   each other and all above EMA 200, SELL when all are below.
 *
 * Deviations from the original: candles tinted instead of the background.
 * Not carried over: alertconditions — use the Buy/Sell signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA Convergence (10/20/89 vs EMA200)_TV', 'price');

// === Inputs ===
const myFastLen = input.number('Fast EMA', 10, { min: 1, max: 500 });
const myMidLen = input.number('Mid EMA', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA', 89, { min: 1, max: 500 });
const myTrendLen = input.number('Trend EMA', 200, { min: 1, max: 500 });
// shortened input title to satisfy the input name length limit
const myConvergenceThreshold = input.number('Max % Spread for Convergence', 1.0, { min: 0.1, max: 100, step: 0.1 });

// === EMA Calculations ===
const myEma10 = ema(close, myFastLen);
const myEma20 = ema(close, myMidLen);
const myEma89 = ema(close, mySlowLen);
const myEma200 = ema(close, myTrendLen);

// === Convergence Condition (shared by both buy & sell) ===
const myHighestEMA = max_of(myEma10, myEma20, myEma89);
const myLowestEMA = min_of(myEma10, myEma20, myEma89);
const mySpreadPct = for_every(myHighestEMA, myLowestEMA, myEma89, (_h, _l, _e89) => _e89 === null || !_l ? null : (_h - _l) / _l * 100);
const myIsConverged = for_every(mySpreadPct, _s => _s !== null && _s <= myConvergenceThreshold);

// === Trend Position Checks ===
const myAllAboveEMA200 = for_every(myEma10, myEma20, myEma89, myEma200, (_e10, _e20, _e89, _e200) => _e200 !== null && _e89 !== null && _e10 > _e200 && _e20 > _e200 && _e89 > _e200);
const myAllBelowEMA200 = for_every(myEma10, myEma20, myEma89, myEma200, (_e10, _e20, _e89, _e200) => _e200 !== null && _e89 !== null && _e10 < _e200 && _e20 < _e200 && _e89 < _e200);

// === Buy / Sell Conditions ===
const myBuyCondition = for_every(myIsConverged, myAllAboveEMA200, (_c, _a) => _c && _a);
const mySellCondition = for_every(myIsConverged, myAllBelowEMA200, (_c, _b) => _c && _b);

// Trigger only on the bar the condition first becomes true
const myBuySignal = for_every(myBuyCondition, (_c, _prev, _i) => _c && !(_i > 0 && myBuyCondition[_i - 1]));
const mySellSignal = for_every(mySellCondition, (_c, _prev, _i) => _c && !(_i > 0 && mySellCondition[_i - 1]));

// === Plotting EMAs ===
paint(myEma10, { name: 'EMA 10', color: '#2962FF', thickness: 1 });
paint(myEma20, { name: 'EMA 20', color: '#FF9800', thickness: 1 });
paint(myEma89, { name: 'EMA 89', color: '#9C27B0', thickness: 1 });
paint(myEma200, { name: 'EMA 200', color: '#F23645', thickness: 2 });

// === Buy / Sell Signal Markers ===
const myBuyMarks = for_every(myBuySignal, low, (_sig, _low) => _sig ? 'BUY' : null);
const mySellMarks = for_every(mySellSignal, high, (_sig, _high) => _sig ? 'SELL' : null);

paint(myBuyMarks, { name: 'BUY', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'SELL', style: 'labels_above', color: 'red', thickness: 3 });

// === Background highlights (approximated via candle coloring) ===
const myBgColors = for_every(myBuyCondition, mySellCondition, (_b, _s) => _b ? 'rgba(0,255,0,0.1)' : (_s ? 'rgba(255,0,0,0.1)' : null));
color_candles(myBgColors);

// === Signals for scanner/alerts/strategy ===
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myBuyCondition, 'Buy Condition');
register_signal(mySellCondition, 'Sell Condition');
