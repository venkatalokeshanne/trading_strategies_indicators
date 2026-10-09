/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VWAP + EMA 9 + EMA 20
 * Author       : deflorimontel
 * Source URL   : https://www.tradingview.com/script/jWE4A8pC-VWAP-EMA-9-EMA-20
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VWAP + EMA 9 + EMA 20_TV
 *
 * The Pine original, in words: session VWAP of hlc3, EMA 9 and EMA 20.
 *
 * Deviations from the original: VWAP resets on TrendSpider's session boundaries (bar_at().session). Cross/VWAP
 *   signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VWAP + EMA 9 + EMA 20_TV', 'price');

// VWAP resets daily by default in TradingView (ta.vwap). We replicate that
// by anchoring VWAP calculation at the start of each trading session/day.
const mySessions = time.map(_t => bar_at(_t).session);
const myVwapSeries = series_of(null);

let mySessionStartIndex = 0;
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIndex === 0 || mySessions[myIndex] !== mySessions[myIndex - 1]) {
		mySessionStartIndex = myIndex;
	}
}

// Compute vwap per session by iterating over session boundaries
const myVwapFull = series_of(null);
let mySegmentStart = 0;
for (let myIndex = 1; myIndex <= close.length; myIndex += 1) {
	const myIsBoundary = (myIndex === close.length) || (mySessions[myIndex] !== mySessions[mySegmentStart]);
	if (myIsBoundary) {
		const mySegmentVwap = vwap(hlc3, volume, mySegmentStart, myIndex - 1);
		for (let myFill = mySegmentStart; myFill < myIndex; myFill += 1) {
			myVwapFull[myFill] = mySegmentVwap[myFill];
		}
		mySegmentStart = myIndex;
	}
}

const myEma9 = ema(close, 9);
const myEma20 = ema(close, 20);

paint(myVwapFull, { name: 'VWAP', color: '#2962FF', thickness: 2, forceUsePriceAxis: true });
paint(myEma9, { name: 'EMA 9', color: '#FDD835', thickness: 2, forceUsePriceAxis: true });
paint(myEma20, { name: 'EMA 20', color: '#EF5350', thickness: 2, forceUsePriceAxis: true });

// Signals for scanners/alerts/strategies: EMA9/EMA20 crossovers and
// price position relative to VWAP, mapped from common usages of this setup.
const myBullishCross = for_every(myEma9, myEma20, (_e9, _e20, _prev, _i) => {
	if (_i === 0) return false;
	return myEma9[_i - 1] <= myEma20[_i - 1] && _e9 > _e20;
});

const myBearishCross = for_every(myEma9, myEma20, (_e9, _e20, _prev, _i) => {
	if (_i === 0) return false;
	return myEma9[_i - 1] >= myEma20[_i - 1] && _e9 < _e20;
});

const myPriceAboveVwap = for_every(close, myVwapFull, (_c, _v) => _v !== null && _c > _v);
const myPriceBelowVwap = for_every(close, myVwapFull, (_c, _v) => _v !== null && _c < _v);

register_signal(myBullishCross, 'EMA9 Crosses Above EMA20');
register_signal(myBearishCross, 'EMA9 Crosses Below EMA20');
register_signal(myPriceAboveVwap, 'Price Above VWAP');
register_signal(myPriceBelowVwap, 'Price Below VWAP');
