/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VASA Multi-Timeframe Rating
 * Author       : VASATrendAI
 * Source URL   : https://www.tradingview.com/script/ds0y9u9a-VASA-Multi-Timeframe-Rating-vF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VASA Multi Timeframe Rating_TV
 *
 * Deviations from the original: Table is a static image of the last bar; EMA/RSI hand-rolled Pine-style; last
 *   completed HTF bar values
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VASA Multi Timeframe Rating_TV', 'price');
const myTf1 = input.select('Timeframe 1', '15', ['5', '15', '30', '60', '120', '240', 'D']);
const myTf2 = input.select('Timeframe 2', '60', ['5', '15', '30', '60', '120', '240', 'D']);
const myTf3 = input.select('Timeframe 3', '240', ['5', '15', '30', '60', '120', '240', 'D']);
const myFastLen = input.number('EMA fast', 21, { min: 1, max: 500 });
const mySlowLen = input.number('EMA slow', 50, { min: 1, max: 500 });
const myRsiLen = input.number('RSI length', 14, { min: 1, max: 500 });
const myTablePos = input.select('Table position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
// Pine ta.rsi: RMA (SMA-seeded) of gains and losses
const myRsi = (_s, _n) => {
	let myUp = null, myDn = null, myCnt = 0, mySu = 0, mySd = 0;
	return _s.map((_v, _i) => {
		if (_i === 0) return null;
		const myCh = _v - _s[_i - 1], myG = Math.max(myCh, 0), myL = Math.max(-myCh, 0);
		if (myUp === null) { mySu += myG; mySd += myL; myCnt += 1; if (myCnt === _n) { myUp = mySu / _n; myDn = mySd / _n; } else return null; }
		else { myUp = (myUp * (_n - 1) + myG) / _n; myDn = (myDn * (_n - 1) + myL) / _n; }
		return myDn === 0 ? 100 : 100 - 100 / (1 + myUp / myDn);
	});
};
const myScoreOn = async (_res) => {
	const myD = await request.history(current.ticker, _res);
	assert(!myD.error, 'Error fetching ' + _res + ' data: ' + myD.error);
	const myEf = myEma(myD.close, myFastLen), myEs = myEma(myD.close, mySlowLen), myR = myRsi(myD.close, myRsiLen);
	// the values of the last completed HTF bar ([1] with lookahead_on), shown for the whole current HTF bar
	const myTu = myD.close.map((_c, _k) => (_k > 0 && myEf[_k - 1] !== null && myEs[_k - 1] !== null) ? (myEf[_k - 1] > myEs[_k - 1] ? 1 : 0) : null);
	const myMu = myD.close.map((_c, _k) => (_k > 0 && myR[_k - 1] !== null) ? (myR[_k - 1] > 50 ? 1 : 0) : null);
	const myLand = (_a) => interpolate_sparse_series(land_points_onto_series(myD.time, _a, time, 'ge'), 'constant');
	const myTuL = myLand(myTu), myMuL = myLand(myMu);
	const myS = myTuL.map((_t, _i) => (_t === null || myMuL[_i] === null) ? null : (_t === 1 ? 1 : -1) + (myMuL[_i] === 1 ? 1 : -1));
	return { tu: myTuL, mu: myMuL, s: myS };
};
const myR1 = await myScoreOn(myTf1);
const myR2 = await myScoreOn(myTf2);
const myR3 = await myScoreOn(myTf3);
const myLabel = (_s) => _s === null ? '-' : (_s >= 2 ? 'Bull' : (_s === 1 ? 'Lean bull' : (_s === 0 ? 'Mixed' : (_s === -1 ? 'Lean bear' : 'Bear'))));
const myBg = (_s) => _s !== null && _s > 0 ? '#15803d' : (_s !== null && _s < 0 ? '#b91c1c' : '#64748b');
const myLast = close.length - 1;
const myRow = (_t, _r) => ({ cells: [
	{ text: _t, color: 'white', background_color: '#222222' },
	{ text: _r.tu[myLast] === 1 ? 'Up' : 'Down', color: 'white', background_color: _r.tu[myLast] === 1 ? '#15803d' : '#b91c1c' },
	{ text: _r.mu[myLast] === 1 ? 'Up' : 'Down', color: 'white', background_color: _r.mu[myLast] === 1 ? '#15803d' : '#b91c1c' },
	{ text: myLabel(_r.s[myLast]), color: 'white', background_color: myBg(_r.s[myLast]) }
] });
paint_overlay('VASA MTF Table', { position: myTablePos }, {
	rows: [
		{ cells: ['TF', 'Trend', 'Mom', 'Rating'].map(_t => ({ text: _t, color: 'white', background_color: '#16233b' })) },
		myRow(myTf1, myR1), myRow(myTf2, myR2), myRow(myTf3, myR3)
	]
});
register_signal(myR1.tu.map(_v => _v === 1), 'Timeframe 1 Trend Up');
register_signal(myR1.mu.map(_v => _v === 1), 'Timeframe 1 Momentum Up');
register_signal(myR2.tu.map(_v => _v === 1), 'Timeframe 2 Trend Up');
register_signal(myR2.mu.map(_v => _v === 1), 'Timeframe 2 Momentum Up');
register_signal(myR3.tu.map(_v => _v === 1), 'Timeframe 3 Trend Up');
register_signal(myR3.mu.map(_v => _v === 1), 'Timeframe 3 Momentum Up');
register_signal(myR1.s.map(_s => _s !== null && _s >= 2), 'Timeframe 1 Bull Rating');
register_signal(myR1.s.map(_s => _s !== null && _s <= -2), 'Timeframe 1 Bear Rating');
register_signal(myR2.s.map(_s => _s !== null && _s >= 2), 'Timeframe 2 Bull Rating');
register_signal(myR2.s.map(_s => _s !== null && _s <= -2), 'Timeframe 2 Bear Rating');
register_signal(myR3.s.map(_s => _s !== null && _s >= 2), 'Timeframe 3 Bull Rating');
register_signal(myR3.s.map(_s => _s !== null && _s <= -2), 'Timeframe 3 Bear Rating');
register_signal(close.map((_c, _i) => [myR1, myR2, myR3].every(_r => _r.s[_i] !== null && _r.s[_i] >= 2)), 'All Timeframes Bull');
register_signal(close.map((_c, _i) => [myR1, myR2, myR3].every(_r => _r.s[_i] !== null && _r.s[_i] <= -2)), 'All Timeframes Bear');
