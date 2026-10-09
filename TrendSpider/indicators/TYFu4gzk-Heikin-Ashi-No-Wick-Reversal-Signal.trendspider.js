/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Heikin Ashi No Wick Reversal Signal
 * Author       : smino2
 * Source URL   : https://www.tradingview.com/script/TYFu4gzk-Heikin-Ashi-No-Wick-Reversal-Signal
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Heikin Ashi No Wick Reversal Signal_TV
 *
 * The Pine original, in words: Heikin Ashi: after a colour change, LONG on the first bullish HA candle with no
 *   lower wick, SHORT on the first bearish one with no upper wick.
 *
 * Deviations from the original: none.
 * Not carried over: alertconditions — use the HA Long/Short No Wick signals.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Heikin Ashi No Wick Reversal Signal_TV', 'price');

// This indicator rebuilds Heikin Ashi candles from the current
// chart's OHLC data, then looks for the first "no wick" candle
// that appears right after a color flip (bull/bear), exactly as
// the original Pine Script logic does.

const myCandleCount = close.length;

// Heikin Ashi close is just the average of OHLC, computable
// in one shot since it has no recursive dependency.
const myHaClose = ohlc4;

// Heikin Ashi open depends on the previous HA open/close, so it
// must be computed sequentially (not via indicator functions).
const myHaOpen = series_of(null);
const myHaHigh = series_of(null);
const myHaLow = series_of(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myIndex === 0) {
		myHaOpen[myIndex] = (open[myIndex] + close[myIndex]) / 2;
	}
	else {
		myHaOpen[myIndex] = (myHaOpen[myIndex - 1] + myHaClose[myIndex - 1]) / 2;
	}

	myHaHigh[myIndex] = Math.max(high[myIndex], myHaOpen[myIndex], myHaClose[myIndex]);
	myHaLow[myIndex] = Math.min(low[myIndex], myHaOpen[myIndex], myHaClose[myIndex]);
}

// Sequence tracking and signal detection, mirroring the Pine
// Script's "var bool" stateful logic candle by candle.
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

let myWaitingBullNoWick = false;
let myWaitingBearNoWick = false;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myBull = myHaClose[myIndex] > myHaOpen[myIndex];
	const myBear = myHaClose[myIndex] < myHaOpen[myIndex];

	const myPrevBull = myHaClose[myIndex - 1] > myHaOpen[myIndex - 1];
	const myPrevBear = myHaClose[myIndex - 1] < myHaOpen[myIndex - 1];

	const myNoBottomWick = myHaLow[myIndex] === myHaOpen[myIndex];
	const myNoTopWick = myHaHigh[myIndex] === myHaOpen[myIndex];

	const myNewBullSequence = myBull && myPrevBear;
	const myNewBearSequence = myBear && myPrevBull;

	if (myNewBullSequence) {
		myWaitingBullNoWick = true;
		myWaitingBearNoWick = false;
	}

	if (myNewBearSequence) {
		myWaitingBearNoWick = true;
		myWaitingBullNoWick = false;
	}

	const myLong = myWaitingBullNoWick && myBull && myNoBottomWick;
	const myShort = myWaitingBearNoWick && myBear && myNoTopWick;

	if (myLong) {
		myWaitingBullNoWick = false;
	}

	if (myShort) {
		myWaitingBearNoWick = false;
	}

	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;
}

// Markers placed below/above bars, like the original plotshape calls.
const myLongMarks = for_every(myLongSignal, _signal => _signal ? 'LONG' : null);
const myShortMarks = for_every(myShortSignal, _signal => _signal ? 'SHORT' : null);

paint(myLongMarks, { style: 'labels_below', color: 'green', name: 'Long Signal' });
paint(myShortMarks, { style: 'labels_above', color: 'red', name: 'Short Signal' });

// Signals exposed for use in Scanners, Alerts and Strategy Tester.
register_signal(myLongSignal, 'HA Long No Wick');
register_signal(myShortSignal, 'HA Short No Wick');
