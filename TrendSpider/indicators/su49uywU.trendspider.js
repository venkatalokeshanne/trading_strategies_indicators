/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : ATR 当前K线止损线
 * Author       : sansanling330
 * Source URL   : https://www.tradingview.com/script/su49uywU
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : ATR Stop - Yu Wu Wei_TV
 *
 * The Pine original, in words: two short lines on the last bar at close -/+ ATR(14) x 2 (long and short stop).
 *
 * Deviations from the original: drawn as a 3-bar projection from the last bar; TrendSpider name uses the listing
 *   title (the Pine title is Chinese).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('ATR Stop - Yu Wu Wei_TV', 'price');

// Inputs mirror the Pine script parameters
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMultiplier = input.number('Stop Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

// ATR computed on the current chart OHLC data
const myAtrValue = atr(high, low, close, myAtrLength);
const myStopDistance = mult(myAtrValue, myAtrMultiplier);

// Long stop: below current close. Short stop: above current close.
const myLongStop = sub(close, myStopDistance);
const myShortStop = add(close, myStopDistance);

// Pine only draws the lines on the last bar, extending a couple of bars
// into the future (bar_index - 1 to bar_index + 2). Here we approximate
// that visual by projecting the last value a few candles forward.
const myLastLongStop = myLongStop[myLongStop.length - 1];
const myLastShortStop = myShortStop[myShortStop.length - 1];

const myProjectionLength = 3;
const myLongProjection = [];
const myShortProjection = [];

for (let myIndex = 0; myIndex < myProjectionLength; myIndex += 1) {
	myLongProjection.push(myLastLongStop);
	myShortProjection.push(myLastShortStop);
}

// Historical lines kept as null, only the projection reproduces the Pine
// behavior of drawing a short line near the last bar.
// NOTE: we must reuse the id returned by paint() when projecting onto the
// same line, instead of calling paint_projection() with a duplicate "name".
// That was the root cause of the "out series already exists" error.
const myLongStopLinePainted = paint(series_of(null), { name: 'Long Stop Line', color: 'red', thickness: 2, style: 'line' });
const myShortStopLinePainted = paint(series_of(null), { name: 'Short Stop Line', color: 'red', thickness: 2, style: 'line' });

paint_projection(myLongStopLinePainted, myLongProjection);
paint_projection(myShortStopLinePainted, myShortProjection);

// Signals for scanners / alerts / strategy tester: raw long/short stop values

// Signal: close crossing below its own long stop level (price hit stop)
const myCloseBelowLongStop = for_every(close, myLongStop, (_c, _s) => _c <= _s);
register_signal(myCloseBelowLongStop, 'Close At or Below Long Stop');

// Signal: close crossing above its own short stop level (price hit stop)
const myCloseAboveShortStop = for_every(close, myShortStop, (_c, _s) => _c >= _s);
register_signal(myCloseAboveShortStop, 'Close At or Above Short Stop');
