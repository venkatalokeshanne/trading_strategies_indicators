/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BTST Breakout & Momentum Screener (3:15-3:25 PM Only)
 * Author       : rahulbalaji4574
 * Source URL   : https://www.tradingview.com/script/tFig8fxc-BTST-Breakout-Momentum-Screener-3-15-3-25-PM-Only
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BTST Breakout Momentum Screener_TV
 *
 * Deviations from the original: Reviewed AI draft; 15:15-15:25 window in Asia/Kolkata via moment-timezone (never
 *   active on non-Indian sessions); Pine-exact RSI; dashboard via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BTST Breakout Momentum Screener_TV', 'price');
const myMoment = library('moment-timezone');
const myRsiPeriod = input.number('RSI Period', 14, { min: 1, max: 200 });
const myRsiThreshold = input.number('Min RSI Level', 60, { min: 0, max: 100 });
const myVolMult = input.number('Volume Multiplier', 1.5, { min: 0.1, max: 10 });
const myHodBuffer = input.number('Near Day High Buffer', 0.992, { min: 0.5, max: 1, step: 0.001 });
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiPeriod);
const myL = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiPeriod);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
const myEma20 = ema(close, 20);
const myVolSma = sma(volume, 20);
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
let myHigh = null, mySV = 0, myV = 0;
const mySessionHigh = [];
const myVwap = [];
for (let myI = 0; myI < close.length; myI += 1) {
	const myNew = myI === 0 || myDayKey[myI] !== myDayKey[myI - 1];
	myHigh = myNew ? high[myI] : Math.max(myHigh, high[myI]);
	if (myNew) { mySV = 0; myV = 0; }
	mySV += (high[myI] + low[myI] + close[myI]) / 3 * volume[myI]; myV += volume[myI];
	mySessionHigh.push(myHigh);
	myVwap.push(myV > 0 ? mySV / myV : null);
}
// Pine session "1515-1525" in Asia/Kolkata (end exclusive)
const myInWindow = time.map(_t => { const myT = myMoment.tz(_t * 1000, 'Asia/Kolkata'); const myM = myT.hours() * 60 + myT.minutes(); return myM >= 915 && myM < 925; });
const myNear = close.map((_c, _i) => _c >= mySessionHigh[_i] * myHodBuffer);
const mySpike = close.map((_c, _i) => myVolSma[_i] !== null && volume[_i] > myVolSma[_i] * myVolMult);
const myAboveVwap = close.map((_c, _i) => myVwap[_i] !== null && _c > myVwap[_i]);
const myAboveEma = close.map((_c, _i) => myEma20[_i] !== null && _c > myEma20[_i]);
const myRsiBull = myRsi.map(_r => _r !== null && _r >= myRsiThreshold);
const mySignal = close.map((_c, _i) => myInWindow[_i] && myNear[_i] && mySpike[_i] && myAboveVwap[_i] && myAboveEma[_i] && myRsiBull[_i]);
paint(myEma20, { name: 'EMA 20', color: 'orange', thickness: 1 });
paint(mySignal.map(_s => _s ? constants.icons.triangle_up : null), { name: 'BTST Buy', style: 'labels_below', color: 'green' });
const myLast = close.length - 1;
const myRow = (_a, _b, _bg) => ({ cells: [{ text: _a, color: 'white', background_color: '#111111' }, { text: _b, color: 'white', background_color: _bg }] });
const myYn = (_f) => _f ? 'YES' : 'NO';
paint_overlay('BTST Dashboard', { position: 'top_right' }, {
	rows: [
		myRow('BTST Condition', 'Status', '#000080'),
		myRow('Time Window 1515-1525', myInWindow[myLast] ? 'ACTIVE' : 'INACTIVE', myInWindow[myLast] ? 'green' : 'gray'),
		myRow('Near Day High', myYn(myNear[myLast]), myNear[myLast] ? 'green' : 'red'),
		myRow('Volume Surge', myYn(mySpike[myLast]), mySpike[myLast] ? 'green' : 'red'),
		myRow('Above VWAP and 20 EMA', myYn(myAboveVwap[myLast] && myAboveEma[myLast]), (myAboveVwap[myLast] && myAboveEma[myLast]) ? 'green' : 'red'),
		myRow('RSI above threshold', myYn(myRsiBull[myLast]), myRsiBull[myLast] ? 'green' : 'red')
	]
});
register_signal(mySignal, 'BTST Buy Signal');
register_signal(myInWindow, 'In BTST Time Window');
