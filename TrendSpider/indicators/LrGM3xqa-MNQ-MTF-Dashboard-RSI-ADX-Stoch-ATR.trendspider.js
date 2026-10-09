/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MNQ MTF Dashboard [RSI/ADX/Stoch/ATR]
 * Author       : wilsonvivas32
 * Source URL   : https://www.tradingview.com/script/LrGM3xqa-MNQ-MTF-Dashboard-RSI-ADX-Stoch-ATR
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MNQ MTF Dashboard_TV
 *
 * Deviations from the original: Table is a static image of the developing bar of each timeframe; bias signals use
 *   the last completed bar; RSI/ADX/ATR/Stoch hand-rolled Pine-style
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MNQ MTF Dashboard_TV', 'price');
const myTablePos = input.select('Table Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 200 });
const myAdxLen = input.number('ADX DI Length', 14, { min: 1, max: 200 });
const myStochLen = input.number('Stoch K Length', 14, { min: 1, max: 200 });
const myStochSmK = input.number('Stoch K Smooth', 3, { min: 1, max: 50 });
const myStochSmD = input.number('Stoch D Smooth', 3, { min: 1, max: 50 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
// SMA-seeded RMA (Pine ta.rma); null-aware (starts once the first value exists)
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; return _s.map(_v => { if (_v === null) return null; if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
const mySma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myS += _s[myK]; } return myS / _n; });
const myMetrics = (_d) => {
	const myN = _d.close.length;
	const myTr = _d.close.map((_c, _i) => _i === 0 ? null : Math.max(_d.high[_i] - _d.low[_i], Math.abs(_d.high[_i] - _d.close[_i - 1]), Math.abs(_d.low[_i] - _d.close[_i - 1])));
	// ta.rsi
	const myGain = _d.close.map((_c, _i) => _i === 0 ? null : Math.max(_c - _d.close[_i - 1], 0));
	const myLoss = _d.close.map((_c, _i) => _i === 0 ? null : Math.max(_d.close[_i - 1] - _c, 0));
	const myRu = myRma(myGain, myRsiLen), myRd = myRma(myLoss, myRsiLen);
	const myRsi = myRu.map((_u, _i) => _u === null ? null : (myRd[_i] === 0 ? 100 : 100 - 100 / (1 + _u / myRd[_i])));
	// the script's own adx(): DI from RMA of DM over RMA of TR, ADX = 100 * RMA(|+DI - -DI| / sum)
	const myUp = _d.high.map((_h, _i) => _i === 0 ? null : _h - _d.high[_i - 1]);
	const myDn = _d.low.map((_l, _i) => _i === 0 ? null : _d.low[_i - 1] - _l);
	const myPdm = myUp.map((_u, _i) => _u === null ? null : (_u > myDn[_i] && _u > 0 ? _u : 0));
	const myMdm = myDn.map((_d2, _i) => _d2 === null ? null : (_d2 > myUp[_i] && _d2 > 0 ? _d2 : 0));
	const myTrr = myRma(myTr, myAdxLen), myPr = myRma(myPdm, myAdxLen), myMr = myRma(myMdm, myAdxLen);
	let myLp = null, myLm = null;
	const myPlus = myTrr.map((_t, _i) => { if (_t !== null && _t !== 0 && myPr[_i] !== null) myLp = 100 * myPr[_i] / _t; return myLp; });
	const myMinus = myTrr.map((_t, _i) => { if (_t !== null && _t !== 0 && myMr[_i] !== null) myLm = 100 * myMr[_i] / _t; return myLm; });
	const myRatio = myPlus.map((_p, _i) => (_p === null || myMinus[_i] === null) ? null : Math.abs(_p - myMinus[_i]) / ((_p + myMinus[_i]) === 0 ? 1 : (_p + myMinus[_i])));
	const myAdx = myRma(myRatio, myAdxLen).map(_v => _v === null ? null : 100 * _v);
	// ta.stoch -> sma -> sma
	const myRaw = _d.close.map((_c, _i) => { if (_i < myStochLen - 1) return null; let myH = -Infinity, myL = Infinity; for (let myK = _i - myStochLen + 1; myK <= _i; myK += 1) { myH = Math.max(myH, _d.high[myK]); myL = Math.min(myL, _d.low[myK]); } return myH === myL ? null : 100 * (_c - myL) / (myH - myL); });
	const myK = mySma(myRaw, myStochSmK), myD = mySma(myK, myStochSmD);
	const myAtr = myRma(myTr, myAtrLen);
	return { time: _d.time, rsi: myRsi, adx: myAdx, k: myK, d: myD, atr: myAtr };
};
const myOn = async (_res) => {
	const myData = await request.history(current.ticker, _res);
	assert(!myData.error, 'Error fetching ' + _res + ' data: ' + myData.error);
	return myMetrics(myData);
};
const myM5 = await myOn('5');
const myM15 = await myOn('15');
const myM60 = await myOn('60');
const myM240 = await myOn('240');
const myMD = await myOn('D');
const myF = (_v) => _v === null ? 'NA' : String(Math.round(_v * 100) / 100);
const myLastOf = (_a) => _a[_a.length - 1];
const myRow = (_lbl, _m) => {
	const myA = myLastOf(_m.adx), myR = myLastOf(_m.rsi), myKv = myLastOf(_m.k), myDv = myLastOf(_m.d), myAt = myLastOf(_m.atr);
	const myBull = myR !== null && myKv !== null && myDv !== null && myR >= 50 && myKv >= myDv;
	const myBear = myR !== null && myKv !== null && myDv !== null && myR < 50 && myKv < myDv;
	const myStochCol = (myKv !== null && myDv !== null && myKv > myDv && myKv >= 50) ? '#009688' : ((myKv !== null && myDv !== null && myKv < myDv && myKv < 50) ? '#F44336' : '#9E9E9E');
	return { cells: [
		{ text: _lbl, color: 'white', background_color: '#222222' },
		{ text: myF(myA), color: 'white', background_color: myA === null ? '#9E9E9E' : (myA >= 25 ? '#009688' : (myA >= 20 ? '#FF9800' : '#9E9E9E')) },
		{ text: myF(myR), color: 'white', background_color: myR !== null && myR >= 50 ? '#009688' : '#F44336' },
		{ text: myF(myKv) + '/' + myF(myDv), color: 'white', background_color: myStochCol },
		{ text: myF(myAt), color: 'white', background_color: '#222222' },
		{ text: myBull ? 'Bull' : (myBear ? 'Bear' : 'Mixed'), color: 'white', background_color: myBull ? '#009688' : (myBear ? '#F44336' : '#9E9E9E') }
	] };
};
paint_overlay('MTF Dashboard Table', { position: myTablePos }, {
	rows: [
		{ cells: ['TF', 'ADX', 'RSI', 'Stoch', 'ATR', 'Bias'].map(_t => ({ text: _t, color: 'white', background_color: '#78909C' })) },
		myRow('5m', myM5), myRow('15m', myM15), myRow('1H', myM60), myRow('4H', myM240), myRow('1D', myMD)
	]
});
// bullish-bias signals use the last completed bar of each timeframe (the table shows the developing bar, as the Pine does)
const myBias = (_m) => {
	const myB = _m.rsi.map((_r, _k) => (_k === 0 || _m.rsi[_k - 1] === null || _m.k[_k - 1] === null || _m.d[_k - 1] === null) ? null : ((_m.rsi[_k - 1] >= 50 && _m.k[_k - 1] >= _m.d[_k - 1]) ? 1 : 0));
	return land_points_onto_series(_m.time, myB, time, 'ge').length ? interpolate_sparse_series(land_points_onto_series(_m.time, myB, time, 'ge'), 'constant') : close.map(() => null);
};
register_signal(myBias(myM5).map(_v => _v === 1), 'Bullish Bias 5m');
register_signal(myBias(myM15).map(_v => _v === 1), 'Bullish Bias 15m');
register_signal(myBias(myM60).map(_v => _v === 1), 'Bullish Bias 1H');
register_signal(myBias(myM240).map(_v => _v === 1), 'Bullish Bias 4H');
register_signal(myBias(myMD).map(_v => _v === 1), 'Bullish Bias 1D');
