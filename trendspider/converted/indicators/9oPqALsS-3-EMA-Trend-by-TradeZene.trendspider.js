/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 3 EMAs by TradeZene
 * Author       : TradeZene
 * Source URL   : https://www.tradingview.com/script/9oPqALsS-3-EMA-Trend-by-TradeZene
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 3 EMAs by TradeZene_TV
 *
 * The Pine original, in words: EMA 9, 27 and 108; background blue when close > EMA 27, orange when below.
 *
 * Deviations from the original: trend shown by candle colour instead of the background tint.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('3 EMAs by TradeZene_TV', 'price');

// EMA length inputs
const emaRow1 = input.row();
const myEma1Len = emaRow1.number('EMA 1 Length', 9, { min: 1, max: 500 });
const myEma2Len = emaRow1.number('EMA 2 Length', 27, { min: 1, max: 500 });
const myEma3Len = emaRow1.number('EMA 3 Length', 108, { min: 1, max: 500 });

// Show/hide toggles
const showRow = input.row();
const myShowEma1 = showRow.boolean('Show EMA 1', true);
const myShowEma2 = showRow.boolean('Show EMA 2', true);
const myShowEma3 = showRow.boolean('Show EMA 3', true);

// EMA calculations
const myEma1 = ema(close, myEma1Len);
const myEma2 = ema(close, myEma2Len);
const myEma3 = ema(close, myEma3Len);

// Plot EMAs, respecting the show toggles (null series when hidden,
// to keep the number of paint() calls constant)
paint(myShowEma1 ? myEma1 : series_of(null), { name: 'EMA1', color: 'blue', thickness: 1 });
paint(myShowEma2 ? myEma2 : series_of(null), { name: 'EMA2', color: 'black', thickness: 2 });
paint(myShowEma3 ? myEma3 : series_of(null), { name: 'EMA3', color: 'orange', thickness: 2 });

// Trend logic, based on EMA 2 (as per the Pine Script logic)
const myBullTrend = for_every(close, myEma2, (_c, _e2) => _c > _e2);
const myBearTrend = for_every(close, myEma2, (_c, _e2) => _c < _e2);

// Background coloring approximation: TrendSpider Custom JS API has no
// bgcolor() equivalent, so we use color_candles() instead to visualize
// the bullish/bearish trend state on the chart.
const myCandleColors = for_every(myBullTrend, myBearTrend, (_bull, _bear) => {
	if (_bull) return 'rgba(0,0,255,0.35)';
	if (_bear) return 'rgba(255,165,0,0.45)';
	return null;
});
color_candles(myCandleColors);

// Signals for scanners, alerts, and strategies
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');
