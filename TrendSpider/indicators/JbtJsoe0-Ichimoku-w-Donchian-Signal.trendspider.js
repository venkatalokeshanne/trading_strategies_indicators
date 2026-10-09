/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Combined Ichimoku & Donchian
 * Author       : visionvista
 * Source URL   : https://www.tradingview.com/script/JbtJsoe0-Ichimoku-w-Donchian-Signal
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Combined Ichimoku and Donchian_TV
 *
 * Deviations from the original: Span clouds end at the last bar; Chikou only where a later bar exists; breakout
 *   ribbons as clouds
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Combined Ichimoku and Donchian_TV', 'price');
const myTenkanLen = input.number('Tenkan Period', 9, { min: 1, max: 300 });
const myKijunLen = input.number('Kijun Period', 26, { min: 1, max: 300 });
const mySenkouB = input.number('Senkou B Period', 52, { min: 1, max: 300 });
const myDisp = input.number('Displacement', 26, { min: 1, max: 100 });
const myShowTenkan = input.boolean('Show Tenkan', true);
const myShowKijun = input.boolean('Show Kijun', true);
const myShowCloud = input.boolean('Show Cloud', true);
const myShowChikou = input.boolean('Show Chikou', true);
const myDcFast = input.number('Fast Band Period', 20, { min: 1, max: 300 });
const myDcSlow = input.number('Slow Band Period', 50, { min: 1, max: 300 });
const myDcBreak = input.number('Breakout Period', 20, { min: 1, max: 300 });
const myShowDC = input.boolean('Show Donchian', true);
const myN = close.length;
const myWin = (_s, _n, _f) => _s.map((_v, _i) => _i < _n - 1 ? null : _f(_s.slice(_i - _n + 1, _i + 1)));
const myHh = (_n) => myWin(high, _n, _w => Math.max(..._w)), myLl = (_n) => myWin(low, _n, _w => Math.min(..._w));
const myMid = (_n) => { const myA = myHh(_n), myB = myLl(_n); return myA.map((_v, _i) => _v === null ? null : (_v + myB[_i]) / 2); };
const myTenkan = myMid(myTenkanLen), myKijun = myMid(myKijunLen), mySpanBraw = myMid(mySenkouB);
const mySpanAraw = myTenkan.map((_v, _i) => (_v === null || myKijun[_i] === null) ? null : (_v + myKijun[_i]) / 2);
const myDelay = (_s, _o) => _s.map((_v, _i) => _i - _o >= 0 ? _s[_i - _o] : null);
const myGate = (_s, _f) => _f ? _s : _s.map(() => null);
const mySpanA = myDelay(mySpanAraw, myDisp - 1), mySpanB = myDelay(mySpanBraw, myDisp - 1);
// Chikou is plotted disp-1 bars back: value at bar i is the close disp-1 bars later (only where that bar exists)
const myChikou = close.map((_c, _i) => _i + myDisp - 1 < myN ? close[_i + myDisp - 1] : null);
const myUpF = myHh(myDcFast), myLoF = myLl(myDcFast), myUpS = myHh(myDcSlow), myLoS = myLl(myDcSlow);
const myBrkU = myHh(myDcBreak).map((_v, _i, _a) => _i ? _a[_i - 1] : null), myBrkL = myLl(myDcBreak).map((_v, _i, _a) => _i ? _a[_i - 1] : null);
paint(myGate(myTenkan, myShowTenkan), { name: 'Tenkan sen', color: '#2962ff' });
paint(myGate(myKijun, myShowKijun), { name: 'Kijun sen', color: '#ef5350' });
paint(myGate(mySpanA, myShowCloud), { name: 'Span A', color: '#26a69a' });
paint(myGate(mySpanB, myShowCloud), { name: 'Span B', color: '#ef5350' });
color_cloud(myGate(mySpanA, myShowCloud), myGate(mySpanB, myShowCloud), 'rgba(38,166,154,0.15)', 'rgba(239,83,80,0.15)', 'Bull Cloud', 'Bear Cloud');
paint(myGate(myChikou, myShowChikou), { name: 'Chikou Span', color: '#9c27b0' });
paint(myGate(myUpF, myShowDC), { name: 'Fast Upper', color: 'gray' });
paint(myGate(myLoF, myShowDC), { name: 'Fast Lower', color: 'gray' });
paint(myGate(myUpS, myShowDC), { name: 'Slow Upper', color: 'silver' });
paint(myGate(myLoS, myShowDC), { name: 'Slow Lower', color: 'silver' });
color_cloud(myGate(myUpF, myShowDC), myGate(myUpS, myShowDC), 'rgba(128,128,128,0.15)', 'rgba(128,128,128,0.15)', 'Upper Ribbon', 'Upper Ribbon Dn');
color_cloud(myGate(myLoF, myShowDC), myGate(myLoS, myShowDC), 'rgba(128,128,128,0.15)', 'rgba(128,128,128,0.15)', 'Lower Ribbon', 'Lower Ribbon Dn');
// first breakout in each direction until the opposite one fires (Pine var lastSignal)
let myLastSig = 0;
const myTrigL = [], myTrigS = [];
for (let myI = 0; myI < myN; myI += 1) {
	const myLong = myBrkU[myI] !== null && close[myI] > myBrkU[myI], myShort = myBrkL[myI] !== null && close[myI] < myBrkL[myI];
	const myTl = myLong && myLastSig !== 1, myTs = myShort && myLastSig !== -1;
	if (myTl) myLastSig = 1;
	if (myTs) myLastSig = -1;
	myTrigL.push(myTl); myTrigS.push(myTs);
}
paint(myTrigL.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Long Mark', style: 'labels_below', color: 'green' });
paint(myTrigS.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Short Mark', style: 'labels_above', color: 'red' });
register_signal(myTrigL, 'Donchian Long Entry');
register_signal(myTrigS, 'Donchian Short Entry');
