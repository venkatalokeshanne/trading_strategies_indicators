/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Custom Session Price Lines (GMT+8)
 * Author       : acerpeepz
 * Source URL   : https://www.tradingview.com/script/LwE6wSUM-Custom-Session-Price-Lines-GMT-8-1minute-TIMEFRAME
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Custom Session Price Lines (GMT+8)_TV
 *
 * The Pine original, in words: GMT+8 session lines: the 06:04 open carried through 06:00-19:59, a 06:04-16:59 line
 *   at the 16:59 close, and a 17:00-19:59 line at the 19:59 close.
 *
 * Deviations from the original: time zone fixed at GMT+8 (the Pine's default); dashed lines drawn as solid.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Custom Session Price Lines (GMT+8)_TV', 'price');

// NOTE: TrendSpider's built-in time helpers (bar_at, time_of) use the
// *exchange* timezone, not an arbitrary fixed GMT+8 offset like Pine's
// `hour(time, "GMT+8")`. There is no tz-database conversion available in
// the Custom JS API, so GMT+8 is reproduced manually as a fixed +8h
// offset applied to the UTC unix timestamp (no DST, matching Pine's
// behavior for a fixed "GMT+8" string).

const myOffsetSeconds = 8 * 3600;

// Precompute GMT+8 hour/minute for every candle
const myHourArray = time.map(_t => {
	const myLocalSec = (((_t + myOffsetSeconds) % 86400) + 86400) % 86400;
	return Math.floor(myLocalSec / 3600);
});
const myMinuteArray = time.map(_t => {
	const myLocalSec = (((_t + myOffsetSeconds) % 86400) + 86400) % 86400;
	return Math.floor((myLocalSec % 3600) / 60);
});

const myWhiteSeries = Array(close.length).fill(null);
const myOrangeSeries = Array(close.length).fill(null);
const myBlueSeries = Array(close.length).fill(null);

const myOpen0604BarSignal = Array(close.length).fill(false);
const myOrangeDrawnSignal = Array(close.length).fill(false);
const myBlueDrawnSignal = Array(close.length).fill(false);
const myWhiteActiveSignal = Array(close.length).fill(false);

let myOpen0604Index = null;
let myOpen0604Price = null;
let myOpen1700Index = null;

for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	const myHour = myHourArray[myCandleIndex];
	const myMinute = myMinuteArray[myCandleIndex];

	// --- 1. White line: anchor at 06:04 GMT+8 ---
	if (myHour === 6 && myMinute === 4) {
		myOpen0604Index = myCandleIndex;
		myOpen0604Price = open[myCandleIndex];
		myOpen0604BarSignal[myCandleIndex] = true;
	}

	const myInWhiteSession =
		(myHour > 6 || (myHour === 6 && myMinute >= 0)) &&
		(myHour < 19 || (myHour === 19 && myMinute <= 59));

	if (myInWhiteSession && myOpen0604Index !== null) {
		myWhiteSeries[myCandleIndex] = myOpen0604Price;
		myWhiteActiveSignal[myCandleIndex] = true;
	}

	// --- 2. Orange line: drawn at 16:59 GMT+8, spanning back to 06:04 anchor ---
	if (myHour === 16 && myMinute === 59 && myOpen0604Index !== null) {
		const myOrangeValue = close[myCandleIndex];
		for (let myFillIndex = myOpen0604Index; myFillIndex <= myCandleIndex; myFillIndex += 1) {
			myOrangeSeries[myFillIndex] = myOrangeValue;
		}
		myOrangeDrawnSignal[myCandleIndex] = true;
	}

	// --- 3. Blue line: anchor at 17:00, drawn at 19:59 GMT+8 ---
	if (myHour === 17 && myMinute === 0) {
		myOpen1700Index = myCandleIndex;
	}

	if (myHour === 19 && myMinute === 59 && myOpen1700Index !== null) {
		const myBlueValue = close[myCandleIndex];
		for (let myFillIndex = myOpen1700Index; myFillIndex <= myCandleIndex; myFillIndex += 1) {
			myBlueSeries[myFillIndex] = myBlueValue;
		}
		myBlueDrawnSignal[myCandleIndex] = true;
	}
}

paint(myWhiteSeries, { name: 'White Session Line', color: 'white', thickness: 1 });
paint(myOrangeSeries, { name: 'Orange Line', color: 'orange', thickness: 1 });
paint(myBlueSeries, { name: 'Blue Line', color: 'blue', thickness: 1 });

register_signal(myOpen0604BarSignal, 'Open 0604 Bar');
register_signal(myWhiteActiveSignal, 'White Session Active');
register_signal(myOrangeDrawnSignal, 'Orange Line Drawn At 1659');
register_signal(myBlueDrawnSignal, 'Blue Line Drawn At 1959');
