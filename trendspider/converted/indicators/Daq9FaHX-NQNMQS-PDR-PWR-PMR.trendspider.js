/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : NQNMQS PDR/PWR/PMR
 * Author       : niqonomiqs
 * Source URL   : https://www.tradingview.com/script/Daq9FaHX-NQNMQS-PDR-PWR-PMR
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : NQNMQS PDR PWR PMR_TV
 *
 * Deviations from the original: Previous day/week/month levels are step lines from chart bars in exchange time (Pine
 *   drew extended lines from the extreme bar); only the last-bar labels; style/colour
 *   inputs dropped
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('NQNMQS PDR PWR PMR_TV', 'price');
const myShowDay = input.boolean('Show PDH PDL EQ', true);
const myShowWeek = input.boolean('Show PWH PWL', true);
const myShowMonth = input.boolean('Show PMH PML', true);
const myShowLabels = input.boolean('Show Labels', true);
const myN = close.length;
const myT = time.map(_t => time_of(_t));
// previous completed day / week / month high and low from the chart bars, in exchange time
const myTrack = (_isNew) => {
	let myH = null, myL = null, myPh = null, myPl = null;
	const myPhs = [], myPls = [];
	for (let myI = 0; myI < myN; myI += 1) {
		if (myI > 0 && _isNew(myI)) { myPh = myH; myPl = myL; myH = high[myI]; myL = low[myI]; }
		else { myH = myH === null ? high[myI] : Math.max(myH, high[myI]); myL = myL === null ? low[myI] : Math.min(myL, low[myI]); }
		myPhs.push(myPh); myPls.push(myPl);
	}
	return { h: myPhs, l: myPls };
};
const myDay = myTrack(_i => myT[_i].dayOfMonth !== myT[_i - 1].dayOfMonth || myT[_i].month !== myT[_i - 1].month || myT[_i].year !== myT[_i - 1].year);
const myWeek = myTrack(_i => myT[_i].dayOfWeek < myT[_i - 1].dayOfWeek || (time[_i] - time[_i - 1]) > 6 * 86400);
const myMonth = myTrack(_i => myT[_i].month !== myT[_i - 1].month || myT[_i].year !== myT[_i - 1].year);
const myEq = myDay.h.map((_h, _i) => (_h === null || myDay.l[_i] === null) ? null : (_h + myDay.l[_i]) / 2);
const myGate = (_s, _f) => _f ? _s : _s.map(() => null);
const myPdh = paint(myGate(myDay.h, myShowDay), { name: 'PDH', color: '#2962FF' });
const myPdl = paint(myGate(myDay.l, myShowDay), { name: 'PDL', color: '#D50000' });
const myEqP = paint(myGate(myEq, myShowDay), { name: 'EQ', color: '#9E9E9E', style: 'dotted', marker: 'circle' });
const myPwh = paint(myGate(myWeek.h, myShowWeek), { name: 'PWH', color: '#00897B' });
const myPwl = paint(myGate(myWeek.l, myShowWeek), { name: 'PWL', color: '#F4511E' });
const myPmh = paint(myGate(myMonth.h, myShowMonth), { name: 'PMH', color: '#6A1B9A' });
const myPml = paint(myGate(myMonth.l, myShowMonth), { name: 'PML', color: '#F9A825' });
const myLast = myN - 1;
if (myShowLabels) {
	const myLab = (_p, _v, _n, _c, _on) => { if (_on && _v !== null) paint_label_at_line(_p, myLast, _n + ' ' + _v.toFixed(2), { color: _c }); };
	myLab(myPdh, myDay.h[myLast], 'PDH', '#2962FF', myShowDay);
	myLab(myPdl, myDay.l[myLast], 'PDL', '#D50000', myShowDay);
	myLab(myEqP, myEq[myLast], 'EQ', '#9E9E9E', myShowDay);
	myLab(myPwh, myWeek.h[myLast], 'PWH', '#00897B', myShowWeek);
	myLab(myPwl, myWeek.l[myLast], 'PWL', '#F4511E', myShowWeek);
	myLab(myPmh, myMonth.h[myLast], 'PMH', '#6A1B9A', myShowMonth);
	myLab(myPml, myMonth.l[myLast], 'PML', '#F9A825', myShowMonth);
}
const myXUp = (_lvl) => close.map((_c, _i) => _i > 0 && _lvl[_i] !== null && _lvl[_i - 1] !== null && close[_i - 1] <= _lvl[_i - 1] && _c > _lvl[_i]);
const myXDn = (_lvl) => close.map((_c, _i) => _i > 0 && _lvl[_i] !== null && _lvl[_i - 1] !== null && close[_i - 1] >= _lvl[_i - 1] && _c < _lvl[_i]);
register_signal(myXUp(myDay.h), 'Cross Above PDH');
register_signal(myXDn(myDay.l), 'Cross Below PDL');
register_signal(myXUp(myWeek.h), 'Cross Above PWH');
register_signal(myXDn(myWeek.l), 'Cross Below PWL');
register_signal(myXUp(myMonth.h), 'Cross Above PMH');
register_signal(myXDn(myMonth.l), 'Cross Below PML');
