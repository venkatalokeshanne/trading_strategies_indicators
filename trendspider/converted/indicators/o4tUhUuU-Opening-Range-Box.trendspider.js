/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Opening Range Box
 * Author       : mbern0426
 * Source URL   : https://www.tradingview.com/script/o4tUhUuU-Opening-Range-Box
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Opening Range Box_TV
 *
 * Deviations from the original: Reviewed AI draft; opening range built from the chart bars in Eastern time (the Pine
 *   uses 1-minute data); box as cloud between OR high/low; style options dropped; alerts
 *   mapped to signals.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Opening Range Box_TV', 'price');
const myMoment = library('moment-timezone');
const myOrStart = input.number('OR Start HHMM', 930, { min: 0, max: 2359 });
const myOrEnd = input.number('OR End HHMM', 945, { min: 0, max: 2359 });
const mySessionEnd = input.number('Session End HHMM', 1600, { min: 0, max: 2359 });
const myShowMid = input.boolean('Show Midline', true);
const myUpAlert = input.boolean('Breakout Up Signal', true);
const myDownAlert = input.boolean('Breakout Down Signal', true);
const myMin = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
const myS = myMin(myOrStart), myE = myMin(myOrEnd), myX = myMin(mySessionEnd);
// Eastern time as in the Pine script; the opening range is built from the chart bars (the Pine uses 1-minute data)
const myNy = time.map(_t => myMoment.tz(_t * 1000, 'America/New_York'));
const myTop = close.map(() => null);
const myBottom = close.map(() => null);
const myMid = close.map(() => null);
const myUp = close.map(() => false);
const myDown = close.map(() => false);
let myDay = null, myHi = null, myLo = null, myUpFired = false, myDownFired = false;
for (let myI = 0; myI < close.length; myI += 1) {
	const myKey = myNy[myI].format('YYYYMMDD');
	if (myKey !== myDay) { myDay = myKey; myHi = null; myLo = null; myUpFired = false; myDownFired = false; }
	const myM = myNy[myI].hours() * 60 + myNy[myI].minutes();
	if (myM >= myS && myM < myE) { myHi = myHi === null ? high[myI] : Math.max(myHi, high[myI]); myLo = myLo === null ? low[myI] : Math.min(myLo, low[myI]); }
	if (myM >= myE && myM < myX && myHi !== null) {
		myTop[myI] = myHi; myBottom[myI] = myLo;
		if (myShowMid) myMid[myI] = (myHi + myLo) / 2;
		if (close[myI] > myHi && !myUpFired) { myUpFired = true; if (myUpAlert) myUp[myI] = true; }
		if (close[myI] < myLo && !myDownFired) { myDownFired = true; if (myDownAlert) myDown[myI] = true; }
	}
}
paint(myTop, { name: 'OR High', color: 'blue', thickness: 1 });
paint(myBottom, { name: 'OR Low', color: 'blue', thickness: 1 });
color_cloud(myTop, myBottom, 'rgba(33,150,243,0.15)', 'rgba(33,150,243,0.15)', 'OR Up', 'OR Dn');
paint(myMid, { name: 'OR Midline', color: 'gray', thickness: 1 });
register_signal(myUp, 'Breakout Above OR High');
register_signal(myDown, 'Breakout Below OR Low');
