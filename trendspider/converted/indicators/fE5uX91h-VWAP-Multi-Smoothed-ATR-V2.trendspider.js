/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VWAP-Multi Smoothed ATR V2
 * Author       : zihang1017
 * Source URL   : https://www.tradingview.com/script/fE5uX91h-VWAP-Multi-Smoothed-ATR-V2
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VWAP Multi Smoothed ATR V2_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ATR/EMA; ATR timeframe lagged one completed bar; VWAP
 *   resets per calendar day; needs long history for 2750-bar lengths.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VWAP Multi Smoothed ATR V2_TV', 'price');
const myTfName = input.select('ATR Timeframe', '5', ['1', '5', '15', '30', '60', '240', 'D']);
const myAtrLength = input.number('ATR Length', 2750, { min: 1, max: 10000 });
const myAtrSmooth = input.number('ATR Smooth Length', 2750, { min: 1, max: 10000 });
const myMult1 = input.number('ATR Mult 1', 1.0, { min: 0, max: 20, step: 0.1 });
const myMult2 = input.number('ATR Mult 2', 1.85, { min: 0, max: 20, step: 0.1 });
const myMult3 = input.number('ATR Mult 3', 3.125, { min: 0, max: 20, step: 0.1 });
// ta.vwap(hlc3): resets every session (here: calendar day, exchange time)
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
let mySV = 0, myV = 0;
const myVwap = close.map((_c, _i) => {
	if (_i === 0 || myDayKey[_i] !== myDayKey[_i - 1]) { mySV = 0; myV = 0; }
	mySV += (high[_i] + low[_i] + _c) / 3 * volume[_i]; myV += volume[_i];
	return myV > 0 ? mySV / myV : null;
});
const myHtf = await request.history(current.ticker, myTfName);
assert(!myHtf.error, 'Error fetching ATR timeframe data: ' + myHtf.error);
// pine-parity: ta.atr = SMA-seeded RMA of true range; ta.ema seeded with an SMA of the first valid values
const myTr = myHtf.high.map((_h, _i) => _i === 0 ? _h - myHtf.low[0] : Math.max(_h - myHtf.low[_i], Math.abs(_h - myHtf.close[_i - 1]), Math.abs(myHtf.low[_i] - myHtf.close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLength) myAcc = mySeed / myAtrLength; return myAcc; }
	myAcc = (myAcc * (myAtrLength - 1) + _v) / myAtrLength; return myAcc;
});
let myEma = null, myESeen = 0, myESum = 0;
const myAlpha = 2 / (myAtrSmooth + 1);
const mySmooth = myAtr.map(_v => {
	if (_v === null) return null;
	if (myEma === null) { myESum += _v; myESeen += 1; if (myESeen === myAtrSmooth) myEma = myESum / myAtrSmooth; return myEma; }
	myEma = myAlpha * _v + (1 - myAlpha) * myEma; return myEma;
});
// value of the last COMPLETED higher-timeframe bar (shifted one bar, L23)
const mySmoothAtr = interpolate_sparse_series(land_points_onto_series(myHtf.time, mySmooth.map((_v, _k) => _k ? mySmooth[_k - 1] : null), time, 'le'), 'constant');
const myBand = (_m, _sign) => myVwap.map((_v, _i) => (_v === null || mySmoothAtr[_i] === null) ? null : _v + _sign * _m * mySmoothAtr[_i]);
const myU1 = myBand(myMult1, 1), myL1 = myBand(myMult1, -1);
const myU2 = myBand(myMult2, 1), myL2 = myBand(myMult2, -1);
const myU3 = myBand(myMult3, 1), myL3 = myBand(myMult3, -1);
paint(myVwap, { name: 'VWAP', color: '#2962FF', thickness: 2 });
paint(myU1, { name: 'Upper 1 ATR', color: '#26A69A' });
paint(myL1, { name: 'Lower 1 ATR', color: '#26A69A' });
paint(myU2, { name: 'Upper 2 ATR', color: '#FF9800' });
paint(myL2, { name: 'Lower 2 ATR', color: '#FF9800' });
paint(myU3, { name: 'Upper 3 ATR', color: '#9C27B0' });
paint(myL3, { name: 'Lower 3 ATR', color: '#9C27B0' });
const myPrevClose = shift(close, 1);
const myXUp = (_b) => { const myPrevB = shift(_b, 1); return for_every(close, _b, myPrevClose, myPrevB, (_c, _x, _pc, _px) => _x !== null && _px !== null && _pc <= _px && _c > _x); };
const myXDn = (_b) => { const myPrevB = shift(_b, 1); return for_every(close, _b, myPrevClose, myPrevB, (_c, _x, _pc, _px) => _x !== null && _px !== null && _pc >= _px && _c < _x); };
register_signal(myXUp(myU1), 'Cross Above Upper 1 ATR');
register_signal(myXDn(myL1), 'Cross Below Lower 1 ATR');
register_signal(myXUp(myU2), 'Cross Above Upper 2 ATR');
register_signal(myXDn(myL2), 'Cross Below Lower 2 ATR');
register_signal(myXUp(myU3), 'Cross Above Upper 3 ATR');
register_signal(myXDn(myL3), 'Cross Below Lower 3 ATR');
