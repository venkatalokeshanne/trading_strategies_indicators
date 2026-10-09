/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MTF Alligator State
 * Author       : muhammadsollihinehsan
 * Source URL   : https://www.tradingview.com/script/6W4fATUz-MTF-Alligator-State
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MTF Alligator State_TV
 *
 * Deviations from the original: Always uses the closed HTF bar (Pine default); table is a static image of the last
 *   bar; Pine own-language labels in English
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MTF Alligator State_TV', 'price');
const mySrcName = input.select('Source', 'hl2', ['close', 'hl2', 'hlc3', 'ohlc4', 'open', 'high', 'low']);
const myJawLen = input.number('Jaw Length', 13, { min: 1, max: 200 });
const myJawOff = input.number('Jaw Offset', 8, { min: 0, max: 50 });
const myTeethLen = input.number('Teeth Length', 8, { min: 1, max: 200 });
const myTeethOff = input.number('Teeth Offset', 5, { min: 0, max: 50 });
const myLipsLen = input.number('Lips Length', 5, { min: 1, max: 200 });
const myLipsOff = input.number('Lips Offset', 3, { min: 0, max: 50 });
const myTablePos = input.select('Table position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
// SMA-seeded RMA (Pine ta.rma)
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
const myLag = (_s, _o) => _s.map((_v, _i) => _i - _o >= 0 ? _s[_i - _o] : null);
const myStateOn = async (_res) => {
	const myD = await request.history(current.ticker, _res);
	assert(!myD.error, 'Error fetching ' + _res + ' data: ' + myD.error);
	const mySrc = myD.close.map((_c, _i) => {
		const myO = myD.open[_i], myH = myD.high[_i], myL = myD.low[_i];
		if (mySrcName === 'open') return myO;
		if (mySrcName === 'high') return myH;
		if (mySrcName === 'low') return myL;
		if (mySrcName === 'hl2') return (myH + myL) / 2;
		if (mySrcName === 'hlc3') return (myH + myL + _c) / 3;
		if (mySrcName === 'ohlc4') return (myO + myH + myL + _c) / 4;
		return _c;
	});
	const myJaw = myLag(myRma(mySrc, myJawLen), myJawOff), myTeeth = myLag(myRma(mySrc, myTeethLen), myTeethOff), myLips = myLag(myRma(mySrc, myLipsLen), myLipsOff);
	const mySt = myD.close.map((_c, _i) => {
		if (myJaw[_i] === null || myTeeth[_i] === null || myLips[_i] === null) return null;
		if (myLips[_i] > myTeeth[_i] && myTeeth[_i] > myJaw[_i] && _c > myLips[_i]) return 1;
		if (myLips[_i] < myTeeth[_i] && myTeeth[_i] < myJaw[_i] && _c < myLips[_i]) return -1;
		return 0;
	});
	// closed HTF bar only (the Pine default st[1]): the previous HTF bar's state is shown for the whole current bar
	const myConf = mySt.map((_v, _i) => _i ? mySt[_i - 1] : null);
	return interpolate_sparse_series(land_points_onto_series(myD.time, myConf, time, 'ge'), 'constant');
};
const myW1 = await myStateOn('W');
const myD1 = await myStateOn('D');
const myH4 = await myStateOn('240');
const myH1 = await myStateOn('60');
const myTxt = (_s) => _s === 1 ? 'BUY' : (_s === -1 ? 'SELL' : 'SIDEWAYS');
const myCol = (_s) => _s === 1 ? '#1b9e4b' : (_s === -1 ? '#d1392b' : '#808080');
const myLast = close.length - 1;
const myRow = (_n, _s) => ({ cells: [{ text: _n, color: 'white', background_color: '#333333' }, { text: myTxt(_s[myLast]), color: 'white', background_color: myCol(_s[myLast]) }] });
paint_overlay('Alligator MTF Table', { position: myTablePos }, {
	rows: [
		{ cells: [{ text: 'TF', color: 'white', background_color: 'black' }, { text: 'STATE', color: 'white', background_color: 'black' }] },
		myRow('W1', myW1), myRow('D1', myD1), myRow('H4', myH4), myRow('H1', myH1)
	]
});
register_signal(myW1.map(_s => _s === 1), 'W1 Buy');
register_signal(myW1.map(_s => _s === -1), 'W1 Sell');
register_signal(myD1.map(_s => _s === 1), 'D1 Buy');
register_signal(myD1.map(_s => _s === -1), 'D1 Sell');
register_signal(myH4.map(_s => _s === 1), 'H4 Buy');
register_signal(myH4.map(_s => _s === -1), 'H4 Sell');
register_signal(myH1.map(_s => _s === 1), 'H1 Buy');
register_signal(myH1.map(_s => _s === -1), 'H1 Sell');
register_signal(close.map((_c, _i) => myW1[_i] === 1 && myD1[_i] === 1 && myH4[_i] === 1 && myH1[_i] === 1), 'All Timeframes Buy');
register_signal(close.map((_c, _i) => myW1[_i] === -1 && myD1[_i] === -1 && myH4[_i] === -1 && myH1[_i] === -1), 'All Timeframes Sell');
