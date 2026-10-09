/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Chop Detector
 * Author       : francodomenicandreacchi
 * Source URL   : https://www.tradingview.com/script/bZeU0zdn-Chop-Detector
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Chop Detector_TV
 *
 * Deviations from the original: Reviewed AI draft; helper-rolled smoothing and gradient; centred plot is a display
 *   shift of two bars (signals are not shifted).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Chop Detector_TV', 'lower', { decimals: 3 });
const myLen = input.number('Smoothing lookback', 20, { min: 1, max: 200 });
const myCenter = input.boolean('Center the plot', true);
const myWCenter = input.number('Center weight', 0.5, { min: 0, max: 5, step: 0.05 });
const myWNear = input.number('Adjacent weight', 0.25, { min: 0, max: 5, step: 0.05 });
const myWFar = input.number('Outer weight', 0.10, { min: 0, max: 5, step: 0.05 });
const myUseBrk = input.boolean('Breakout damping', true);
const myW5 = input.number('Weight last 5 wicks', 0.7, { min: 0, max: 1, step: 0.05 });
const myBrkTrig = input.number('Trigger body/wick', 1.0, { min: 0, max: 10, step: 0.1 });
const myBrkStr = input.number('Damping strength', 0.5, { min: 0, max: 5, step: 0.05 });
const myBrkHold = input.number('Hold bars', 4, { min: 1, max: 50 });
const mySmooth = input.number('Output smoothing', 2, { min: 1, max: 50 });
const myLimeThr = input.number('Lime below', 0.53, { min: 0, max: 5, step: 0.01 });
const myLoThr = input.number('Yellow from', 0.53, { min: 0, max: 5, step: 0.01 });
const myHiThr = input.number('Red at', 0.95, { min: 0, max: 5, step: 0.01 });
const myBlackThr = input.number('Black above', 1.0, { min: 0, max: 5, step: 0.01 });
const mySmaOf = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let mySum = 0;
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; mySum += _s[myK]; }
	return mySum / _n;
});
const myWick = close.map((_c, _i) => (high[_i] - Math.max(open[_i], _c)) + (Math.min(open[_i], _c) - low[_i]));
const myBody = close.map((_c, _i) => Math.abs(_c - open[_i]));
const myWickMa = mySmaOf(myWick, myLen), myBodyMa = mySmaOf(myBody, myLen);
const myRaw = close.map((_c, _i) => (myWickMa[_i] === null || myBodyMa[_i] === null || myBodyMa[_i] === 0) ? null : myWickMa[_i] / myBodyMa[_i]);
const myDen = myWCenter + 2 * myWNear + 2 * myWFar;
const myBase = close.map((_c, _i) => {
	if (_i < 4) return null;
	const myV = [myRaw[_i], myRaw[_i - 1], myRaw[_i - 2], myRaw[_i - 3], myRaw[_i - 4]];
	if (myV.some(_x => _x === null)) return null;
	return (myV[2] * myWCenter + (myV[1] + myV[3]) * myWNear + (myV[0] + myV[4]) * myWFar) / myDen;
});
const myWick5 = mySmaOf(myWick, 5), myWick10 = mySmaOf(myWick, 10);
const myBrkNow = close.map((_c, _i) => {
	if (myWick5[_i] === null || myWick10[_i] === null) return null;
	const myRef = myWick5[_i] * myW5 + myWick10[_i] * (1 - myW5);
	return Math.max((myRef > 0 ? myBody[_i] / myRef : 0) - myBrkTrig, 0);
});
const myBrkMax = myBrkNow.map((_v, _i) => {
	if (_i < myBrkHold - 1) return null;
	let myM = -Infinity;
	for (let myK = _i - myBrkHold + 1; myK <= _i; myK += 1) { if (myBrkNow[myK] === null) return null; myM = Math.max(myM, myBrkNow[myK]); }
	return myM;
});
const myDamped = myBase.map((_b, _i) => _b === null ? null : (myUseBrk ? (myBrkMax[_i] === null ? null : _b / (1 + myBrkStr * myBrkMax[_i])) : _b));
const myV = mySmaOf(myDamped, mySmooth);
const myHex = (_h) => [parseInt(_h.substring(1, 3), 16), parseInt(_h.substring(3, 5), 16), parseInt(_h.substring(5, 7), 16)];
const myMix = (_a, _b, _t) => { const myA = myHex(_a), myB = myHex(_b); return 'rgb(' + myA.map((_x, _k) => Math.round(_x + (myB[_k] - _x) * _t)).join(',') + ')'; };
const myColor = myV.map(_v => {
	if (_v === null) return 'gray';
	if (_v > myBlackThr) return '#000000';
	if (_v < myLimeThr) return '#97C459';
	const myT = Math.min(Math.max((_v - myLoThr) / (myHiThr - myLoThr), 0), 1);
	return myT < 0.5 ? myMix('#1D9E75', '#EF9F27', myT / 0.5) : myMix('#EF9F27', '#E24B4A', (myT - 0.5) / 0.5);
});
// "Center the plot" is the Pine plot offset of -2: bar i displays the value computed two bars later (display only, signals are not shifted)
const myShow = (_s) => myCenter ? _s.map((_v, _i) => _i + 2 < _s.length ? _s[_i + 2] : null) : _s;
paint(myShow(myV), { name: 'Chop', style: 'histogram', color: myShow(myColor), thickness: 3 });
paint(horizontal_line(myBlackThr), { name: 'Black Threshold', color: 'rgba(0,0,0,0.4)' });
paint(horizontal_line(myHiThr), { name: 'Red Threshold', color: 'rgba(226,75,74,0.4)' });
paint(horizontal_line(myLoThr), { name: 'Yellow Threshold', color: 'rgba(29,158,117,0.4)' });
paint(horizontal_line(myLimeThr), { name: 'Lime Threshold', color: 'rgba(151,196,89,0.4)' });
register_signal(myV.map(_v => _v !== null && _v < myLimeThr), 'Lime Zone Low Chop');
register_signal(myV.map(_v => _v !== null && _v >= myLoThr && _v < myHiThr), 'Yellow Zone Transition');
register_signal(myV.map(_v => _v !== null && _v >= myHiThr && _v <= myBlackThr), 'Red Zone High Chop');
register_signal(myV.map(_v => _v !== null && _v > myBlackThr), 'Black Zone Extreme Chop');
