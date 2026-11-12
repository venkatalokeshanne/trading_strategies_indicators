/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA EMA Ribbon
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/RFEbunir-VASA-EMA-Ribbon-vF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA EMA Ribbon_TV
 *
 * Deviations from the original: Reviewed AI draft; ribbon fill as clouds (amber when compressed); colour inputs
 *   fixed at Pine defaults.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA EMA Ribbon_TV', 'price');
const myRibbonTab = input.tab('Ribbon');
const mySrcName = myRibbonTab.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myBaseLen = myRibbonTab.number('Base length', 8, { min: 1, max: 500 });
const myEmaStep = myRibbonTab.number('EMA step', 8, { min: 1, max: 500 });
const myCount = myRibbonTab.number('EMA count', 6, { min: 2, max: 8 });
const myStyleTab = input.tab('Style');
const myShadeComp = myStyleTab.boolean('Shade compression', true);
const myCompPct = myStyleTab.number('Compression %', 0.5, { min: 0.01, max: 100, step: 0.05 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myEmas = [0, 1, 2, 3, 4, 5, 6, 7].map(_k => ema(mySrc, myBaseLen + myEmaStep * _k));
const myESlow = ema(mySrc, myBaseLen + myEmaStep * (myCount - 1));
const myE1 = myEmas[0];
const myTrendUp = for_every(myE1, myESlow, (_a, _b) => _a !== null && _b !== null && _a > _b);
const myRibColor = myTrendUp.map(_u => _u ? '#15803d' : '#b91c1c');
const myCompressed = myE1.map((_e, _i) => myESlow[_i] !== null && _e !== null && close[_i] !== 0 && Math.abs(_e - myESlow[_i]) / close[_i] * 100 < myCompPct);
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
paint(myGate(myEmas[0], myCount >= 1), { name: 'EMA 1', color: myRibColor });
paint(myGate(myEmas[1], myCount >= 2), { name: 'EMA 2', color: myRibColor });
paint(myGate(myEmas[2], myCount >= 3), { name: 'EMA 3', color: myRibColor });
paint(myGate(myEmas[3], myCount >= 4), { name: 'EMA 4', color: myRibColor });
paint(myGate(myEmas[4], myCount >= 5), { name: 'EMA 5', color: myRibColor });
paint(myGate(myEmas[5], myCount >= 6), { name: 'EMA 6', color: myRibColor });
paint(myGate(myEmas[6], myCount >= 7), { name: 'EMA 7', color: myRibColor });
paint(myGate(myEmas[7], myCount >= 8), { name: 'EMA 8', color: myRibColor });
const myCompGate = (_s) => _s.map((_v, _i) => (myShadeComp && myCompressed[_i]) ? _v : null);
color_cloud(myCompGate(myE1), myCompGate(myESlow), 'rgba(245,158,11,0.3)', 'rgba(245,158,11,0.3)', 'Compress Up', 'Compress Dn');
color_cloud(myE1.map((_v, _i) => (myShadeComp && myCompressed[_i]) ? null : _v), myESlow.map((_v, _i) => (myShadeComp && myCompressed[_i]) ? null : _v), 'rgba(21,128,61,0.12)', 'rgba(185,28,28,0.12)', 'Bull Fill', 'Bear Fill');
const myPrevUp = shift(myTrendUp, 1);
register_signal(for_every(myTrendUp, myPrevUp, (_t, _p) => _t === true && _p === false), 'Ribbon Turned Up');
register_signal(for_every(myTrendUp, myPrevUp, (_t, _p) => _t === false && _p === true), 'Ribbon Turned Down');
register_signal(myCompressed.map((_c, _i) => _c && _i > 0 && !myCompressed[_i - 1]), 'Ribbon Compressed');
