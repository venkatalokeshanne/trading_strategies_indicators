/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : ORB 15m Range Breakout - Trading Trio
 * Author       : tonyflies1624
 * Source URL   : https://www.tradingview.com/script/geWHFQNg-ORB-15m-Range-Breakout-Trading-Trio
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : ORB 15m Range Breakout_TV
 *
 * Deviations from the original: Reviewed AI draft; New York clock via moment-timezone; range lines drawn through the
 *   window and until the close time; line style options dropped; alerts mapped to
 *   signals.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('ORB 15m Range Breakout_TV', 'price');
const myMoment = library('moment-timezone');
const myStart = input.number('Window Start HHMM', 930, { min: 0, max: 2359 });
const myEnd = input.number('Window End HHMM', 945, { min: 0, max: 2359 });
const myClose = input.number('Session Close HHMM', 1600, { min: 0, max: 2359 });
const myHiColor = input.color('High Line Color', 'green');
const myLoColor = input.color('Low Line Color', 'red');
const myShowShapes = input.boolean('Show Breakout Marks', true);
const myMin = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
const myS = myMin(myStart), myE = myMin(myEnd), myC = myMin(myClose);
// New York clock as in the Pine script
const myMinutes = time.map(_t => { const myT = myMoment.tz(_t * 1000, 'America/New_York'); return myT.hours() * 60 + myT.minutes(); });
const myIn = myMinutes.map(_m => _m >= myS && _m < myE);
const myPast = myMinutes.map(_m => _m >= myC);
const myHiLine = close.map(() => null);
const myLoLine = close.map(() => null);
const myUp = close.map(() => false);
const myDown = close.map(() => false);
let myHi = null, myLo = null, myStableHi = null, myStableLo = null, myHiBroken = false, myLoBroken = false;
for (let myI = 0; myI < close.length; myI += 1) {
	const myPrevIn = myI > 0 ? myIn[myI - 1] : false;
	if (myIn[myI] && !myPrevIn) { myHi = high[myI]; myLo = low[myI]; myHiBroken = false; myLoBroken = false; }
	else if (myIn[myI]) { myHi = Math.max(myHi, high[myI]); myLo = Math.min(myLo, low[myI]); }
	if (!myIn[myI] && myPrevIn) { myStableHi = myHi; myStableLo = myLo; }
	if (myIn[myI]) { myHiLine[myI] = myHi; myLoLine[myI] = myLo; }
	else if (myStableHi !== null && !myPast[myI]) { myHiLine[myI] = myStableHi; myLoLine[myI] = myStableLo; }
	const myBreakUp = !myIn[myI] && !myPast[myI] && myStableHi !== null && !myHiBroken && close[myI] > myStableHi;
	const myBreakDown = !myIn[myI] && !myPast[myI] && myStableLo !== null && !myLoBroken && close[myI] < myStableLo;
	if (myBreakUp) myHiBroken = true;
	if (myBreakDown) myLoBroken = true;
	myUp[myI] = myBreakUp;
	myDown[myI] = myBreakDown;
}
paint(myHiLine, { name: 'Range High', color: myHiColor, thickness: 2 });
paint(myLoLine, { name: 'Range Low', color: myLoColor, thickness: 2 });
paint(myUp.map(_f => (myShowShapes && _f) ? constants.icons.triangle_up : null), { name: 'Bullish Break Mark', style: 'labels_below', color: 'green' });
paint(myDown.map(_f => (myShowShapes && _f) ? constants.icons.triangle_down : null), { name: 'Bearish Break Mark', style: 'labels_above', color: 'red' });
register_signal(myUp, 'Bullish Breakout');
register_signal(myDown, 'Bearish Breakout');
