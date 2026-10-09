/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Custom Cumulative Volume Delta (CVD) - Upstox Style
 * Author       : sarath1128
 * Source URL   : https://www.tradingview.com/script/FdCD7dRm-Custom-Cumulative-Volume-Delta-CVD-EMA-DIVERGENCE
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : CVD Upstox Style_TV
 *
 * Deviations from the original: CVD candles drawn as close line (coloured) plus dotted open line; Session reset is
 *   2-hour UTC blocks; divergence circles drawn on the pivot bar
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('CVD Upstox Style_TV', 'lower');
const myResetMode = input.select('CVD Reset Anchor', 'Daily', ['Daily', 'Session', 'Never']);
const myMaLen = input.number('Signal MA Length', 21, { min: 1, max: 500 });
const myMaType = input.select('Signal MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const myShowDiv = input.boolean('Show Divergences', true);
const myN = close.length;
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.year * 10000 + myX.month * 100 + myX.dayOfMonth; });
const myBlock = time.map(_t => Math.floor(_t / 7200));
const myCvdOpen = [], myCvdHigh = [], myCvdLow = [], myCvdClose = [];
let myPrevClose = 0;
for (let myI = 0; myI < myN; myI += 1) {
	const myRange = high[myI] - low[myI];
	const myEff = myRange === 0 ? 0 : (close[myI] - open[myI]) / myRange;
	const myVw = volume[myI] * Math.abs(myEff);
	let myDelta;
	if (close[myI] > open[myI]) myDelta = myVw + volume[myI] * 0.1;
	else if (close[myI] < open[myI]) myDelta = -myVw - volume[myI] * 0.1;
	else myDelta = myRange === 0 ? 0 : volume[myI] * ((close[myI] - low[myI]) / myRange - 0.5);
	const myReset = myI > 0 && ((myResetMode === 'Daily' && myDayKey[myI] !== myDayKey[myI - 1]) || (myResetMode === 'Session' && myBlock[myI] !== myBlock[myI - 1]));
	let myO, myC, myH, myL;
	if (myReset) { myO = 0; myC = myDelta; myH = Math.max(0, myDelta); myL = Math.min(0, myDelta); }
	else { myO = myPrevClose; myC = myO + myDelta; myH = Math.max(myO, myC); myL = Math.min(myO, myC); }
	myCvdOpen.push(myO); myCvdClose.push(myC); myCvdHigh.push(myH); myCvdLow.push(myL);
	myPrevClose = myC;
}
const mySmaA = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) myS += _s[myK]; return myS / _n; });
const myEmaA = (_s, _n) => { let myAcc = null; const myK = 2 / (_n + 1); return _s.map((_v, _i) => { if (_i < _n - 1) return null; if (myAcc === null) { myAcc = mySmaA(_s, _n)[_i]; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myWmaA = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = 0; myK < _n; myK += 1) myS += _s[_i - myK] * (_n - myK); return myS / (_n * (_n + 1) / 2); });
const mySignalMa = myMaType === 'EMA' ? myEmaA(myCvdClose, myMaLen) : (myMaType === 'WMA' ? myWmaA(myCvdClose, myMaLen) : mySmaA(myCvdClose, myMaLen));
// pivots with 5 left/5 right; the divergence is judged when a pivot is confirmed, against the previous confirmed pivot
const myLb = 5;
const myIsPivot = (_arr, _isHigh, _i) => { const myP = _i - myLb; if (myP - myLb < 0) return false; for (let myK = myP - myLb; myK <= _i; myK += 1) { if (myK === myP) continue; if (_isHigh ? _arr[myK] > _arr[myP] : _arr[myK] < _arr[myP]) return false; } return true; };
const myBear = close.map(() => false), myBull = close.map(() => false);
let myPrevPh = null, myPrevPl = null;
for (let myI = 0; myI < myN; myI += 1) {
	if (myIsPivot(high, true, myI)) {
		if (myShowDiv && myPrevPh !== null && high[myI - myLb] > high[myPrevPh - myLb] && myCvdClose[myI - myLb] < myCvdClose[myPrevPh - myLb]) myBear[myI] = true;
		myPrevPh = myI;
	}
	if (myIsPivot(low, false, myI)) {
		if (myShowDiv && myPrevPl !== null && low[myI - myLb] < low[myPrevPl - myLb] && myCvdClose[myI - myLb] > myCvdClose[myPrevPl - myLb]) myBull[myI] = true;
		myPrevPl = myI;
	}
}
// the Pine plots the circle on the pivot bar (offset -5); here it is drawn on that earlier bar
const myBullMark = close.map((_c, _i) => (_i + myLb < myN && myBull[_i + myLb]) ? myCvdLow[_i] : null);
const myBearMark = close.map((_c, _i) => (_i + myLb < myN && myBear[_i + myLb]) ? myCvdHigh[_i] : null);
paint(myCvdClose, { name: 'CVD Close', color: myCvdClose.map((_c, _i) => _c >= myCvdOpen[_i] ? '#26A69A' : '#EF5350'), thickness: 2 });
paint(myCvdOpen, { name: 'CVD Open', color: 'rgba(150,150,150,0.5)', style: 'dotted' });
paint(horizontal_line(0), { name: 'Zero Baseline', color: 'gray', style: 'dotted' });
paint(mySignalMa, { name: 'Signal MA Line', color: 'orange', thickness: 2 });
paint(myBullMark, { name: 'Bull Div Mark', color: 'green', style: 'dotted', marker: 'circle' });
paint(myBearMark, { name: 'Bear Div Mark', color: 'red', style: 'dotted', marker: 'circle' });
register_signal(myBull, 'Bullish CVD Divergence');
register_signal(myBear, 'Bearish CVD Divergence');
register_signal(myCvdClose.map((_c, _i) => _c >= myCvdOpen[_i]), 'CVD Candle Bullish');
register_signal(myCvdClose.map((_c, _i) => mySignalMa[_i] !== null && _c > mySignalMa[_i]), 'CVD Above Signal MA');
