/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : VWAP Slope Trend Filter
 * Author       : leogaa
 * Source URL   : https://www.tradingview.com/script/OkbSIHvu-VWAP-Slope-Trend-Filter
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : VWAP Slope Trend Filter_TV
 *
 * Deviations from the original: Reviewed AI draft; Pine-exact ATR; VWAP resets per calendar day; background
 *   colouring (bgcolor) and LONG/SHORT text not available - triangle icons used.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('VWAP Slope Trend Filter_TV', 'price');
const mySrcName = input.select('VWAP Source', 'hlc3', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const mySlopeLength = input.number('Slope Length', 5, { min: 1, max: 500 });
const myMinSlope = input.number('Minimum Slope', 0.03, { min: -10, max: 10, step: 0.01 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myShowSignals = input.boolean('Show Signals', true);
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
// ta.vwap resets every session (here: calendar day, exchange time)
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
let mySV = 0, myV = 0;
const myVwap = mySrc.map((_p, _i) => {
	if (_i === 0 || myDayKey[_i] !== myDayKey[_i - 1]) { mySV = 0; myV = 0; }
	mySV += _p * volume[_i]; myV += volume[_i];
	return myV > 0 ? mySV / myV : null;
});
// ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtr = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLength) myAcc = mySeed / myAtrLength; return myAcc; }
	myAcc = (myAcc * (myAtrLength - 1) + _v) / myAtrLength; return myAcc;
});
const myNorm = myVwap.map((_v, _i) => {
	const myPast = _i >= mySlopeLength ? myVwap[_i - mySlopeLength] : null;
	if (_v === null || myPast === null || myAtr[_i] === null) return null;
	return myAtr[_i] !== 0 ? (_v - myPast) / myAtr[_i] : 0;
});
const myBull = myNorm.map(_s => _s !== null && _s > myMinSlope);
const myBear = myNorm.map(_s => _s !== null && _s < -myMinSlope);
paint(myVwap, { name: 'VWAP', color: myBull.map((_b, _i) => _b ? 'lime' : (myBear[_i] ? 'red' : 'gray')), thickness: 3 });
const myBullStart = myBull.map((_b, _i) => _b && !(_i > 0 && myBull[_i - 1]));
const myBearStart = myBear.map((_b, _i) => _b && !(_i > 0 && myBear[_i - 1]));
paint(myBullStart.map(_s => (myShowSignals && _s) ? constants.icons.triangle_up : null), { name: 'Bull Start Mark', style: 'labels_below', color: 'lime' });
paint(myBearStart.map(_s => (myShowSignals && _s) ? constants.icons.triangle_down : null), { name: 'Bear Start Mark', style: 'labels_above', color: 'red' });
register_signal(myBullStart, 'VWAP Bull Trend Start');
register_signal(myBearStart, 'VWAP Bear Trend Start');
register_signal(myBull, 'VWAP Bull Trend Active');
register_signal(myBear, 'VWAP Bear Trend Active');
