/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RTH ADR
 * Author       : sukyu
 * Source URL   : https://www.tradingview.com/script/Tw3dM9WD-ADR-of-RTH
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RTH ADR_TV
 *
 * Deviations from the original: Reviewed AI draft; Pacific-time RTH window via moment-timezone; opacity inputs
 *   dropped; table via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RTH ADR_TV', 'price');
const myMoment = library('moment-timezone');
const myLookbackDays = input.number('Lookback Days', 14, { min: 1, max: 500 });
const myStart = input.number('RTH Start HHMM', 630, { min: 0, max: 2359 });
const myEnd = input.number('RTH End HHMM', 1310, { min: 0, max: 2359 });
const myMin = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
const myStartMin = myMin(myStart);
const myEndMin = myMin(myEnd);
// session clock in Pacific time as in the Pine script
const myIn = time.map(_t => { const myT = myMoment.tz(_t * 1000, 'America/Los_Angeles'); const myM = myT.hours() * 60 + myT.minutes(); return myM >= myStartMin && myM < myEndMin; });
const myRanges = [];
let myHigh = null, myLow = null;
const myCurrent = [];
const myAvg = [];
for (let myI = 0; myI < close.length; myI += 1) {
	const myPrevIn = myI > 0 ? myIn[myI - 1] : false;
	if (myIn[myI] && !myPrevIn) { myHigh = high[myI]; myLow = low[myI]; }
	else if (myIn[myI]) { myHigh = Math.max(myHigh, high[myI]); myLow = Math.min(myLow, low[myI]); }
	if (!myIn[myI] && myPrevIn && myHigh !== null) myRanges.push(myHigh - myLow);
	const myN = Math.min(myLookbackDays, myRanges.length);
	let mySum = 0;
	for (let myK = 0; myK < myN; myK += 1) mySum += myRanges[myRanges.length - 1 - myK];
	myAvg.push(myN > 0 ? mySum / myN : null);
	myCurrent.push(myHigh !== null ? myHigh - myLow : null);
}
const myLast = close.length - 1;
const myPct = (myAvg[myLast] !== null && myAvg[myLast] !== 0 && myCurrent[myLast] !== null) ? myCurrent[myLast] / myAvg[myLast] * 100 : null;
const myFmt = (_v) => _v === null ? 'n/a' : _v.toFixed(2);
const myRow = (_a, _b) => ({ cells: [{ text: _a, color: 'black', background_color: 'rgba(255,255,255,0.85)' }, { text: _b, color: 'black', background_color: 'rgba(255,255,255,0.85)' }] });
paint_overlay('RTH ADR Table', { position: 'top_right' }, {
	rows: [
		myRow('RTH ADR (' + myLookbackDays + 'd)', myFmt(myAvg[myLast])),
		myRow('Today Range', myFmt(myCurrent[myLast])),
		myRow('Today % of Avg', myPct === null ? 'n/a' : myPct.toFixed(2) + '%')
	]
});
register_signal(myIn, 'In RTH Session');
register_signal(close.map((_c, _i) => myAvg[_i] !== null && myAvg[_i] !== 0 && myCurrent[_i] !== null && myCurrent[_i] / myAvg[_i] > 1), 'Range Above Average');
register_signal(close.map((_c, _i) => myAvg[_i] !== null && myAvg[_i] !== 0 && myCurrent[_i] !== null && myCurrent[_i] / myAvg[_i] < 0.5), 'Range Below Half Average');
