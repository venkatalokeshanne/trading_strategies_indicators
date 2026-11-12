/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : RSI + CCI MultiTF Signal (ATR + Flat + Full Stoch Filter)
 * Author       : evgeniykulikov
 * Source URL   : https://www.tradingview.com/script/lu5mFdPv-btc-eth-15m-signal-atr-flat-filter
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : RSI CCI MultiTF Signal_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI/CCI/stoch/ATR hand-rolled; 1h values lag one
 *   completed 1h bar (non-repainting); alert text not carried over.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('RSI CCI MultiTF Signal_TV', 'price');
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myCciLength = input.number('CCI Length', 20, { min: 1, max: 200 });
const myStochKLength = input.number('Stoch K Length', 14, { min: 1, max: 200 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myUseAtrFilter = input.boolean('Use ATR Filter', true);
const myUseFlatFilter = input.boolean('Use Flat Filter', true);
// Pine-exact helpers (SMA-seeded RMA; windows over valid values)
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myRsiOf = (_c, _n) => {
	const myG = myRma(_c.map((_v, _i) => _i === 0 ? null : Math.max(_v - _c[_i - 1], 0)), _n);
	const myL = myRma(_c.map((_v, _i) => _i === 0 ? null : Math.max(_c[_i - 1] - _v, 0)), _n);
	return myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
};
const mySmaOf = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let mySum = 0;
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; mySum += _s[myK]; }
	return mySum / _n;
});
const myCciOf = (_c, _n) => {
	const myMa = mySmaOf(_c, _n);
	return _c.map((_v, _i) => {
		if (myMa[_i] === null) return null;
		let myDev = 0;
		for (let myK = _i - _n + 1; myK <= _i; myK += 1) myDev += Math.abs(_c[myK] - myMa[_i]);
		myDev /= _n;
		return myDev === 0 ? 0 : (_v - myMa[_i]) / (0.015 * myDev);
	});
};
const myRsi15 = myRsiOf(close, myRsiLength);
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
const myAtr = myRma(myTr, myAtrLength);
const myAtrSma = mySmaOf(myAtr, myAtrLength);
const myRange20 = close.map((_c, _i) => {
	if (_i < 19) return null;
	let myHi = -Infinity, myLo = Infinity;
	for (let myK = _i - 19; myK <= _i; myK += 1) { myHi = Math.max(myHi, high[myK]); myLo = Math.min(myLo, low[myK]); }
	return myHi - myLo;
});
const myK = close.map((_c, _i) => {
	if (_i < myStochKLength - 1) return null;
	let myHi = -Infinity, myLo = Infinity;
	for (let myJ = _i - myStochKLength + 1; myJ <= _i; myJ += 1) { myHi = Math.max(myHi, high[myJ]); myLo = Math.min(myLo, low[myJ]); }
	return myHi === myLo ? null : 100 * (_c - myLo) / (myHi - myLo);
});
const my1h = await request.history(current.ticker, '60');
assert(!my1h.error, 'Error fetching 1h data: ' + my1h.error);
// 1h values seen on the chart are those of the last COMPLETED 1h bar (shifted one bar, L23)
const myLand = (_vals) => interpolate_sparse_series(land_points_onto_series(my1h.time, _vals.map((_v, _k) => _k ? _vals[_k - 1] : null), time, 'le'), 'constant');
const myRsi1h = myLand(myRsiOf(my1h.close, myRsiLength));
const myCci1h = myLand(myCciOf(my1h.close, myCciLength));
const myLongSignal = close.map((_c, _i) => {
	const myPrev = _i > 0 ? myRsi15[_i - 1] : null;
	if (myPrev === null || myRsi15[_i] === null || myK[_i] === null || myRsi1h[_i] === null || myCci1h[_i] === null) return false;
	const myAtrOk = !myUseAtrFilter || (myAtr[_i] !== null && myAtrSma[_i] !== null && myAtr[_i] > myAtrSma[_i] * 1.1);
	const myFlatOk = !myUseFlatFilter || (myRange20[_i] !== null && myAtr[_i] !== null && myRange20[_i] > myAtr[_i] * 2);
	return myPrev <= 30 && myRsi15[_i] > 30 && myK[_i] > 20 && myRsi1h[_i] < 40 && myCci1h[_i] < 100 && myAtrOk && myFlatOk;
});
const myShortSignal = close.map((_c, _i) => {
	const myPrev = _i > 0 ? myRsi15[_i - 1] : null;
	if (myPrev === null || myRsi15[_i] === null || myK[_i] === null || myRsi1h[_i] === null || myCci1h[_i] === null) return false;
	const myAtrOk = !myUseAtrFilter || (myAtr[_i] !== null && myAtrSma[_i] !== null && myAtr[_i] > myAtrSma[_i] * 1.1);
	const myFlatOk = !myUseFlatFilter || (myRange20[_i] !== null && myAtr[_i] !== null && myRange20[_i] > myAtr[_i] * 2);
	return myPrev >= 70 && myRsi15[_i] < 70 && myK[_i] < 80 && myRsi1h[_i] > 60 && myCci1h[_i] > 100 && myAtrOk && myFlatOk;
});
paint(myLongSignal.map(_s => _s ? constants.icons.triangle_up : null), { name: 'Long Mark', style: 'labels_below', color: 'green' });
paint(myShortSignal.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Short Mark', style: 'labels_above', color: 'red' });
register_signal(myLongSignal, 'Long Signal');
register_signal(myShortSignal, 'Short Signal');
