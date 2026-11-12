/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Williams Vix Fix - Sợ Hãi & Hưng Phấn
 * Author       : giangsofa
 * Source URL   : https://www.tradingview.com/script/57LVPi6x
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Williams Vix Fix Fear Euphoria_TV
 *
 * Deviations from the original: Reviewed AI draft; population stdev and window highs/lows hand-rolled; histograms
 *   plotted from zero.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Williams Vix Fix Fear Euphoria_TV', 'lower');
const myPd = input.number('StDev Lookback', 22, { min: 1, max: 500 });
const myBbl = input.number('BB Length', 20, { min: 1, max: 500 });
const myMult = input.number('BB StDev Mult', 2.0, { min: 1, max: 5 });
const myLb = input.number('Percentile Lookback', 50, { min: 1, max: 500 });
const myPh = input.number('Highest Percentile', 0.85, { min: 0, max: 2, step: 0.01 });
const myPl = input.number('Lowest Percentile', 1.01, { min: 0, max: 2, step: 0.01 });
const myShowPct = input.boolean('Show Percentile Lines', false);
const myShowSd = input.boolean('Show StDev Lines', false);
const myBottomColor = input.color('Fear Color', 'lime');
const myTopColor = input.color('Euphoria Color', 'red');
const myWin = (_s, _n, _f) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	const myW = [];
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myW.push(_s[myK]); }
	return _f(myW);
});
const myMax = (_s, _n) => myWin(_s, _n, _w => Math.max(..._w));
const myMin = (_s, _n) => myWin(_s, _n, _w => Math.min(..._w));
const mySma = (_s, _n) => myWin(_s, _n, _w => _w.reduce((_a, _b) => _a + _b, 0) / _n);
const myStdev = (_s, _n) => myWin(_s, _n, _w => { const myM = _w.reduce((_a, _b) => _a + _b, 0) / _n; return Math.sqrt(_w.reduce((_a, _b) => _a + (_b - myM) * (_b - myM), 0) / _n); });
const myBuild = (_series) => {
	const myMid = mySma(_series, myBbl);
	const mySd = myStdev(_series, myBbl);
	const myUpper = _series.map((_v, _i) => (myMid[_i] === null || mySd[_i] === null) ? null : myMid[_i] + myMult * mySd[_i]);
	const myRangeHigh = myMax(_series, myLb).map(_v => _v === null ? null : _v * myPh);
	const mySignal = _series.map((_v, _i) => _v !== null && ((myUpper[_i] !== null && _v >= myUpper[_i]) || (myRangeHigh[_i] !== null && _v >= myRangeHigh[_i])));
	return { upper: myUpper, rangeHigh: myRangeHigh, signal: mySignal };
};
const myHighClose = myMax(close, myPd);
const myWvf = close.map((_c, _i) => myHighClose[_i] === null ? null : ((myHighClose[_i] - low[_i]) / myHighClose[_i]) * 100);
const myLowClose = myMin(close, myPd);
const myInv = close.map((_c, _i) => myLowClose[_i] === null ? null : ((high[_i] - myLowClose[_i]) / myLowClose[_i]) * 100);
const myFear = myBuild(myWvf);
const myEuph = myBuild(myInv);
const myNeg = (_s) => _s.map(_v => _v === null ? null : -_v);
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
paint(myWvf, { name: 'WVF Fear', style: 'histogram', color: myFear.signal.map(_s => _s ? myBottomColor : 'gray'), thickness: 4 });
paint(myNeg(myInv), { name: 'Inverse WVF Euphoria', style: 'histogram', color: myEuph.signal.map(_s => _s ? myTopColor : 'silver'), thickness: 4 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'rgba(0,0,0,0.5)' });
paint(myGate(myFear.rangeHigh, myShowPct), { name: 'Range High Fear', color: 'orange', thickness: 2 });
paint(myGate(myFear.upper, myShowSd), { name: 'Upper Band Fear', color: 'aqua', thickness: 2 });
paint(myGate(myNeg(myEuph.rangeHigh), myShowPct), { name: 'Range High Euphoria', color: 'orange', thickness: 2 });
paint(myGate(myNeg(myEuph.upper), myShowSd), { name: 'Upper Band Euphoria', color: 'aqua', thickness: 2 });
register_signal(myFear.signal, 'Fear Spike');
register_signal(myEuph.signal, 'Euphoria Spike');
