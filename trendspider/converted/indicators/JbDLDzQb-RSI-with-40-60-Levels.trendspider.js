/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RSI with 40/60 Levels
 * Author       : Jon_Turner
 * Source URL   : https://www.tradingview.com/script/JbDLDzQb-RSI-with-40-60-Levels
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RSI with 40 60 Levels_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI, MA types hand-rolled; gradient fills replaced by
 *   plain tinted fills.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RSI with 40 60 Levels_TV', 'lower', { decimals: 2 });
const myRsiTab = input.tab('RSI Settings');
const myRsiLength = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const mySrcName = myRsiTab.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const mySmoothTab = input.tab('Smoothing');
const myMaType = mySmoothTab.select('MA Type', 'SMA', ['SMA', 'EMA', 'WMA', 'RMA']);
const myMaLength = mySmoothTab.number('MA Length', 5, { min: 1, max: 200 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
// pine-parity: SMA-seeded RMA; the MA types are hand-rolled over the valid values of the RSI
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myUp = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(_v - mySrc[_i - 1], 0)), myRsiLength);
const myDown = myRma(mySrc.map((_v, _i) => _i === 0 ? null : Math.max(mySrc[_i - 1] - _v, 0)), myRsiLength);
const myRsi = myUp.map((_u, _i) => (_u === null || myDown[_i] === null) ? null : (myDown[_i] === 0 ? 100 : (_u === 0 ? 0 : 100 - 100 / (1 + _u / myDown[_i]))));
const myWindowAvg = (_s, _n, _w) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let myNum = 0, myDen = 0;
	for (let myK = 0; myK < _n; myK += 1) {
		const myV = _s[_i - _n + 1 + myK];
		if (myV === null) return null;
		const myWt = _w ? myK + 1 : 1;
		myNum += myV * myWt; myDen += myWt;
	}
	return myNum / myDen;
});
let myMa;
if (myMaType === 'EMA') {
	let myE = null, myCnt = 0, mySum = 0;
	const myAlpha = 2 / (myMaLength + 1);
	myMa = myRsi.map(_v => {
		if (_v === null) return null;
		if (myE === null) { mySum += _v; myCnt += 1; if (myCnt === myMaLength) myE = mySum / myMaLength; return myE; }
		myE = myAlpha * _v + (1 - myAlpha) * myE; return myE;
	});
} else if (myMaType === 'RMA') {
	myMa = myRma(myRsi, myMaLength);
} else {
	myMa = myWindowAvg(myRsi, myMaLength, myMaType === 'WMA');
}
paint(myRsi, { name: 'RSI', color: '#7E57C2', thickness: 2 });
paint(myMa, { name: 'RSI MA', color: myMa.map((_m, _i) => (_m !== null && myRsi[_i] !== null && _m > myRsi[_i]) ? 'red' : 'green'), thickness: 1 });
paint(horizontal_line(70), { name: 'Overbought 70', color: 'rgba(255,0,0,0.5)' });
paint(horizontal_line(30), { name: 'Oversold 30', color: 'rgba(0,128,0,0.5)' });
paint(horizontal_line(50), { name: 'Midline 50', color: 'rgba(128,128,128,0.4)' });
paint(horizontal_line(60), { name: 'Upper 60', color: 'rgba(255,165,0,0.8)' });
paint(horizontal_line(40), { name: 'Lower 40', color: 'rgba(255,165,0,0.8)' });
color_cloud(horizontal_line(60), horizontal_line(40), 'rgba(121,114,114,0.15)', 'rgba(121,114,114,0.15)', 'Zone 4060 Up', 'Zone 4060 Dn');
color_cloud(horizontal_line(70), horizontal_line(60), 'rgba(123,31,162,0.1)', 'rgba(123,31,162,0.1)', 'Zone 6070 Up', 'Zone 6070 Dn');
color_cloud(horizontal_line(40), horizontal_line(30), 'rgba(123,31,162,0.1)', 'rgba(123,31,162,0.1)', 'Zone 3040 Up', 'Zone 3040 Dn');
// gradient fills are not available: plain tinted fills beyond 70 and 30
color_cloud(myRsi.map(_v => (_v !== null && _v > 70) ? _v : null), myRsi.map(_v => (_v !== null && _v > 70) ? 70 : null), 'rgba(0,200,0,0.3)', 'rgba(0,200,0,0.3)', 'Overbought Up', 'Overbought Dn');
color_cloud(myRsi.map(_v => (_v !== null && _v < 30) ? 30 : null), myRsi.map(_v => (_v !== null && _v < 30) ? _v : null), 'rgba(200,0,0,0.3)', 'rgba(200,0,0,0.3)', 'Oversold Up', 'Oversold Dn');
const myPrev = shift(myRsi, 1);
register_signal(for_every(myRsi, myPrev, (_r, _p) => _r !== null && _p !== null && _r > 60 && _p <= 60), 'RSI Cross Above 60');
register_signal(for_every(myRsi, myPrev, (_r, _p) => _r !== null && _p !== null && _r < 40 && _p >= 40), 'RSI Cross Below 40');
register_signal(myRsi.map(_r => _r !== null && _r > 70), 'RSI Overbought Above 70');
register_signal(myRsi.map(_r => _r !== null && _r < 30), 'RSI Oversold Below 30');
register_signal(myMa.map((_m, _i) => _m !== null && myRsi[_i] !== null && _m > myRsi[_i]), 'RSI MA Above RSI');
register_signal(myMa.map((_m, _i) => _m !== null && myRsi[_i] !== null && _m < myRsi[_i]), 'RSI MA Below RSI');
