/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RSI + Williams Vix Fix
 * Author       : giangsofa
 * Source URL   : https://www.tradingview.com/script/0ONS5Opr
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RSI plus Williams Vix Fix_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI; population stdev and window highs/lows
 *   hand-rolled; WVF histogram plotted from zero (histbase not available); fill as
 *   cloud; colour/width inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RSI plus Williams Vix Fix_TV', 'lower');
const myRsiTab = input.tab('RSI');
const myRsiLength = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const mySrcName = myRsiTab.select('RSI Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myOverbought = myRsiTab.number('Overbought', 70, { min: 1, max: 100 });
const myOversold = myRsiTab.number('Oversold', 30, { min: 0, max: 99 });
const myWvfTab = input.tab('Williams Vix Fix');
const myPd = myWvfTab.number('StDev Lookback', 22, { min: 1, max: 500 });
const myBbl = myWvfTab.number('BB Length', 20, { min: 1, max: 500 });
const myMult = myWvfTab.number('BB StDev Mult', 2, { min: 1, max: 5 });
const myLb = myWvfTab.number('Percentile Lookback', 50, { min: 1, max: 500 });
const myPh = myWvfTab.number('Highest Percentile', 0.85, { min: 0, max: 5 });
const myPl = myWvfTab.number('Lowest Percentile', 1.01, { min: 0, max: 5 });
const myShowPct = myWvfTab.boolean('Show Pctile Lines', false);
const myShowSd = myWvfTab.boolean('Show StDev Line', false);
const myZoneBottom = myWvfTab.number('WVF Zone Bottom', 40, { min: 0, max: 100 });
const myZoneTop = myWvfTab.number('WVF Zone Top', 60, { min: 0, max: 100 });
const myDynNorm = myWvfTab.boolean('Auto Normalize WVF', true);
const myDynLb = myWvfTab.number('Normalize Lookback', 100, { min: 10, max: 1000 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(_v - mySrc[_i - 1], 0)), myRsiLength);
const myL = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(mySrc[_i - 1] - _v, 0)), myRsiLength);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
// window helpers over valid values (null until the window is full)
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
const myHighClose = myMax(close, myPd);
const myWvf = close.map((_c, _i) => myHighClose[_i] === null ? null : ((myHighClose[_i] - low[_i]) / myHighClose[_i]) * 100);
const myMid = mySma(myWvf, myBbl);
const mySd = myStdev(myWvf, myBbl);
const myUpper = myWvf.map((_v, _i) => (myMid[_i] === null || mySd[_i] === null) ? null : myMid[_i] + myMult * mySd[_i]);
const myRangeHigh = myMax(myWvf, myLb).map(_v => _v === null ? null : _v * myPh);
const myRangeLow = myMin(myWvf, myLb).map(_v => _v === null ? null : _v * myPl);
const mySignal = myWvf.map((_v, _i) => _v !== null && ((myUpper[_i] !== null && _v >= myUpper[_i]) || (myRangeHigh[_i] !== null && _v >= myRangeHigh[_i])));
const myWvfMin = myMin(myWvf, myDynLb);
const myWvfMax = myMax(myWvf, myDynLb);
const myNorm = myWvf.map((_v, _i) => {
	if (_v === null) return null;
	if (!myDynNorm) return _v;
	if (myWvfMin[_i] === null || myWvfMax[_i] === null) return null;
	return myWvfMax[_i] > myWvfMin[_i] ? (_v - myWvfMin[_i]) / (myWvfMax[_i] - myWvfMin[_i]) * 100 : 0;
});
const myScale = (myZoneTop - myZoneBottom) / 100.0;
const myZone = (_s) => _s.map(_v => _v === null ? null : myZoneBottom + _v * myScale);
paint(myRsi, { name: 'RSI', color: '#2962FF', thickness: 2 });
paint(horizontal_line(myOverbought), { name: 'Overbought', color: '#787B86' });
paint(horizontal_line(50), { name: 'Middle', color: 'rgba(120,123,134,0.5)' });
paint(horizontal_line(myOversold), { name: 'Oversold', color: '#787B86' });
color_cloud(horizontal_line(myOverbought), horizontal_line(myOversold), 'rgba(33,150,243,0.1)', 'rgba(33,150,243,0.1)', 'RSI Back Up', 'RSI Back Dn');
paint(myShowPct ? myZone(myRangeHigh) : close.map(() => null), { name: 'Range High Percentile', color: 'orange', thickness: 2 });
paint(myShowPct ? myZone(myRangeLow) : close.map(() => null), { name: 'Range Low Percentile', color: 'orange', thickness: 2 });
paint(myZone(myNorm), { name: 'Williams Vix Fix', style: 'histogram', color: mySignal.map(_s => _s ? 'lime' : 'gray'), thickness: 4 });
paint(myShowSd ? myZone(myUpper) : close.map(() => null), { name: 'Upper Band StdDev', color: 'aqua', thickness: 2 });
register_signal(myRsi.map(_r => _r !== null && _r >= myOverbought), 'RSI Overbought');
register_signal(myRsi.map(_r => _r !== null && _r <= myOversold), 'RSI Oversold');
register_signal(mySignal, 'Williams Vix Fix Triggered');
