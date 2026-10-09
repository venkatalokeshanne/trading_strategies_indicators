/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : NY 9-10 Candle High/Low
 * Author       : version
 * Source URL   : https://www.tradingview.com/script/BZ6UmL9L-NY-9-10-Candle-High-Low
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : NY 9-10 Candle High/Low_TV
 *
 * The Pine original, in words: highlights the 09:00-10:00 New York bars and draws that window's high and low for 3
 *   more bars.
 *
 * Deviations from the original: levels drawn as line segments over the window and the next 3 bars; colour inputs
 *   fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('NY 9-10 Candle High/Low_TV', 'price');
const myMoment = library('moment-timezone');

// NOTE: Pine's `time(timeframe.period, session, timezone)` checks the exchange
// session clock in New York time. We approximate this using time_of(), which
// reports hours/minutes in the exchange time zone of the current ticker. This
// matches Pine's behavior for US-listed symbols but may differ for symbols
// whose native exchange time zone is not America/New_York.
const myStartHour = input.number('Window Start Hour (24h)', 9, { min: 0, max: 23 });
const myStartMinute = input.number('Window Start Minute', 0, { min: 0, max: 59 });
const myEndHour = input.number('Window End Hour (24h)', 10, { min: 0, max: 23 });
const myEndMinute = input.number('Window End Minute', 0, { min: 0, max: 59 });
const myExtendBars = input.number('Extend Bars', 3, { min: 1, max: 20 });

const myHighColor = 'green';
const myLowColor = 'red';
const myLength = close.length;

// determine, per candle, whether its time falls inside the NY window
const myInWindow = [];
for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myNy = myMoment.tz(time[myIndex] * 1000, 'America/New_York');
	const myMinutesOfDay = myNy.hours() * 60 + myNy.minutes();
	const myStartMinutesOfDay = myStartHour * 60 + myStartMinute;
	const myEndMinutesOfDay = myEndHour * 60 + myEndMinute;
	myInWindow.push(myMinutesOfDay >= myStartMinutesOfDay && myMinutesOfDay < myEndMinutesOfDay);
}

// track session high/low, session start/end flags
const mySessionStartFlag = series_of(false);
const mySessionEndFlag = series_of(false);
const myCandleColors = series_of(null);
let mySessionHigh = null;
let mySessionLow = null;
let myStartBarIndex = null;

// output ladder lines (extended levels), rebuilt as we iterate
const myHighLevel = series_of(null);
const myLowLevel = series_of(null);
let myExtendCountdown = 0;
let myLastEndedHigh = null;
let myLastEndedLow = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myWasInWindow = myIndex > 0 ? myInWindow[myIndex - 1] : false;
	const myNowInWindow = myInWindow[myIndex];
	const myStart = myNowInWindow && !myWasInWindow;
	const myEnd = !myNowInWindow && myWasInWindow;

	mySessionStartFlag[myIndex] = myStart;
	mySessionEndFlag[myIndex] = myEnd;

	if (myStart) {
		mySessionHigh = high[myIndex];
		mySessionLow = low[myIndex];
		myStartBarIndex = myIndex;
	}
	else if (myNowInWindow) {
		mySessionHigh = Math.max(mySessionHigh, high[myIndex]);
		mySessionLow = Math.min(mySessionLow, low[myIndex]);
	}

	myCandleColors[myIndex] = myNowInWindow ? 'rgba(255,235,59,0.35)' : null;

	if (myEnd) {
		myLastEndedHigh = mySessionHigh;
		myLastEndedLow = mySessionLow;
		myExtendCountdown = myExtendBars;
	}

	if (myNowInWindow) {
		myHighLevel[myIndex] = mySessionHigh;
		myLowLevel[myIndex] = mySessionLow;
	}
	else if (myExtendCountdown > 0 && myLastEndedHigh !== null) {
		myHighLevel[myIndex] = myLastEndedHigh;
		myLowLevel[myIndex] = myLastEndedLow;
		myExtendCountdown -= 1;
	}
	else {
		myHighLevel[myIndex] = null;
		myLowLevel[myIndex] = null;
	}
}

color_candles(myCandleColors);

paint(myHighLevel, { name: 'High Line', color: myHighColor, thickness: 2 });
paint(myLowLevel, { name: 'Low Line', color: myLowColor, thickness: 2 });

register_signal(mySessionStartFlag, 'NY Window Session Start');
register_signal(mySessionEndFlag, 'NY Window Session End');
register_signal(myInWindow, 'Inside NY Window');
