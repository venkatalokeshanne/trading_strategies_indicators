/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Normalized Ichimoku Oscillator
 * Author       : visionvista
 * Source URL   : https://www.tradingview.com/script/cSiGmGMD-Normalized-Ichimoku-Oscillator
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Normalized Ichimoku Oscillator_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ATR; EMA/HMA hand-rolled over valid values; dotted
 *   threshold styles not available.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Normalized Ichimoku Oscillator_TV', 'lower');
const myIchTab = input.tab('Ichimoku Lengths');
const myTenkanLen = myIchTab.number('Tenkan Period', 9, { min: 1 });
const myKijunLen = myIchTab.number('Kijun Period', 26, { min: 1 });
const mySpanBLen = myIchTab.number('Span B Period', 52, { min: 1 });
const myAtrLen = myIchTab.number('ATR Normalization', 14, { min: 1 });
const myMaTab = input.tab('Kijun Deviation MA');
const myShowKijunMa = myMaTab.boolean('Show Kijun MA', true);
const myMaType = myMaTab.select('MA Type', 'EMA', ['EMA', 'SMA', 'HMA']);
const myMaLen = myMaTab.number('MA Length', 10, { min: 1 });
const myVisTab = input.tab('Visibility');
const myShowTenkan = myVisTab.boolean('Show Tenkan Dev', true);
const myShowKijun = myVisTab.boolean('Show Kijun Dev', true);
const myShowSpanA = myVisTab.boolean('Show Span A Dev', true);
const myShowSpanB = myVisTab.boolean('Show Span B Dev', true);
const myLevTab = input.tab('Thresholds');
const myObExtreme = myLevTab.number('Overbought Extreme', 3.0, { min: -10, max: 10, step: 0.1 });
const myObWarning = myLevTab.number('Overbought Warning', 2.0, { min: -10, max: 10, step: 0.1 });
const myOsWarning = myLevTab.number('Oversold Warning', -2.0, { min: -10, max: 10, step: 0.1 });
const myOsExtreme = myLevTab.number('Oversold Extreme', -3.0, { min: -10, max: 10, step: 0.1 });
const myDonchian = (_n) => close.map((_c, _i) => {
	if (_i < _n - 1) return null;
	let myHi = -Infinity, myLo = Infinity;
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { myHi = Math.max(myHi, high[myK]); myLo = Math.min(myLo, low[myK]); }
	return (myHi + myLo) / 2;
});
const myTenkan = myDonchian(myTenkanLen);
const myKijun = myDonchian(myKijunLen);
const mySpanA = myTenkan.map((_t, _i) => (_t === null || myKijun[_i] === null) ? null : (_t + myKijun[_i]) / 2);
const mySpanB = myDonchian(mySpanBLen);
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLen) myAcc = mySeed / myAtrLen; return myAcc; }
	myAcc = (myAcc * (myAtrLen - 1) + _v) / myAtrLen; return myAcc;
});
const myOsc = (_line) => close.map((_c, _i) => (myAtr[_i] === null || _line[_i] === null) ? null : (myAtr[_i] > 0 ? (_c - _line[_i]) / myAtr[_i] : 0));
const myOscTenkan = myOsc(myTenkan), myOscKijun = myOsc(myKijun), myOscSpanA = myOsc(mySpanA), myOscSpanB = myOsc(mySpanB);
// moving averages over valid values (EMA seeded with an SMA; HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n)))
const myWma = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let myNum = 0, myDen = 0;
	for (let myK = 0; myK < _n; myK += 1) { const myV = _s[_i - _n + 1 + myK]; if (myV === null) return null; myNum += myV * (myK + 1); myDen += myK + 1; }
	return myNum / myDen;
});
const mySmaOf = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let mySum = 0;
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; mySum += _s[myK]; }
	return mySum / _n;
});
let myKijunMa;
if (myMaType === 'SMA') {
	myKijunMa = mySmaOf(myOscKijun, myMaLen);
} else if (myMaType === 'HMA') {
	const myHalf = myWma(myOscKijun, Math.max(1, Math.round(myMaLen / 2)));
	const myFull = myWma(myOscKijun, myMaLen);
	const myRaw = myHalf.map((_h, _i) => (_h === null || myFull[_i] === null) ? null : 2 * _h - myFull[_i]);
	myKijunMa = myWma(myRaw, Math.max(1, Math.round(Math.sqrt(myMaLen))));
} else {
	let myE = null, myCnt = 0, mySum = 0;
	const myAlpha = 2 / (myMaLen + 1);
	myKijunMa = myOscKijun.map(_v => {
		if (_v === null) return null;
		if (myE === null) { mySum += _v; myCnt += 1; if (myCnt === myMaLen) myE = mySum / myMaLen; return myE; }
		myE = myAlpha * _v + (1 - myAlpha) * myE; return myE;
	});
}
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
const myZero = series_of(0);
paint(myZero, { name: 'Equilibrium', color: 'gray', thickness: 1 });
paint(myGate(myOscTenkan, myShowTenkan), { name: 'Tenkan Dev', color: 'blue' });
paint(myGate(myOscKijun, myShowKijun), { name: 'Kijun Dev', color: 'white', thickness: 2 });
paint(myGate(myOscSpanA, myShowSpanA), { name: 'Span A Dev', color: 'green' });
paint(myGate(myOscSpanB, myShowSpanB), { name: 'Span B Dev', color: 'orange' });
paint(myGate(myKijunMa, myShowKijunMa), { name: 'Kijun MA', color: 'yellow', thickness: 1 });
color_cloud(myOscKijun, myZero, 'rgba(76,175,80,0.3)', 'rgba(244,67,54,0.3)', 'Kijun Above', 'Kijun Below');
paint(horizontal_line(myObExtreme), { name: 'OB Extreme', color: 'red', thickness: 2 });
paint(horizontal_line(myObWarning), { name: 'OB Warning', color: 'rgba(244,67,54,0.5)' });
paint(horizontal_line(myOsWarning), { name: 'OS Warning', color: 'rgba(76,175,80,0.5)' });
paint(horizontal_line(myOsExtreme), { name: 'OS Extreme', color: 'green', thickness: 2 });
const myPrev = shift(myOscKijun, 1);
register_signal(for_every(myOscKijun, myPrev, (_c, _p) => _c !== null && _p !== null && _p >= myObExtreme && _c < myObExtreme), 'Kijun OB Alert');
register_signal(for_every(myOscKijun, myPrev, (_c, _p) => _c !== null && _p !== null && _p <= myOsExtreme && _c > myOsExtreme), 'Kijun OS Alert');
