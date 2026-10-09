/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Flow Bias — Volume Weighted
 * Author       : jaymesantosneto
 * Source URL   : https://www.tradingview.com/script/vrVMfkBW-Flow-Bias-Volume-Weighted
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Flow Bias VWAP Cloud_TV
 *
 * Deviations from the original: VWAP resets per calendar day (exchange time); cloud drawn as three null-gated
 *   clouds.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Flow Bias VWAP Cloud_TV', 'price');
const mySmoothLen = input.number('Smoothing', 5, { min: 1, max: 200 });
const myDirectionLen = input.number('Direction Sens.', 3, { min: 1, max: 200 });
const myNeutralATR = input.number('Neutral Zone ATR', 0.03, { min: 0, max: 5, step: 0.01 });
// ta.vwap(src): session (here: calendar day, exchange time) anchored volume-weighted average
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
const myVwapOf = (_src) => {
	let mySV = 0, myV = 0;
	return _src.map((_p, _i) => {
		if (_i === 0 || myDayKey[_i] !== myDayKey[_i - 1]) { mySV = 0; myV = 0; }
		mySV += _p * volume[_i]; myV += volume[_i];
		return myV > 0 ? mySV / myV : null;
	});
};
const mySmoothHigh = vwma(myVwapOf(high), mySmoothLen);
const mySmoothLow = vwma(myVwapOf(low), mySmoothLen);
const myMid = mySmoothHigh.map((_h, _i) => (_h === null || mySmoothLow[_i] === null) ? null : (_h + mySmoothLow[_i]) / 2);
// ta.atr(14) = RMA (SMA-seeded) of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === 14) myAcc = mySeed / 14; return myAcc; }
	myAcc = (myAcc * 13 + _v) / 14; return myAcc;
});
const myState = myMid.map((_m, _i) => {
	const myPast = _i >= myDirectionLen ? myMid[_i - myDirectionLen] : null;
	if (_m === null || myPast === null || myAtr[_i] === null) return 0;
	const myZone = myAtr[_i] * myNeutralATR;
	const mySlope = _m - myPast;
	return mySlope > myZone ? 1 : (mySlope < -myZone ? -1 : 0);
});
const myGateTo = (_s, _st) => _s.map((_v, _i) => myState[_i] === _st ? _v : null);
color_cloud(myGateTo(mySmoothHigh, 1), myGateTo(mySmoothLow, 1), 'rgba(33,150,243,0.45)', 'rgba(33,150,243,0.45)', 'Bull Up', 'Bull Dn');
color_cloud(myGateTo(mySmoothHigh, -1), myGateTo(mySmoothLow, -1), 'rgba(239,83,80,0.45)', 'rgba(239,83,80,0.45)', 'Bear Up', 'Bear Dn');
color_cloud(myGateTo(mySmoothHigh, 0), myGateTo(mySmoothLow, 0), 'rgba(158,158,158,0.45)', 'rgba(158,158,158,0.45)', 'Neutral Up', 'Neutral Dn');
register_signal(myState.map(_s => _s === 1), 'Flow Bias Bullish');
register_signal(myState.map(_s => _s === -1), 'Flow Bias Bearish');
