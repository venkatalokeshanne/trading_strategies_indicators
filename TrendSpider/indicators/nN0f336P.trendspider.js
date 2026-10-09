/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RG Kenny 2x VWAP
 * Author       : radek_gie
 * Source URL   : https://www.tradingview.com/script/nN0f336P
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RG Kenny 2x VWAP_TV
 *
 * Deviations from the original: Reviewed AI draft; New York time and weeks via moment-timezone (ISO week); colour
 *   inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RG Kenny 2x VWAP_TV', 'price');
const myMoment = library('moment-timezone');
const myTab = input.tab('VWAP');
const myShowBlue = myTab.boolean('Blue VWAP 1:00 ET', true);
const myShowYellow = myTab.boolean('Yellow MultiDay Mon 1:00', true);
// New York time as in the Pine script (tz = America/New_York)
const myNy = time.map(_t => myMoment.tz(_t * 1000, 'America/New_York'));
const myBlue = series_of(null);
const myYellow = series_of(null);
let myBluePV = 0, myBlueVol = 0, myBlueStarted = false, myLastBlueKey = null;
let myYellowPV = 0, myYellowVol = 0, myYellowStarted = false, myLastWeekKey = null;
for (let myI = 0; myI < close.length; myI += 1) {
	const myT = myNy[myI];
	const myHlc3 = (high[myI] + low[myI] + close[myI]) / 3;
	const myAfterAnchor = myT.hours() >= 1;
	const myDateKey = myT.format('YYYYMMDD');
	if (myAfterAnchor && myDateKey !== myLastBlueKey) {
		myBluePV = myHlc3 * volume[myI]; myBlueVol = volume[myI]; myBlueStarted = true; myLastBlueKey = myDateKey;
	} else if (myBlueStarted) {
		myBluePV += myHlc3 * volume[myI]; myBlueVol += volume[myI];
	}
	myBlue[myI] = (myBlueStarted && myBlueVol > 0) ? myBluePV / myBlueVol : null;
	const myWeekKey = myT.isoWeekYear() * 100 + myT.isoWeek();
	if (myT.day() === 1 && myAfterAnchor && myWeekKey !== myLastWeekKey) {
		myYellowPV = myHlc3 * volume[myI]; myYellowVol = volume[myI]; myYellowStarted = true; myLastWeekKey = myWeekKey;
	} else if (myYellowStarted) {
		myYellowPV += myHlc3 * volume[myI]; myYellowVol += volume[myI];
	}
	myYellow[myI] = (myYellowStarted && myYellowVol > 0) ? myYellowPV / myYellowVol : null;
}
paint(myBlue.map(_v => myShowBlue ? _v : null), { name: 'Blue VWAP', color: '#2962FF', thickness: 3 });
paint(myYellow.map(_v => myShowYellow ? _v : null), { name: 'Yellow VWAP', color: '#FFC107', thickness: 2 });
register_signal(close.map((_c, _i) => myBlue[_i] !== null && _c > myBlue[_i]), 'Close Above Blue VWAP');
register_signal(close.map((_c, _i) => myBlue[_i] !== null && _c < myBlue[_i]), 'Close Below Blue VWAP');
register_signal(close.map((_c, _i) => myYellow[_i] !== null && _c > myYellow[_i]), 'Close Above Yellow VWAP');
register_signal(close.map((_c, _i) => myYellow[_i] !== null && _c < myYellow[_i]), 'Close Below Yellow VWAP');
