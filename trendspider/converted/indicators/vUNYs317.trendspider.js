/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MHIDa Volume-Dry Pullback
 * Author       : MHIDa
 * Source URL   : https://www.tradingview.com/script/vUNYs317
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MHIDa Volume Dry Pullback_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact RSI; bgcolor not available; barcolor as gray candles;
 *   dry label as icon.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MHIDa Volume Dry Pullback_TV', 'price');
const myEmaGateLen = input.number('EMA gate', 50, { min: 2 });
const myEmaMeanLen = input.number('EMA mean', 20, { min: 2 });
const myVolMaLen = input.number('Volume average', 20, { min: 2 });
const myVolDryMult = input.number('Volume dry mult', 0.7, { min: 0.1, max: 1.0, step: 0.05 });
const myRsiLen = input.number('RSI length', 14, { min: 2 });
const myRsiDip = input.number('RSI in dip below', 45, { min: 1, max: 99 });
const myUseTurn = input.boolean('Require turn up', true);
const myEmaGate = ema(close, myEmaGateLen);
const myEmaMean = ema(close, myEmaMeanLen);
const myVolMa = sma(volume, myVolMaLen);
// pine-parity: ta.rsi uses SMA-seeded RMA of gains/losses
const myRma = (_src, _n) => {
	let myAcc = null, mySeen = 0, mySeed = 0;
	return _src.map(_v => {
		if (_v === null) return myAcc;
		if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === _n) myAcc = mySeed / _n; return myAcc; }
		myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc;
	});
};
const myG = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(_c - close[_i - 1], 0)), myRsiLen);
const myL = myRma(close.map((_c, _i) => _i === 0 ? null : Math.max(close[_i - 1] - _c, 0)), myRsiLen);
const myRsi = myG.map((_g, _i) => (_g === null || myL[_i] === null) ? null : (myL[_i] === 0 ? 100 : 100 - 100 / (1 + _g / myL[_i])));
const myInBull = close.map((_c, _i) => myEmaGate[_i] !== null && _c > myEmaGate[_i]);
const myPullback = close.map((_c, _i) => myEmaMean[_i] !== null && _c < myEmaMean[_i] && myRsi[_i] !== null && myRsi[_i] < myRsiDip);
const myVolDry = close.map((_c, _i) => myVolMa[_i] !== null && volume[_i] < myVolMa[_i] * myVolDryMult);
const myTurnUp = close.map((_c, _i) => !myUseTurn || (_i > 0 && _c > close[_i - 1]));
const myFlag = close.map((_c, _i) => myInBull[_i] && myPullback[_i] && myVolDry[_i] && myTurnUp[_i]);
paint(myEmaGate, { name: 'EMA gate', color: 'teal', thickness: 2 });
paint(myEmaMean, { name: 'EMA mean', color: 'orange', thickness: 1 });
paint(myFlag.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Dry Pullback Mark', style: 'labels_below', color: 'lime' });
color_candles(close.map((_c, _i) => (myPullback[_i] && myVolDry[_i]) ? 'gray' : null));
register_signal(myFlag, 'Dry Volume Pullback Signal');
register_signal(myInBull, 'Bull Context');
