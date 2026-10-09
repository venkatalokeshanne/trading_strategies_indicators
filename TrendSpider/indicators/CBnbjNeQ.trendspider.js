/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 出来高＋値幅収縮スキャナー V3
 * Author       : LeaderLab
 * Source URL   : https://www.tradingview.com/script/CBnbjNeQ
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Volume Range Contraction Scanner V3_TV
 *
 * Deviations from the original: Pine screener table/inputs groups replaced by plots and signals; null-aware windows
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Volume Range Contraction Scanner V3_TV', 'lower');
const myShortVolLen = input.number('Short Vol Avg', 10, { min: 1, max: 200 });
const myLongVolLen = input.number('Long Vol Avg', 50, { min: 1, max: 300 });
const myVolRatioMax = input.number('Volume Ratio Max', 0.70, { min: 0.01, max: 5, step: 0.01 });
const myRangeLen = input.number('Range Period', 10, { min: 1, max: 200 });
const myRangeMaxPct = input.number('Max Range %', 10.0, { min: 0.1, max: 100, step: 0.1 });
const myCompareBars = input.number('Range Compare Bars', 20, { min: 1, max: 300 });
const myNewHighLookback = input.number('New High Lookback', 40, { min: 1, max: 300 });
const myYearBars = input.number('Year Bars', 252, { min: 10, max: 500 });
const myN = close.length;
const myWin = (_s, _n, _f) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	const myW = [];
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myW.push(_s[myK]); }
	return _f(myW);
});
const mySma = (_s, _n) => myWin(_s, _n, _w => _w.reduce((_a, _b) => _a + _b, 0) / _n);
const myShort = mySma(volume, myShortVolLen), myLong = mySma(volume, myLongVolLen);
const myVolRatio = myShort.map((_s, _i) => (_s === null || myLong[_i] === null || myLong[_i] <= 0) ? null : _s / myLong[_i]);
const myDry = myVolRatio.map(_r => _r !== null && _r <= myVolRatioMax);
const myRangeHigh = myWin(high, myRangeLen, _w => Math.max(..._w)), myRangeLow = myWin(low, myRangeLen, _w => Math.min(..._w));
const myRangePct = close.map((_c, _i) => (myRangeHigh[_i] === null || myRangeLow[_i] === null) ? null : (myRangeHigh[_i] - myRangeLow[_i]) / _c * 100);
const myTight = myRangePct.map(_p => _p !== null && _p <= myRangeMaxPct);
const myContracting = myRangePct.map((_p, _i) => _i >= myCompareBars && _p !== null && myRangePct[_i - myCompareBars] !== null && _p < myRangePct[_i - myCompareBars]);
// highest(high[1], yearBars): highest of the previous yearBars highs
const myPrev52 = close.map((_c, _i) => {
	if (_i < myYearBars) return null;
	let myM = -Infinity;
	for (let myK = _i - myYearBars; myK < _i; myK += 1) myM = Math.max(myM, high[myK]);
	return myM;
});
const myNewHigh = close.map((_c, _i) => myPrev52[_i] !== null && high[_i] > myPrev52[_i]);
const myRecent = myNewHigh.map((_v, _i) => { if (_i < myNewHighLookback - 1) return false; for (let myK = _i - myNewHighLookback + 1; myK <= _i; myK += 1) if (myNewHigh[myK]) return true; return false; });
let mySince = null;
const myBarsSince = myNewHigh.map(_h => { mySince = _h ? 0 : (mySince === null ? null : mySince + 1); return mySince; });
const myMa200 = mySma(close, 200), myMa50 = mySma(close, 50);
const mySlope = myMa200.map((_m, _i) => (_i < 20 || _m === null || myMa200[_i - 20] === null || myMa200[_i - 20] === 0) ? null : (_m - myMa200[_i - 20]) / myMa200[_i - 20] * 100);
const mySlopeOk = mySlope.map(_s => _s !== null && _s >= 1.0);
const myRising = myMa200.map((_m, _i) => _i >= 20 && [0, 5, 10, 15, 20].every(_k => myMa200[_i - _k] !== null) && myMa200[_i] > myMa200[_i - 5] && myMa200[_i - 5] > myMa200[_i - 10] && myMa200[_i - 10] > myMa200[_i - 15] && myMa200[_i - 15] > myMa200[_i - 20]);
const myAbove50 = close.map((_c, _i) => myMa50[_i] !== null && _c > myMa50[_i]);
const myAbove200 = close.map((_c, _i) => myMa200[_i] !== null && _c > myMa200[_i]);
const myMatch = close.map((_c, _i) => myDry[_i] && myTight[_i] && myContracting[_i] && myRecent[_i] && mySlopeOk[_i] && myRising[_i] && myAbove50[_i] && myAbove200[_i]);
const myB = (_a) => _a.map(_v => _v ? 1 : 0);
paint(myVolRatio, { name: 'Volume Ratio 10D 50D', color: '#4DA3FF' });
paint(myRangePct, { name: 'Range Pct 10D', color: '#EF5350' });
paint(myB(myTight), { name: 'Tight Flag', color: '#26A69A' });
paint(myB(myContracting), { name: 'Contracting Flag', color: '#AB47BC' });
paint(myB(myRecent), { name: 'Recent 52W High', color: '#FFA726' });
paint(myBarsSince, { name: 'Days Since 52W High', color: '#78909C' });
paint(mySlope, { name: 'MA200 Slope Pct', color: '#26C6DA' });
paint(myB(myRising), { name: 'MA200 Rise Flag', color: '#9CCC65' });
paint(myB(myAbove50), { name: 'Above MA50', color: '#FFD54F' });
paint(myB(myAbove200), { name: 'Above MA200', color: '#FF8A65' });
paint(myB(myMatch), { name: 'Scanner', style: 'histogram', color: '#00E676' });
register_signal(myDry, 'Volume Dry Up');
register_signal(myTight, 'Range Tight');
register_signal(myContracting, 'Range Contracting');
register_signal(myRecent, 'Recent 52 Week High');
register_signal(mySlopeOk, 'MA200 Slope OK');
register_signal(myRising, 'MA200 Rising');
register_signal(myMatch, 'Scanner Match');
