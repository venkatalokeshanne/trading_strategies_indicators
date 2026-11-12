/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kloom Session Levels
 * Author       : Kloom
 * Source URL   : https://www.tradingview.com/script/8Si9e0te-Kloom-Session-Levels-NY-and-London-Sessions-PDH-PDL
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kloom Session Levels_TV
 *
 * Deviations from the original: Reviewed AI draft; both sessions in New York time via moment-timezone; PDH/PDL from
 *   the previous completed daily bar; bgcolor tints as high-low bands.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kloom Session Levels_TV', 'price');
const myMoment = library('moment-timezone');
const myShowNy = input.boolean('Show NY session', true);
const myNyStart = input.number('NY Start HHMM', 930, { min: 0, max: 2359 });
const myNyEnd = input.number('NY End HHMM', 1600, { min: 0, max: 2359 });
const myShowLdn = input.boolean('Show London session', true);
const myLdnStart = input.number('London Start HHMM', 300, { min: 0, max: 2359 });
const myLdnEnd = input.number('London End HHMM', 1130, { min: 0, max: 2359 });
const myShowPdhl = input.boolean('Show PDH/PDL', true);
const myShowOpen = input.boolean('Show session open', true);
const myMin = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
// both sessions are New York clock times, as in the Pine script
const myMinutes = time.map(_t => { const myT = myMoment.tz(_t * 1000, 'America/New_York'); return myT.hours() * 60 + myT.minutes(); });
const myInNy = myMinutes.map(_m => _m >= myMin(myNyStart) && _m < myMin(myNyEnd));
const myInLdn = myMinutes.map(_m => _m >= myMin(myLdnStart) && _m < myMin(myLdnEnd));
const myRun = (_in) => {
	const myHi = [], myLo = [], myOp = [];
	let myH = null, myL = null, myO = null;
	for (let myI = 0; myI < close.length; myI += 1) {
		if (_in[myI]) {
			if (myI === 0 || !_in[myI - 1]) { myH = high[myI]; myL = low[myI]; myO = open[myI]; }
			else { myH = Math.max(myH, high[myI]); myL = Math.min(myL, low[myI]); }
		}
		myHi.push(_in[myI] ? myH : null); myLo.push(_in[myI] ? myL : null); myOp.push(_in[myI] ? myO : null);
	}
	return { hi: myHi, lo: myLo, op: myOp };
};
const myNy = myRun(myInNy), myLdn = myRun(myInLdn);
const myDaily = await request.history(current.ticker, 'D');
assert(!myDaily.error, 'Error fetching daily data: ' + myDaily.error);
// request.security(D, high[1]/low[1], lookahead_on): the previous completed day on every chart bar of the next day
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(myDaily.time, _vals.map((_v, _k) => _k ? _vals[_k - 1] : null), time, 'le'), 'constant');
const myPdh = myLand(myDaily.high), myPdl = myLand(myDaily.low);
const myGate = (_s, _f) => _s.map((_v, _i) => _f[_i] ? _v : null);
const myNyOn = myInNy.map(_f => _f && myShowNy), myLdnOn = myInLdn.map(_f => _f && myShowLdn);
paint(myGate(myNy.hi, myNyOn), { name: 'NY High', color: 'rgba(41,98,255,0.8)' });
paint(myGate(myNy.lo, myNyOn), { name: 'NY Low', color: 'rgba(41,98,255,0.8)' });
paint(myGate(myNy.op, myNyOn.map(_f => _f && myShowOpen)), { name: 'NY Open', color: 'rgba(41,98,255,0.5)', style: 'dotted', marker: 'circle' });
paint(myGate(myLdn.hi, myLdnOn), { name: 'London High', color: 'rgba(156,39,176,0.8)' });
paint(myGate(myLdn.lo, myLdnOn), { name: 'London Low', color: 'rgba(156,39,176,0.8)' });
const myPdhP = paint(myPdh.map(_v => myShowPdhl ? _v : null), { name: 'PDH', color: 'rgba(255,152,0,0.8)' });
const myPdlP = paint(myPdl.map(_v => myShowPdhl ? _v : null), { name: 'PDL', color: 'rgba(255,152,0,0.8)' });
const myLast = close.length - 1;
if (myShowPdhl && myPdh[myLast] !== null) {
	paint_label_at_line(myPdhP, myLast, 'PDH ' + myPdh[myLast], { color: 'orange' });
	paint_label_at_line(myPdlP, myLast, 'PDL ' + myPdl[myLast], { color: 'orange' });
}
// bgcolor session tints are shown as high-low bands
color_cloud(myGate(high, myNyOn), myGate(low, myNyOn), 'rgba(41,98,255,0.12)', 'rgba(41,98,255,0.12)', 'NY Up', 'NY Dn');
color_cloud(myGate(high, myLdnOn), myGate(low, myLdnOn), 'rgba(156,39,176,0.12)', 'rgba(156,39,176,0.12)', 'London Up', 'London Dn');
register_signal(myInNy.map((_f, _i) => _f && !(_i > 0 && myInNy[_i - 1])), 'NY Session Start');
register_signal(myInLdn.map((_f, _i) => _f && !(_i > 0 && myInLdn[_i - 1])), 'London Session Start');
register_signal(myInNy, 'In NY Session');
register_signal(myInLdn, 'In London Session');
