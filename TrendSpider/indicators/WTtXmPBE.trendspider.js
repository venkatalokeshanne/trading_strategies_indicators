/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Volume Exhaustion Trend Line
 * Author       : BullBearSR
 * Source URL   : https://www.tradingview.com/script/WTtXmPBE
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Volume Exhaustion Trend Line_TV
 *
 * Deviations from the original: Pivots hand-rolled (ties allowed); line holds last value when trend is none as in
 *   Pine var; fill via color_cloud between line and close
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Volume Exhaustion Trend Line_TV', 'price');
const myLeft = input.number('Left Bars', 20, { min: 1, max: 200 });
const myRight = input.number('Right Bars', 1, { min: 1, max: 50 });
const myVolLen = input.number('Volume MA Length', 20, { min: 1, max: 300 });
const myMaLen = input.number('Line MA Length', 20, { min: 1, max: 300 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 300 });
const myAtrMult = input.number('ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myN = close.length;
const mySma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) myS += _s[myK]; return myS / _n; });
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, myCnt = 0, mySeed = 0;
const myAtr = myTr.map(_v => { if (myAcc === null) { mySeed += _v; myCnt += 1; if (myCnt === myAtrLen) myAcc = mySeed / myAtrLen; return myAcc; } myAcc = (myAcc * (myAtrLen - 1) + _v) / myAtrLen; return myAcc; });
const myVolMa = mySma(volume, myVolLen), myBasis = mySma(close, myMaLen);
// ta.pivothigh / ta.pivotlow: the pivot bar is `right` bars back and is confirmed on the current bar
const myPivot = (_arr, _isHigh, _i) => {
	const myP = _i - myRight;
	if (myP - myLeft < 0) return null;
	for (let myK = myP - myLeft; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? _arr[myK] > _arr[myP] : _arr[myK] < _arr[myP]) return null;
	}
	return _arr[myP];
};
let myLastHigh = null, myPrevHigh = null, myLastLow = null, myPrevLow = null, myTrend = 'none';
let myHighStrong = false, myLowStrong = false, myHasHigh = false, myHasLow = false, myPendUp = false, myPendDn = false, myLine = null;
const myLineS = [], myTrendS = [], myPendUpS = [], myPendDnS = [];
const myApply = () => {
	if (myPrevHigh !== null && myLastHigh !== null && myPrevLow !== null && myLastLow !== null) {
		let myNew = 'none';
		if (myLastHigh > myPrevHigh && myLastLow > myPrevLow) myNew = 'up';
		else if (myLastHigh < myPrevHigh && myLastLow < myPrevLow) myNew = 'down';
		if (myNew !== 'up') myPendUp = false;
		if (myNew !== 'down') myPendDn = false;
		myTrend = myNew;
	}
};
for (let myI = 0; myI < myN; myI += 1) {
	const myPh = myPivot(high, true, myI), myPl = myPivot(low, false, myI);
	const myWeak = (myI - myRight >= 0 && myVolMa[myI - myRight] !== null) ? volume[myI - myRight] < myVolMa[myI - myRight] : false;
	if (myPh !== null) {
		if (myTrend === 'up') { if (myWeak) { if (myPendUp || (myHasHigh && myHighStrong)) myPendUp = true; } else myPendUp = false; } else myPendUp = false;
		myHighStrong = !myWeak; myHasHigh = true; myPrevHigh = myLastHigh; myLastHigh = myPh;
		if (myPrevHigh !== null && myLastLow !== null && myPrevLow !== null) myApply();
	}
	if (myPl !== null) {
		if (myTrend === 'down') { if (myWeak) { if (myPendDn || (myHasLow && myLowStrong)) myPendDn = true; } else myPendDn = false; } else myPendDn = false;
		myLowStrong = !myWeak; myHasLow = true; myPrevLow = myLastLow; myLastLow = myPl;
		if (myPrevHigh !== null && myLastHigh !== null && myPrevLow !== null) myApply();
	}
	if (myBasis[myI] !== null && myAtr[myI] !== null) {
		const myUp = myBasis[myI] + myAtrMult * myAtr[myI], myLo = myBasis[myI] - myAtrMult * myAtr[myI];
		if (myTrend === 'up') myLine = myPendUp ? myUp : myLo;
		else if (myTrend === 'down') myLine = myPendDn ? myLo : myUp;
	}
	myLineS.push(myLine); myTrendS.push(myTrend); myPendUpS.push(myPendUp); myPendDnS.push(myPendDn);
}
const myBull = close.map((_c, _i) => myLineS[_i] !== null && myLineS[_i] < _c);
const myBear = close.map((_c, _i) => myLineS[_i] !== null && myLineS[_i] >= _c);
paint(myLineS, { name: 'Volume Exhaustion Line', color: myLineS.map((_v, _i) => _v === null ? 'gray' : (myBull[_i] ? '#00e676' : '#ff5252')), thickness: 2 });
// the Pine fills between the line and the close, green when the line is below price, red when above
color_cloud(close.map((_c, _i) => myLineS[_i] === null ? null : _c), myLineS, 'rgba(0,230,118,0.15)', 'rgba(255,82,82,0.15)', 'Close Above Line', 'Close Below Line');
register_signal(myBull, 'Bullish Line Below Price');
register_signal(myBear, 'Bearish Line Above Price');
register_signal(myTrendS.map(_t => _t === 'up'), 'Trend Up');
register_signal(myTrendS.map(_t => _t === 'down'), 'Trend Down');
register_signal(myPendUpS, 'Pending Exhaustion Up');
register_signal(myPendDnS, 'Pending Exhaustion Down');
