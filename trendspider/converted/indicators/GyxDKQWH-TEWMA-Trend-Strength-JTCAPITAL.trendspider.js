/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : TEWMA Trend Strength - [JTCAPITAL]
 * Author       : JTCapitalNL
 * Source URL   : https://www.tradingview.com/script/GyxDKQWH-TEWMA-Trend-Strength-JTCAPITAL
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : TEWMA Trend Strength_TV
 *
 * Deviations from the original: Reviewed AI draft; TEMA/WMA/EMA and Pine-exact ATR hand-rolled; bgcolor not
 *   available; fills as clouds.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('TEWMA Trend Strength_TV', 'lower');
const mySrcName = input.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myLen = input.number('Length', 50, { min: 1, max: 500 });
const myMulti = input.number('Multiplier', 2, { min: 0.05, max: 10, step: 0.05 });
const myAtrLength = input.number('ATR Length', 40, { min: 1, max: 500 });
const mySmoothLen = input.number('Smoothing Length', 50, { min: 1, max: 500 });
const myUpper = input.number('Upper Level', 1, { min: -10, max: 10, step: 0.1 });
const myLower = input.number('Lower Level', -1, { min: -10, max: 10, step: 0.1 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myLen2 = Math.round(myLen * myMulti);
// null-aware helpers: WMA, SMA-seeded EMA, TEMA = 3*e1 - 3*e2 + e3
const myWma = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let myNum = 0, myDen = 0;
	for (let myK = 0; myK < _n; myK += 1) { const myV = _s[_i - _n + 1 + myK]; if (myV === null) return null; myNum += myV * (myK + 1); myDen += myK + 1; }
	return myNum / myDen;
});
const myEma = (_s, _n) => {
	let myAcc = null, myCnt = 0, mySum = 0;
	const myAlpha = 2 / (_n + 1);
	return _s.map(_v => {
		if (_v === null) return null;
		if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; }
		myAcc = myAlpha * _v + (1 - myAlpha) * myAcc; return myAcc;
	});
};
const myTema = (_s, _n) => {
	const myE1 = myEma(_s, _n), myE2 = myEma(myE1, _n), myE3 = myEma(myE2, _n);
	return myE1.map((_v, _i) => (_v === null || myE2[_i] === null || myE3[_i] === null) ? null : 3 * _v - 3 * myE2[_i] + myE3[_i]);
};
const myT1 = myTema(myWma(mySrc, myLen), myLen);
const myT2 = myTema(myWma(mySrc, myLen2), myLen2);
const myTewma = myT1.map((_v, _i) => (_v === null || myT2[_i] === null) ? null : (_v + myT2[_i]) / 2);
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLength) myAcc = mySeed / myAtrLength; return myAcc; }
	myAcc = (myAcc * (myAtrLength - 1) + _v) / myAtrLength; return myAcc;
});
const myStrength = close.map((_c, _i) => (myTewma[_i] === null || myAtr[_i] === null || myAtr[_i] === 0) ? null : (_c - myTewma[_i]) / myAtr[_i]);
const mySmoothed = myEma(myStrength, mySmoothLen);
const myBull = 'rgb(49,132,228)';
const myBear = 'rgb(132,3,158)';
const myZero = series_of(0);
paint(myStrength, { name: 'Strength', color: myStrength.map(_s => (_s !== null && _s > 0) ? myBull : myBear), thickness: 2 });
paint(mySmoothed, { name: 'Smoothed', color: mySmoothed.map(_s => (_s !== null && _s > 0) ? myBull : myBear), thickness: 1 });
color_cloud(myStrength, myZero, 'rgba(49,132,228,0.4)', 'rgba(132,3,158,0.4)', 'Strength Bull', 'Strength Bear');
color_cloud(mySmoothed, myZero, 'rgba(49,132,228,0.3)', 'rgba(132,3,158,0.3)', 'Smoothed Bull', 'Smoothed Bear');
paint(horizontal_line(myUpper), { name: 'Upper Level', color: 'silver' });
paint(horizontal_line(myLower), { name: 'Lower Level', color: 'silver' });
register_signal(myStrength.map(_s => _s !== null && _s > 0), 'Strength Bullish');
register_signal(myStrength.map(_s => _s !== null && _s < 0), 'Strength Bearish');
register_signal(mySmoothed.map(_s => _s !== null && _s > 0), 'Smoothed Bullish');
register_signal(mySmoothed.map(_s => _s !== null && _s < 0), 'Smoothed Bearish');
register_signal(myStrength.map(_s => _s !== null && _s > myUpper), 'Strength Above Upper');
register_signal(myStrength.map(_s => _s !== null && _s < myLower), 'Strength Below Lower');
