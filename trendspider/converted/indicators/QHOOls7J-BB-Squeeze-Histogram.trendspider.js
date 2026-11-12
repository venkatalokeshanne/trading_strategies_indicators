/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BB Squeeze Histogram
 * Author       : Options360
 * Source URL   : https://www.tradingview.com/script/QHOOls7J-BB-Squeeze-Histogram
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BB Squeeze Histogram_TV
 *
 * Deviations from the original: Reviewed AI draft; all MA types, population stdev, percentrank and ALMA hand-rolled
 *   (VWAP type equals the source as in the Pine call); histogram plotted from zero
 *   (histbase not available).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BB Squeeze Histogram_TV', 'lower');
const mySrcName = input.select('Source', 'ohlc4', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myLength = input.number('Length', 20, { min: 1, max: 500 });
const myMult = input.number('Band SD', 3.0, { min: 0.001, max: 50 });
const myOffset = input.number('ALMA offset', 0.89, { min: 0, max: 1, step: 0.01 });
const mySigma = input.number('ALMA sigma', 5, { min: 1, max: 50 });
const myNormalize = input.boolean('Normalize 0-100', false);
const myNormLen = input.number('Normalize lookback', 200, { min: 10, max: 2000 });
const mySqueezeLen = input.number('Squeeze lookback', 100, { min: 10, max: 2000 });
const myAvgLen = input.number('Column avg lookback', 100, { min: 10, max: 2000 });
const myMaType = input.select('MA Type', 'VWMA', ['SMA', 'EMA', 'RMA', 'WMA', 'VWMA', 'VWAP', 'HMA', 'SWMA', 'ALMA']);
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myWin = (_s, _n, _f) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	const myW = [];
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myW.push(_s[myK]); }
	return _f(myW, _i);
});
const mySum = (_w) => _w.reduce((_a, _b) => _a + _b, 0);
const mySma = (_s, _n) => myWin(_s, _n, _w => mySum(_w) / _n);
const myWma = (_s, _n) => myWin(_s, _n, _w => _w.reduce((_a, _b, _k) => _a + _b * (_k + 1), 0) / (_n * (_n + 1) / 2));
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySm = 0; const myA = 2 / (_n + 1); return _s.map(_v => { if (_v === null) return null; if (myAcc === null) { mySm += _v; myCnt += 1; if (myCnt === _n) myAcc = mySm / _n; return myAcc; } myAcc = myA * _v + (1 - myA) * myAcc; return myAcc; }); };
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySm = 0; return _s.map(_v => { if (_v === null) return myAcc; if (myAcc === null) { mySm += _v; myCnt += 1; if (myCnt === _n) myAcc = mySm / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
const myVwma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myNum = 0, myDen = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) { myNum += _s[myK] * volume[myK]; myDen += volume[myK]; } return myDen === 0 ? null : myNum / myDen; });
let myBasis;
if (myMaType === 'SMA') myBasis = mySma(mySrc, myLength);
else if (myMaType === 'EMA') myBasis = myEma(mySrc, myLength);
else if (myMaType === 'RMA') myBasis = myRma(mySrc, myLength);
else if (myMaType === 'WMA') myBasis = myWma(mySrc, myLength);
else if (myMaType === 'VWMA') myBasis = myVwma(mySrc, myLength);
else if (myMaType === 'VWAP') myBasis = mySrc.slice(); // ta.vwap(src, bool(length)) anchors on every bar, so it equals the source
else if (myMaType === 'HMA') {
	const myHalf = myWma(mySrc, Math.max(1, Math.floor(myLength / 2)));
	const myFull = myWma(mySrc, myLength);
	const myRaw = myHalf.map((_h, _i) => (_h === null || myFull[_i] === null) ? null : 2 * _h - myFull[_i]);
	myBasis = myWma(myRaw, Math.max(1, Math.round(Math.sqrt(myLength))));
}
else if (myMaType === 'SWMA') myBasis = mySrc.map((_v, _i) => _i < 3 ? null : (mySrc[_i - 3] + 2 * mySrc[_i - 2] + 2 * mySrc[_i - 1] + _v) / 6);
else {
	const myM = Math.floor(myOffset * (myLength - 1));
	const myS = myLength / mySigma;
	const myWts = [];
	for (let myK = 0; myK < myLength; myK += 1) myWts.push(Math.exp(-((myK - myM) * (myK - myM)) / (2 * myS * myS)));
	const myNorm = mySum(myWts);
	myBasis = myWin(mySrc, myLength, _w => _w.reduce((_a, _b, _k) => _a + _b * myWts[_k], 0) / myNorm);
}
const myDev = myWin(mySrc, myLength, _w => { const myMean = mySum(_w) / myLength; return Math.sqrt(_w.reduce((_a, _b) => _a + (_b - myMean) * (_b - myMean), 0) / myLength); });
const myWidth = myDev.map(_d => _d === null ? null : 2 * myMult * _d);
const myRank = myWidth.map((_v, _i) => {
	if (_i < myNormLen || _v === null) return null;
	let myC = 0;
	for (let myK = 1; myK <= myNormLen; myK += 1) { const myV = myWidth[_i - myK]; if (myV === null) return null; if (myV <= _v) myC += 1; }
	return myC / myNormLen * 100;
});
const myNeutral = myNormalize ? 50 : 0;
const myAbove = mySrc.map((_s, _i) => myBasis[_i] !== null && _s >= myBasis[_i]);
const myHist = myWidth.map((_w, _i) => {
	const myMag = myNormalize ? (myRank[_i] === null ? null : myRank[_i] / 2) : _w;
	if (myMag === null) return null;
	return myAbove[_i] ? myNeutral + myMag : myNeutral - myMag;
});
const myColor = myHist.map((_h, _i) => {
	if (_h === null) return 'gray';
	const myExp = _i === 0 || myWidth[_i - 1] === null || myWidth[_i] >= myWidth[_i - 1];
	return myAbove[_i] ? (myExp ? '#26a69a' : '#b2dfdb') : (myExp ? '#ff5252' : '#ffcdd2');
});
paint(myHist, { name: 'BB Width Histogram', style: 'histogram', color: myColor });
paint(close.map(() => myNeutral), { name: 'Neutral', color: 'rgba(128,128,128,0.5)' });
paint(close.map(() => myNormalize ? 100 : null), { name: 'Top 100', color: 'rgba(128,128,128,0.3)' });
paint(close.map(() => myNormalize ? 0 : null), { name: 'Bottom 0', color: 'rgba(128,128,128,0.3)' });
const myPosVal = myHist.map((_h, _i) => (_h !== null && myAbove[_i]) ? _h : 0);
const myPosCnt = myHist.map((_h, _i) => (_h !== null && myAbove[_i]) ? 1 : 0);
const myNegVal = myHist.map((_h, _i) => (_h !== null && !myAbove[_i]) ? _h : 0);
const myNegCnt = myHist.map((_h, _i) => (_h !== null && !myAbove[_i]) ? 1 : 0);
const myRoll = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myT = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) myT += _s[myK]; return myT; });
const mySPv = myRoll(myPosVal, myAvgLen), mySPc = myRoll(myPosCnt, myAvgLen), mySNv = myRoll(myNegVal, myAvgLen), mySNc = myRoll(myNegCnt, myAvgLen);
paint(mySPv.map((_v, _i) => _v === null ? null : _v / Math.max(mySPc[_i], 1)), { name: 'Avg Positive Column', color: '#ff0202', thickness: 1 });
paint(mySNv.map((_v, _i) => _v === null ? null : _v / Math.max(mySNc[_i], 1)), { name: 'Avg Negative Column', color: '#3cfe12', thickness: 1 });
const myLowW = myWin(myWidth, mySqueezeLen, _w => Math.min(..._w));
const mySqueeze = myWidth.map((_w, _i) => _w !== null && myLowW[_i] !== null && _w === myLowW[_i]);
paint(mySqueeze.map(_s => _s ? myNeutral : null), { name: 'Squeeze', style: 'dotted', marker: 'circle', color: 'yellow' });
register_signal(myAbove, 'Price Above Basis');
register_signal(mySqueeze, 'In Squeeze');
register_signal(myWidth.map((_w, _i) => _w !== null && _i > 0 && myWidth[_i - 1] !== null && _w >= myWidth[_i - 1]), 'Band Width Expanding');
