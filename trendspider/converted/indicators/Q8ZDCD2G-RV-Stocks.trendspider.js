/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RV Stocks
 * Author       : vijaysolanki06011
 * Source URL   : https://www.tradingview.com/script/Q8ZDCD2G-RV-Stocks
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RV Stocks_TV
 *
 * The Pine original, in words: BUY when the bar's high is above the previous 5 highs, its low below the previous 5
 *   lows, and volume above the highest volume of the previous 75 bars.
 *
 * Deviations from the original: none.
 * Not carried over: background tint on signal bars.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RV Stocks_TV', 'price');

// Volume lookback window, matches Pine's "Volume Lookback" input
const myVolLen = input.number('Volume Lookback', 75, { min: 1, max: 500 });

// highCond: current high is strictly greater than each of the previous 5 highs
const myHighCond = for_every(
	high, shift(high, 1), shift(high, 2), shift(high, 3), shift(high, 4), shift(high, 5),
	(_h0, _h1, _h2, _h3, _h4, _h5) => _h0 > _h1 && _h0 > _h2 && _h0 > _h3 && _h0 > _h4 && _h0 > _h5
);

// lowCond: current low is strictly lower than each of the previous 5 lows
const myLowCond = for_every(
	low, shift(low, 1), shift(low, 2), shift(low, 3), shift(low, 4), shift(low, 5),
	(_l0, _l1, _l2, _l3, _l4, _l5) => _l0 < _l1 && _l0 < _l2 && _l0 < _l3 && _l0 < _l4 && _l0 < _l5
);

// volCond: current volume exceeds the highest volume of the previous volLen candles
// (Pine's ta.highest(volume, volLen)[1] is "highest of last volLen bars, as of 1 bar ago")
const myHighestVolPrev = shift(highest(volume, myVolLen), 1);
const myVolCond = for_every(volume, myHighestVolPrev, (_v, _hv) => _hv !== null && _v > _hv);

// final signal: all three conditions true
const mySignal = for_every(myHighCond, myLowCond, myVolCond, (_h, _l, _v) => _h && _l && _v);

// Shape marker below bar, equivalent to plotshape(location.belowbar, triangleup)
const mySignalMarks = for_every(mySignal, _s => _s ? 'BUY' : null);
paint(mySignalMarks, { name: 'BuySignal', style: 'labels_below', color: 'lime' });

// Background highlight equivalent, using candle coloring as closest analog

// Register signal for use in Scanners, Alerts and Strategy Tester
register_signal(mySignal, 'RV Stocks Signal');
