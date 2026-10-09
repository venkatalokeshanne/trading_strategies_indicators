/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Colored Bars
 * Author       : bashu9
 * Source URL   : https://www.tradingview.com/script/r90ArcSO-Colored-Bars
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Colored Bars_TV
 *
 * The Pine original, in words: colours each candle by its Gann type vs the previous bar: up (green), down (red),
 *   outside (fuchsia), inside (grey); darker shade when the body goes against the type.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Colored Bars_TV', 'price');

// Shows Show Bar Colors toggle, same as Pine input
const myShowColors = input.boolean('Show Bar Colors', true);

// Darkens a hex color by a given percent, replicating Pine's darken()
function myDarken(_hex, _pct) {
	const myFactor = 1.0 - _pct / 100.0;
	const myR = parseInt(_hex.slice(1, 3), 16);
	const myG = parseInt(_hex.slice(3, 5), 16);
	const myB = parseInt(_hex.slice(5, 7), 16);
	const myRound = _v => Math.max(0, Math.min(255, Math.round(_v * myFactor)));
	const myToHex = _v => _v.toString(16).padStart(2, '0');
	return `#${myToHex(myRound(myR))}${myToHex(myRound(myG))}${myToHex(myRound(myB))}`;
}

const myGreen = '#00ff00';
const myRed = '#ff0000';
const myFuchsia = '#ff00ff';
const myGray = '#808080';

const myGreenDark = myDarken(myGreen, 50);
const myRedDark = myDarken(myRed, 50);
const myFuchsiaDark = myDarken(myFuchsia, 50);
const myGrayDark = myDarken(myGray, 50);

const UP = 1;
const DOWN = -1;
const INSIDE = 0;
const OUTSIDE = 2;

// Classify every bar according to Pine logic. First bar is a special case
// since there is no previous bar to compare against.
const myBType = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex === 0) {
		myBType[myIndex] = close[myIndex] > open[myIndex] ? UP : DOWN;
	}
	else {
		const myHigh = high[myIndex];
		const myLow = low[myIndex];
		const myPrevHigh = high[myIndex - 1];
		const myPrevLow = low[myIndex - 1];

		if (myHigh > myPrevHigh && myLow > myPrevLow) {
			myBType[myIndex] = UP;
		}
		else if (myHigh < myPrevHigh && myLow < myPrevLow) {
			myBType[myIndex] = DOWN;
		}
		else if (myHigh <= myPrevHigh && myLow >= myPrevLow) {
			myBType[myIndex] = INSIDE;
		}
		else {
			myBType[myIndex] = OUTSIDE;
		}
	}
}

// Build the per-candle color series, matching Pine's barcolor() logic
const myColors = for_every(open, close, myBType, (_open, _close, _type) => {
	if (!myShowColors) {
		return null;
	}

	if (_type === UP) {
		return _open < _close ? myGreen : myGreenDark;
	}
	if (_type === DOWN) {
		return _open > _close ? myRed : myRedDark;
	}
	if (_type === OUTSIDE) {
		return _open < _close ? myFuchsia : myFuchsiaDark;
	}
	// INSIDE
	return _open < _close ? myGray : myGrayDark;
});

color_candles(myColors);

// Signals for scanning/alerts/strategies, mapping each bar classification
register_signal(for_every(myBType, _type => _type === UP), 'Up Bar');
register_signal(for_every(myBType, _type => _type === DOWN), 'Down Bar');
register_signal(for_every(myBType, _type => _type === INSIDE), 'Inside Bar');
register_signal(for_every(myBType, _type => _type === OUTSIDE), 'Outside Bar');
