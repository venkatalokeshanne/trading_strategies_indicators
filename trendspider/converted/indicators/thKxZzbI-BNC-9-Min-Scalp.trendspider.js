/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BNC Contrarian
 * Author       : LeClair6754
 * Source URL   : https://www.tradingview.com/script/thKxZzbI-BNC-9-Min-Scalp
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BNC Contrarian_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI/stoch/EMA; weekly RSI of the last completed weekly
 *   bar (no look-ahead); level styles/fills via clouds; table via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BNC Contrarian_TV', 'lower');
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRsiOf = (_c, _n) => {
	const myG = myRma(_c.map((_v, _i) => _i === 0 ? null : Math.max(_v - _c[_i - 1], 0)), _n);
	const myL = myRma(_c.map((_v, _i) => _i === 0 ? null : Math.max(_c[_i - 1] - _v, 0)), _n);
	return myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
};
const myEmaOf = (_s, _n) => {
	let myAcc = null, myCnt = 0, mySum = 0;
	const myAlpha = 2 / (_n + 1);
	return _s.map(_v => {
		if (_v === null) return null;
		if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; }
		myAcc = myAlpha * _v + (1 - myAlpha) * myAcc; return myAcc;
	});
};
const myRsi = myRsiOf(close, 14);
// ta.stoch(rsi, rsi, rsi, 14)
const myStoch = myRsi.map((_v, _i) => {
	if (_i < 14 || _v === null) return null;
	let myHi = -Infinity, myLo = Infinity;
	for (let myK = _i - 13; myK <= _i; myK += 1) { if (myRsi[myK] === null) return null; myHi = Math.max(myHi, myRsi[myK]); myLo = Math.min(myLo, myRsi[myK]); }
	return myHi === myLo ? null : 100 * (_v - myLo) / (myHi - myLo);
});
const mySk = myEmaOf(myStoch, 3);
const mySkNorm = mySk.map(_s => _s === null ? null : (_s > 90 ? 100 : (_s < 10 ? 0 : 50)));
const myEma20 = myEmaOf(close, 20);
const myDev = close.map((_c, _i) => myEma20[_i] === null ? null : Math.min(Math.max((_c - myEma20[_i]) / myEma20[_i] * 500 + 50, 0), 100));
const myWeekly = await request.history(current.ticker, 'W');
assert(!myWeekly.error, 'Error fetching weekly data: ' + myWeekly.error);
const myWeeklyRsi = myRsiOf(myWeekly.close, 14);
// the weekly RSI of the last COMPLETED weekly bar (shifted one bar, L23)
const myRsiW = interpolate_sparse_series(land_points_onto_series(myWeekly.time, myWeeklyRsi.map((_v, _k) => _k ? myWeeklyRsi[_k - 1] : null), time, 'le'), 'constant');
const myEmotion = close.map((_c, _i) => (myRsiW[_i] === null || myRsi[_i] === null || mySkNorm[_i] === null || myDev[_i] === null) ? null : myRsiW[_i] * 0.40 + myRsi[_i] * 0.25 + mySkNorm[_i] * 0.25 + myDev[_i] * 0.10);
let myState = 0;
const mySell = [], myBuy = [];
myEmotion.forEach(_e => {
	const myFomo = _e !== null && _e > 75, myPanic = _e !== null && _e < 25, myNeutral = _e !== null && _e >= 35 && _e <= 65;
	if (myState === 0 && myFomo) myState = 1;
	if (myState === 0 && myPanic) myState = 2;
	const myS = myState === 1 && !myFomo && _e !== null;
	const myB = myState === 2 && !myPanic && _e !== null;
	mySell.push(myS); myBuy.push(myB);
	if (myS || myB) myState = 3;
	if (myState === 3 && myNeutral) myState = 0;
});
const myColor = myEmotion.map(_e => _e === null ? 'gray' : (_e > 75 ? '#ff0000' : (_e > 60 ? '#ffa500' : (_e > 50 ? '#ffd400' : (_e > 40 ? '#008080' : (_e > 25 ? '#00ffff' : '#00ff00'))))));
paint(myEmotion, { name: 'Emotion', style: 'histogram', color: myColor });
paint(myEmotion, { name: 'Emotion Line', color: myColor, thickness: 1 });
paint(horizontal_line(75), { name: 'Do Not Long', color: 'rgba(255,0,0,0.8)' });
paint(horizontal_line(50), { name: 'Neutral', color: 'rgba(128,128,128,0.4)' });
paint(horizontal_line(25), { name: 'Do Not Short', color: 'rgba(0,255,0,0.8)' });
color_cloud(horizontal_line(100), horizontal_line(75), 'rgba(255,0,0,0.12)', 'rgba(255,0,0,0.12)', 'Hot Up', 'Hot Dn');
color_cloud(horizontal_line(25), horizontal_line(0), 'rgba(0,255,0,0.12)', 'rgba(0,255,0,0.12)', 'Cold Up', 'Cold Dn');
const myLast = myEmotion[myEmotion.length - 1];
const myOk = myLast !== null;
const myZone = !myOk ? 'n/a' : (myLast > 75 ? 'DO NOT LONG' : (myLast > 55 ? 'CAUTION' : (myLast > 45 ? 'NEUTRAL' : (myLast > 25 ? 'CAUTION' : 'DO NOT SHORT'))));
const myAction = !myOk ? 'n/a' : (myLast > 75 ? 'WAIT -> SELL' : (myLast < 25 ? 'WAIT -> BUY' : 'NO EDGE'));
const myBg = !myOk ? '#333333' : (myLast > 75 ? '#cc0000' : (myLast > 55 ? '#cc7a00' : (myLast > 45 ? '#666666' : (myLast > 25 ? '#007a7a' : '#00cc00'))));
paint_overlay('Emotion Table', { position: 'top_left' }, {
	rows: [
		{ cells: [{ text: 'EMOTION', color: '#cccccc', background_color: '#1a1a1a' }, { text: myOk ? String(Math.round(myLast)) : 'n/a', color: '#ffffff', background_color: '#1a1a1a' }] },
		{ cells: [{ text: 'ZONE', color: '#cccccc', background_color: '#1a1a1a' }, { text: myZone, color: '#ffffff', background_color: myBg }] },
		{ cells: [{ text: 'ACTION', color: '#cccccc', background_color: '#1a1a1a' }, { text: myAction, color: '#ffffff', background_color: myBg }] }
	]
});
register_signal(mySell, 'Fade FOMO Sell Signal');
register_signal(myBuy, 'Fade Panic Buy Signal');
