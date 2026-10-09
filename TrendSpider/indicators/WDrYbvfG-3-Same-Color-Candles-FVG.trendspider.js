/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 3 Same-Color Candles FVG
 * Author       : hamza20255
 * Source URL   : https://www.tradingview.com/script/WDrYbvfG-3-Same-Color-Candles-FVG
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 3 Same-Color Candles FVG_TV
 *
 * The Pine original, in words: a box over the gap when three same-colour candles leave a fair value gap (low > high
 *   two bars back for green, high < low two bars back for red), extended 3 bars.
 *
 * Deviations from the original: boxes drawn as filled top/bottom lines; colour inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
// EXPERIMENT: TrendSpider has no native "box" drawing primitive like
// Pine Script's box.new(). This indicator approximates the FVG boxes
// using "ladder" style lines (step lines) spanning from the start of
// the 3-candle pattern to a configurable number of bars ahead, with
// fill() used to shade the area between the top and bottom lines.
// The detection logic (3 same-color candles + gap condition) is an
// exact port of the Pine Script conditions.
describe_indicator('3 Same-Color Candles FVG_TV', 'price');

const myShowBullish = input.boolean('Show Bullish FVG', true);
const myShowBearish = input.boolean('Show Bearish FVG', true);
const myBoxExtend = input.number('Box Extension Ahead (Bars)', 3, { min: 0, max: 50 });

const myIsGreen = for_every(close, open, (_c, _o) => _c > _o);
const myIsRed = for_every(close, open, (_c, _o) => _c < _o);

// Pine: close[idx] where idx=0 is current bar, idx=2 is two bars back.
// In our arrays index increases forward in time, so "idx bars ago" at
// position i is i - idx.
const myThreeGreen = series_of(false);
const myThreeRed = series_of(false);
const myIsBullishFVG = series_of(false);
const myIsBearishFVG = series_of(false);

for (let myIndex = 2; myIndex < close.length; myIndex += 1) {
	myThreeGreen[myIndex] = myIsGreen[myIndex - 2] && myIsGreen[myIndex - 1] && myIsGreen[myIndex];
	myThreeRed[myIndex] = myIsRed[myIndex - 2] && myIsRed[myIndex - 1] && myIsRed[myIndex];

	myIsBullishFVG[myIndex] = myThreeGreen[myIndex] && (low[myIndex] > high[myIndex - 2]);
	myIsBearishFVG[myIndex] = myThreeRed[myIndex] && (high[myIndex] < low[myIndex - 2]);
}

// Build "box" approximations as ladder lines.
const myBullTop = series_of(null);
const myBullBottom = series_of(null);
const myBearTop = series_of(null);
const myBearBottom = series_of(null);

for (let myIndex = 2; myIndex < close.length; myIndex += 1) {
	if (myIsBullishFVG[myIndex]) {
		const myLeft = myIndex - 2;
		const myRight = Math.min(myIndex + myBoxExtend, close.length - 1);

		for (let myFillIndex = myLeft; myFillIndex <= myRight; myFillIndex += 1) {
			myBullTop[myFillIndex] = low[myIndex];
			myBullBottom[myFillIndex] = high[myIndex - 2];
		}
		if (myRight + 1 < close.length) {
			myBullTop[myRight + 1] = null;
			myBullBottom[myRight + 1] = null;
		}
	}

	if (myIsBearishFVG[myIndex]) {
		const myLeft = myIndex - 2;
		const myRight = Math.min(myIndex + myBoxExtend, close.length - 1);

		for (let myFillIndex = myLeft; myFillIndex <= myRight; myFillIndex += 1) {
			myBearTop[myFillIndex] = low[myIndex - 2];
			myBearBottom[myFillIndex] = high[myIndex];
		}
		if (myRight + 1 < close.length) {
			myBearTop[myRight + 1] = null;
			myBearBottom[myRight + 1] = null;
		}
	}
}

const myBullTopPainted = paint(myShowBullish ? myBullTop : series_of(null), { name: 'BullishFVGTop', color: 'green', thickness: 1 });
const myBullBottomPainted = paint(myShowBullish ? myBullBottom : series_of(null), { name: 'BullishFVGBottom', color: 'green', thickness: 1 });
fill(myBullTopPainted, myBullBottomPainted, 'green', 0.2);

const myBearTopPainted = paint(myShowBearish ? myBearTop : series_of(null), { name: 'BearishFVGTop', color: 'red', thickness: 1 });
const myBearBottomPainted = paint(myShowBearish ? myBearBottom : series_of(null), { name: 'BearishFVGBottom', color: 'red', thickness: 1 });
fill(myBearTopPainted, myBearBottomPainted, 'red', 0.2);

// Signals for scanners, alerts and strategies
register_signal(myIsBullishFVG, 'Bullish FVG');
register_signal(myIsBearishFVG, 'Bearish FVG');
