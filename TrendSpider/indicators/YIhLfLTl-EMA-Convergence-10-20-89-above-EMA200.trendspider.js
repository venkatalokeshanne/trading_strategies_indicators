/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA Convergence (10/20/89 above EMA200)
 * Author       : Chandok99
 * Source URL   : https://www.tradingview.com/script/YIhLfLTl-EMA-Convergence-10-20-89-above-EMA200
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA Convergence (10/20/89 above EMA200)_TV
 *
 * The Pine original, in words: EMA 10/20/89/200; BUY on the first bar where EMA 10, 20 and 89 are within 1 % of
 *   each other and all above EMA 200.
 *
 * Deviations from the original: candles tinted instead of the background.
 * Not carried over: alertcondition — use the Buy Signal.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA Convergence (10/20/89 above EMA200)_TV', 'price');

// === Inputs ===
const myEma1Len = input.number('Fast EMA', 10, { min: 1, max: 500 });
const myEma2Len = input.number('Mid EMA', 20, { min: 1, max: 500 });
const myEma3Len = input.number('Slow EMA', 89, { min: 1, max: 500 });
const myEma4Len = input.number('Trend EMA', 200, { min: 1, max: 500 });
// shortened input name to satisfy the platform's name length limit
const myConvergenceThreshold = input.number('Max % Spread for Convergence', 1.0, { min: 0.1, max: 100, step: 0.1 });

// === EMA Calculations ===
const myEma10 = ema(close, myEma1Len);
const myEma20 = ema(close, myEma2Len);
const myEma89 = ema(close, myEma3Len);
const myEma200 = ema(close, myEma4Len);

// === Convergence Condition ===
// highest/lowest of the 3 fast EMAs, per candle
const myHighestEma = for_every(myEma10, myEma20, myEma89, (_e10, _e20, _e89) => Math.max(_e10, _e20, _e89));
const myLowestEma = for_every(myEma10, myEma20, myEma89, (_e10, _e20, _e89) => Math.min(_e10, _e20, _e89));
const mySpreadPct = for_every(myHighestEma, myLowestEma, (_hi, _lo) => _lo ? (_hi - _lo) / _lo * 100 : null);
const myIsConverged = for_every(mySpreadPct, _spread => _spread !== null && _spread <= myConvergenceThreshold);

// === All 3 EMAs above EMA200 ===
const myAllAboveEma200 = for_every(myEma10, myEma20, myEma89, myEma200, (_e10, _e20, _e89, _e200) => _e200 !== null && _e89 !== null && _e10 > _e200 && _e20 > _e200 && _e89 > _e200);

// === Buy Condition ===
const myBuyCondition = for_every(myIsConverged, myAllAboveEma200, (_conv, _above) => _conv && _above);

// Trigger only on the bar the condition first becomes true (edge detection,
// equivalent to Pine's "buyCondition and not buyCondition[1]")
const myBuySignal = for_every(myBuyCondition, (_cond, _prev, _idx) => {
	if (_idx === 0) return false;
	return _cond && !myBuyCondition[_idx - 1];
});

// === Plotting EMAs ===
paint(myEma10, { name: 'EMA 10', color: '#2962FF', thickness: 1 });
paint(myEma20, { name: 'EMA 20', color: '#FF9800', thickness: 1 });
paint(myEma89, { name: 'EMA 89', color: '#9C27B0', thickness: 1 });
paint(myEma200, { name: 'EMA 200', color: '#F44336', thickness: 2 });

// === Buy Signal Marker ===
const myBuyMarks = for_every(myBuySignal, _signal => _signal ? constants.icons.triangle_up : null);
paint(myBuyMarks, { name: 'Buy Marker', style: 'labels_below', color: 'green' });

// === Background highlight when converged and bullish aligned ===
const myBgColors = for_every(myBuyCondition, _cond => _cond ? 'rgba(0,128,0,0.1)' : null);
color_candles(myBgColors);

// === Signals for scanning/alerting ===
register_signal(myBuySignal, 'Buy Signal');
register_signal(myBuyCondition, 'Converged And Above EMA200');
