/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA RSI + Divergence
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/0XvCvqer-VASA-RSI-Divergence-vF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA RSI Plus Divergence_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI; pivots hand-rolled and confirmed right-bars later
 *   (signals on the confirmation bar, marks on the pivot bar as Pine labels); divergence
 *   lines drawn by linear interpolation; colour inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA RSI Plus Divergence_TV', 'lower');
const myRsiTab = input.tab('RSI');
const mySrcName = myRsiTab.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myLenR = myRsiTab.number('RSI length', 14, { min: 2 });
const myObLevel = myRsiTab.number('Overbought', 70, { min: 50, max: 100 });
const myOsLevel = myRsiTab.number('Oversold', 30, { min: 0, max: 50 });
const myDivTab = input.tab('Divergence');
const myLb = myDivTab.number('Pivot left bars', 5, { min: 1 });
const myRb = myDivTab.number('Pivot right bars', 5, { min: 1 });
const myRngMax = myDivTab.number('Max bars between', 60, { min: 5 });
const myDrawLn = myDivTab.boolean('Draw divergence line', true);
const myColUp = '#15803d';
const myColDn = '#b91c1c';
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
const myG = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(_v - mySrc[_i - 1], 0)), myLenR);
const myL = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(mySrc[_i - 1] - _v, 0)), myLenR);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
// ta.pivothigh/pivotlow(rsi, left, right): the pivot is confirmed `right` bars later (the signal bar)
const myPivotAt = (_i, _isHigh) => {
	const myP = _i - myRb;
	if (myP - myLb < 0 || myRsi[myP] === null) return false;
	for (let myK = myP - myLb; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (myRsi[myK] === null) return false;
		if (_isHigh ? (myK < myP ? !(myRsi[myP] > myRsi[myK]) : !(myRsi[myP] >= myRsi[myK])) : (myK < myP ? !(myRsi[myP] < myRsi[myK]) : !(myRsi[myP] <= myRsi[myK]))) return false;
	}
	return true;
};
const myBull = close.map(() => false);
const myBear = close.map(() => false);
const myBullMark = close.map(() => null);
const myBearMark = close.map(() => null);
const myBullLine = close.map(() => null);
const myBearLine = close.map(() => null);
let myPrevLow = null, myPrevHigh = null;
for (let myI = 0; myI < close.length; myI += 1) {
	const myP = myI - myRb;
	if (myPivotAt(myI, false)) {
		if (myPrevLow !== null && (myP - myPrevLow.bar) <= myRngMax && low[myP] < myPrevLow.price && myRsi[myP] > myPrevLow.rsi) {
			myBull[myI] = true;
			myBullMark[myP] = myRsi[myP];
			if (myDrawLn) for (let myK = myPrevLow.bar; myK <= myP; myK += 1) myBullLine[myK] = myPrevLow.rsi + (myRsi[myP] - myPrevLow.rsi) * (myK - myPrevLow.bar) / (myP - myPrevLow.bar);
		}
		myPrevLow = { bar: myP, price: low[myP], rsi: myRsi[myP] };
	}
	if (myPivotAt(myI, true)) {
		if (myPrevHigh !== null && (myP - myPrevHigh.bar) <= myRngMax && high[myP] > myPrevHigh.price && myRsi[myP] < myPrevHigh.rsi) {
			myBear[myI] = true;
			myBearMark[myP] = myRsi[myP];
			if (myDrawLn) for (let myK = myPrevHigh.bar; myK <= myP; myK += 1) myBearLine[myK] = myPrevHigh.rsi + (myRsi[myP] - myPrevHigh.rsi) * (myK - myPrevHigh.bar) / (myP - myPrevHigh.bar);
		}
		myPrevHigh = { bar: myP, price: high[myP], rsi: myRsi[myP] };
	}
}
paint(horizontal_line(myObLevel), { name: 'Overbought', color: 'rgba(185,28,28,0.6)' });
paint(horizontal_line(myOsLevel), { name: 'Oversold', color: 'rgba(21,128,61,0.6)' });
paint(horizontal_line(50), { name: 'Midline', color: 'rgba(128,128,128,0.4)' });
paint(myRsi, { name: 'RSI', color: '#2563eb', thickness: 2 });
paint(myBullMark, { name: 'Bull Mark', style: 'dotted', marker: 'triangle', color: myColUp });
paint(myBearMark, { name: 'Bear Mark', style: 'dotted', marker: 'triangle-down', color: myColDn });
paint(myBullLine, { name: 'Bull Div Line', color: myColUp, thickness: 2 });
paint(myBearLine, { name: 'Bear Div Line', color: myColDn, thickness: 2 });
register_signal(myBull, 'Bullish Divergence');
register_signal(myBear, 'Bearish Divergence');
