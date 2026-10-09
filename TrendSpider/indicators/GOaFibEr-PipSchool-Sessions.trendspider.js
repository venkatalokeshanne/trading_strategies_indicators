/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : PipSchool
 * Author       : RyanAcademy
 * Source URL   : https://www.tradingview.com/script/GOaFibEr-PipSchool-Sessions
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : PipSchool Sessions_TV
 *
 * Deviations from the original: Reviewed AI draft; New York session clocks via moment-timezone; bgcolor replaced by
 *   high-low bands; resolution input dropped (sessions restart daily).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('PipSchool Sessions_TV', 'price');
const myMoment = library('moment-timezone');
const myHighLowView = input.boolean('High/Low View', false);
const myShowLondon = input.boolean('London Session', true);
const myShowNy = input.boolean('New York Session', true);
const myLondonStart = input.number('London Start HHMM', 300, { min: 0, max: 2359 });
const myLondonEnd = input.number('London End HHMM', 1200, { min: 0, max: 2359 });
const myNyStart = input.number('New York Start HHMM', 800, { min: 0, max: 2359 });
const myNyEnd = input.number('New York End HHMM', 1700, { min: 0, max: 2359 });
const myMinutes = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
const myIn = (_m, _s, _e) => { const myS = myMinutes(_s), myE = myMinutes(_e); return myS <= myE ? (_m >= myS && _m < myE) : (_m >= myS || _m < myE); };
// session clocks are New York time, as in the Pine script
const myMin = time.map(_t => { const myT = myMoment.tz(_t * 1000, 'America/New_York'); return myT.hours() * 60 + myT.minutes(); });
const myLondon = myMin.map(_m => myIn(_m, myLondonStart, myLondonEnd));
const myNy = myMin.map(_m => myIn(_m, myNyStart, myNyEnd));
const myRun = (_flags) => {
	const myHi = [], myLo = [];
	let myH = null, myL = null;
	for (let myI = 0; myI < close.length; myI += 1) {
		if (_flags[myI]) {
			if (myI === 0 || !_flags[myI - 1]) { myH = high[myI]; myL = low[myI]; }
			else { myH = Math.max(myH, high[myI]); myL = Math.min(myL, low[myI]); }
		}
		myHi.push(_flags[myI] ? myH : null);
		myLo.push(_flags[myI] ? myL : null);
	}
	return { hi: myHi, lo: myLo };
};
const myLondonRun = myRun(myLondon);
const myNyRun = myRun(myNy);
const myGate = (_s, _f) => _s.map((_v, _i) => _f[_i] ? _v : null);
// bgcolor is not available: the plain view shades the bar ranges, the high/low view shades the running session range
const myLonOn = myLondon.map(_f => _f && myShowLondon);
const myNyOn = myNy.map(_f => _f && myShowNy);
const myLonHi = myHighLowView ? myLondonRun.hi : myGate(high, myLonOn);
const myLonLo = myHighLowView ? myLondonRun.lo : myGate(low, myLonOn);
const myNyHi = myHighLowView ? myNyRun.hi : myGate(high, myNyOn);
const myNyLo = myHighLowView ? myNyRun.lo : myGate(low, myNyOn);
color_cloud(myGate(myLonHi, myLonOn), myGate(myLonLo, myLonOn), 'rgba(0,128,0,0.2)', 'rgba(0,128,0,0.2)', 'London Up', 'London Dn');
color_cloud(myGate(myNyHi, myNyOn), myGate(myNyLo, myNyOn), 'rgba(255,0,0,0.2)', 'rgba(255,0,0,0.2)', 'New York Up', 'New York Dn');
register_signal(myLonOn, 'London Session Active');
register_signal(myNyOn, 'New York Session Active');
