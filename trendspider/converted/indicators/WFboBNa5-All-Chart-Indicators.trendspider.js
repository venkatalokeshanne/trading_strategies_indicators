/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : All Chart Indicators
 * Author       : subhashksagar76
 * Source URL   : https://www.tradingview.com/script/WFboBNa5-All-Chart-Indicators
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : All Chart Indicators Overlay_TV
 *
 * Deviations from the original: Pine supertrend hand-rolled; pivots from previous completed higher-timeframe bar,
 *   lagged one bar; forceUsePriceAxis dropped
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('All Chart Indicators Overlay_TV', 'price');
const myAtrLen1 = input.number('ST 1 ATR Length', 44, { min: 1, max: 500 });
const myFactor1 = input.number('ST 1 Multiplier', 4.4, { min: 0.1, max: 20, step: 0.1 });
const myAtrLen2 = input.number('ST 2 ATR Length', 44, { min: 1, max: 500 });
const myFactor2 = input.number('ST 2 Multiplier', 5.0, { min: 0.1, max: 20, step: 0.1 });
const myPivotSrc = input.select('Pivot Timeframe', 'Daily', ['Daily', 'Weekly', 'Monthly']);
const myN = close.length;
// ta.supertrend(factor, atrLen): Pine reference algorithm (direction -1 = up-trend); this script's own colouring treats dir == 1 as green
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const mySuper = (_len, _factor) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	const myAtr = myTr.map(_v => { if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _len) myAcc = mySeed / _len; return myAcc; } myAcc = (myAcc * (_len - 1) + _v) / _len; return myAcc; });
	const myLine = [], myDir = [];
	let myUpper = null, myLower = null, myPrevSt = null;
	for (let myI = 0; myI < myN; myI += 1) {
		if (myAtr[myI] === null) { myLine.push(null); myDir.push(null); continue; }
		const myHl2 = (high[myI] + low[myI]) / 2;
		let myUp = myHl2 + _factor * myAtr[myI], myLo = myHl2 - _factor * myAtr[myI];
		const myPUp = myUpper, myPLo = myLower;
		myLo = (myPLo === null || myLo > myPLo || close[myI - 1] < myPLo) ? myLo : myPLo;
		myUp = (myPUp === null || myUp < myPUp || close[myI - 1] > myPUp) ? myUp : myPUp;
		let myD;
		if (myPrevSt === null) myD = 1;
		else if (myPrevSt === myPUp) myD = close[myI] > myUp ? -1 : 1;
		else myD = close[myI] < myLo ? 1 : -1;
		const mySt = myD === -1 ? myLo : myUp;
		myUpper = myUp; myLower = myLo; myPrevSt = mySt;
		myLine.push(mySt); myDir.push(myD);
	}
	return { line: myLine, dir: myDir };
};
const myS1 = mySuper(myAtrLen1, myFactor1), myS2 = mySuper(myAtrLen2, myFactor2);
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
let mySV = 0, myV = 0;
const myVwap = close.map((_c, _i) => { if (_i === 0 || myDayKey[_i] !== myDayKey[_i - 1]) { mySV = 0; myV = 0; } mySV += (high[_i] + low[_i] + _c) / 3 * volume[_i]; myV += volume[_i]; return myV > 0 ? mySV / myV : null; });
const myRes = myPivotSrc === 'Daily' ? 'D' : (myPivotSrc === 'Weekly' ? 'W' : 'M');
const myHtf = await request.history(current.ticker, myRes);
assert(!myHtf.error, 'Error fetching pivot timeframe data: ' + myHtf.error);
// classic pivots from the previous completed higher-timeframe bar (the Pine only updates them when a pivot high and low coincide)
const myLevel = (_f) => interpolate_sparse_series(land_points_onto_series(myHtf.time, myHtf.close.map((_c, _k) => {
	if (_k === 0) return null;
	const myH = myHtf.high[_k - 1], myL = myHtf.low[_k - 1], myC = myHtf.close[_k - 1];
	return _f((myH + myL + myC) / 3, myH, myL);
}), time, 'le'), 'constant');
paint(myS1.line, { name: 'ST1 44 4.4', color: myS1.dir.map(_d => _d === 1 ? 'green' : 'red'), thickness: 2 });
paint(myS2.line, { name: 'ST2 44 5', color: myS2.dir.map(_d => _d === 1 ? 'blue' : 'orange'), thickness: 2 });
paint(myVwap, { name: 'VWAP', color: 'blue', thickness: 2 });
paint(myLevel((_p) => _p), { name: 'PP', color: 'gray', style: 'dotted', marker: 'circle' });
paint(myLevel((_p, _h, _l) => 2 * _p - _l), { name: 'R1', color: 'red' });
paint(myLevel((_p, _h, _l) => 2 * _p - _h), { name: 'S1', color: 'green' });
paint(myLevel((_p, _h, _l) => _p + (_h - _l)), { name: 'R2', color: 'rgba(239,83,80,0.6)' });
paint(myLevel((_p, _h, _l) => _p - (_h - _l)), { name: 'S2', color: 'rgba(38,166,154,0.6)' });
paint(myLevel((_p, _h, _l) => _h + 2 * (_p - _l)), { name: 'R3', color: 'rgba(239,83,80,0.4)' });
paint(myLevel((_p, _h, _l) => _l - 2 * (_h - _p)), { name: 'S3', color: 'rgba(38,166,154,0.4)' });
register_signal(myS1.dir.map(_d => _d === 1), 'Supertrend 1 Dir 1');
register_signal(myS2.dir.map(_d => _d === 1), 'Supertrend 2 Dir 1');
