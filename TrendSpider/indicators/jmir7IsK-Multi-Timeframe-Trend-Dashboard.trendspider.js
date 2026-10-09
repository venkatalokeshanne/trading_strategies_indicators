/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Multi-Timeframe Trend Dashboard Fixed v6
 * Author       : sarath1128
 * Source URL   : https://www.tradingview.com/script/jmir7IsK-Multi-Timeframe-Trend-Dashboard
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Multi Timeframe Trend Dashboard_TV
 *
 * Deviations from the original: Table is a static image of the developing bar of each timeframe; signals use the
 *   last completed bar; timeframes chosen from a list
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Multi Timeframe Trend Dashboard_TV', 'price');
const myTfs = ['5', '15', '30', '60', '120', '240', 'D', 'W'];
const myTf1 = input.select('Timeframe 1', '15', myTfs);
const myTf2 = input.select('Timeframe 2', '60', myTfs);
const myTf3 = input.select('Timeframe 3', '240', myTfs);
const myTf4 = input.select('Timeframe 4', 'D', myTfs);
const myFastLen = input.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 50, { min: 1, max: 500 });
const myAdxLen = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxCut = input.number('ADX Strong Cutoff', 20, { min: 1, max: 100 });
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; return _s.map(_v => { if (_v === null) return null; if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
// ta.dmi(len, len): DI+, DI-, ADX
const myState = async (_res) => {
	const myD = await request.history(current.ticker, _res);
	assert(!myD.error, 'Error fetching ' + _res + ' data: ' + myD.error);
	const myH = myD.high, myL = myD.low, myC = myD.close;
	const myTr = myH.map((_h, _i) => _i === 0 ? _h - myL[0] : Math.max(_h - myL[_i], Math.abs(_h - myC[_i - 1]), Math.abs(myL[_i] - myC[_i - 1])));
	const myUp = myH.map((_h, _i) => _i === 0 ? null : _h - myH[_i - 1]);
	const myDn = myL.map((_l, _i) => _i === 0 ? null : myL[_i - 1] - _l);
	const myPdm = myUp.map((_u, _i) => _u === null ? null : (_u > myDn[_i] && _u > 0 ? _u : 0));
	const myMdm = myDn.map((_d, _i) => _d === null ? null : (_d > myUp[_i] && _d > 0 ? _d : 0));
	const myTrr = myRma(myTr, myAdxLen), myPr = myRma(myPdm, myAdxLen), myMr = myRma(myMdm, myAdxLen);
	const myPlus = myTrr.map((_t, _i) => (_t === null || _t === 0 || myPr[_i] === null) ? null : 100 * myPr[_i] / _t);
	const myMinus = myTrr.map((_t, _i) => (_t === null || _t === 0 || myMr[_i] === null) ? null : 100 * myMr[_i] / _t);
	const myDx = myPlus.map((_p, _i) => (_p === null || myMinus[_i] === null) ? null : Math.abs(_p - myMinus[_i]) / ((_p + myMinus[_i]) === 0 ? 1 : (_p + myMinus[_i])));
	const myAdx = myRma(myDx, myAdxLen).map(_v => _v === null ? null : 100 * _v);
	const myEf = myEma(myC, myFastLen), myEs = myEma(myC, mySlowLen);
	const myDir = myC.map((_c, _i) => {
		if (myEf[_i] === null || myEs[_i] === null || myPlus[_i] === null || myMinus[_i] === null) return 0;
		if (_c > myEf[_i] && myEf[_i] > myEs[_i] && myPlus[_i] > myMinus[_i]) return 1;
		if (_c < myEf[_i] && myEf[_i] < myEs[_i] && myMinus[_i] > myPlus[_i]) return -1;
		return 0;
	});
	const myStrong = myAdx.map(_a => _a !== null && _a > myAdxCut ? 1 : 0);
	// signals use the last completed HTF bar
	const myLand = (_a) => interpolate_sparse_series(land_points_onto_series(myD.time, _a.map((_v, _k) => _k ? _a[_k - 1] : null), time, 'ge'), 'constant');
	return { dirNow: myDir[myDir.length - 1], strongNow: myStrong[myStrong.length - 1] === 1, dir: myLand(myDir), strong: myLand(myStrong) };
};
const myS1 = await myState(myTf1);
const myS2 = await myState(myTf2);
const myS3 = await myState(myTf3);
const myS4 = await myState(myTf4);
const myRow = (_n, _tf, _s) => {
	const myTxt = _s.dirNow === 1 ? (_s.strongNow ? 'STRONG BULL' : 'WEAK BULL') : (_s.dirNow === -1 ? (_s.strongNow ? 'STRONG BEAR' : 'WEAK BEAR') : 'CONSOLIDATING');
	const myBg = _s.dirNow === 1 ? (_s.strongNow ? '#008000' : '#2ECC71') : (_s.dirNow === -1 ? (_s.strongNow ? '#FF0000' : '#800000') : '#808080');
	return { cells: [{ text: 'TF ' + _n + ' (' + _tf + ')', color: 'white', background_color: '#222222' }, { text: myTxt, color: 'white', background_color: myBg }] };
};
paint_overlay('Trend Dashboard Table', { position: 'bottom_right' }, {
	rows: [
		{ cells: [{ text: 'TIMEFRAME', color: 'yellow', background_color: 'black' }, { text: 'TREND STATE', color: 'yellow', background_color: 'black' }] },
		myRow(1, myTf1, myS1), myRow(2, myTf2, myS2), myRow(3, myTf3, myS3), myRow(4, myTf4, myS4)
	]
});
register_signal(myS1.dir.map(_d => _d === 1), 'TF1 Bull');
register_signal(myS1.dir.map(_d => _d === -1), 'TF1 Bear');
register_signal(myS1.strong.map(_v => _v === 1), 'TF1 Strong Trend');
register_signal(myS2.dir.map(_d => _d === 1), 'TF2 Bull');
register_signal(myS2.dir.map(_d => _d === -1), 'TF2 Bear');
register_signal(myS2.strong.map(_v => _v === 1), 'TF2 Strong Trend');
register_signal(myS3.dir.map(_d => _d === 1), 'TF3 Bull');
register_signal(myS3.dir.map(_d => _d === -1), 'TF3 Bear');
register_signal(myS3.strong.map(_v => _v === 1), 'TF3 Strong Trend');
register_signal(myS4.dir.map(_d => _d === 1), 'TF4 Bull');
register_signal(myS4.dir.map(_d => _d === -1), 'TF4 Bear');
register_signal(myS4.strong.map(_v => _v === 1), 'TF4 Strong Trend');
