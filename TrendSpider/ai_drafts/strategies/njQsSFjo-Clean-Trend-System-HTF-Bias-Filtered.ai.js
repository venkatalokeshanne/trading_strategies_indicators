describe_indicator('Clean Trend System - HTF Bias Filtered', 'price');

// NOTE: Pine's strategy.position_size is approximated using the
// internal trendState variable (LONG_FIRED / SHORT_FIRED / NONE),
// since this is not a real strategy backtester with live position
// tracking. This should behave identically to the original logic
// because the state machine itself gates re-entries the same way
// position_size does in the source script.

const myTab = input.tab('Settings');
const myEmaFast = myTab.number('Fast EMA', 9, { min: 1, max: 200 });
const myEmaSlow = myTab.number('Slow EMA', 21, { min: 1, max: 300 });
const myEmaTrend = myTab.number('Trend EMA', 50, { min: 1, max: 500 });
const myRsiLen = myTab.number('RSI Length', 5, { min: 1, max: 100 });
const myAtrLen = myTab.number('ATR Length', 10, { min: 1, max: 100 });
const myBreakoutPeriod = myTab.number('Breakout Lookback Period', 20, { min: 1, max: 300 });

// === AUTO HTF RESOLUTION MAPPING ===
function myGetHtf(_myRes) {
	const myMap = {
		'1': '15', '2': '15', '3': '15', '5': '15',
		'10': '60',
		'15': '240', '20': '240', '30': '240', '45': '240',
		'60': 'D', '120': 'D', '180': 'D',
		'240': 'W', 'D': 'W', '1D': 'W'
	};
	return myMap[_myRes] || 'W';
}

const myHtf = myGetHtf(current.resolution);

const myHtfData = await request.history(current.ticker, myHtf);
assert(!myHtfData.error, `Error fetching HTF data: "${myHtfData.error}"`);

const myHtfEmaTrendRaw = ema(myHtfData.close, myEmaTrend);
const myHtfEmaFastRaw = ema(myHtfData.close, myEmaFast);
const myHtfEmaSlowRaw = ema(myHtfData.close, myEmaSlow);

// land HTF points onto the current time series, using 'ge' + constant
// interpolation to avoid repainting / future-looking data (same as
// request.security with lookahead_on approximated causally here)
const myHtfTrendLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEmaTrendRaw, time, 'ge'), 'constant'
);
const myHtfFastLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEmaFastRaw, time, 'ge'), 'constant'
);
const myHtfSlowLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfEmaSlowRaw, time, 'ge'), 'constant'
);
const myHtfCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myHtfData.close, time, 'ge'), 'constant'
);

const myHtfBullish = for_every(myHtfCloseLanded, myHtfTrendLanded, myHtfFastLanded, myHtfSlowLanded,
	(_c, _t, _f, _s) => _c > _t && _f > _s && _s > _t);
const myHtfBearish = for_every(myHtfCloseLanded, myHtfTrendLanded, myHtfFastLanded, myHtfSlowLanded,
	(_c, _t, _f, _s) => _c < _t && _f < _s && _s < _t);

// === LTF INDICATORS ===
const myEmaF = ema(close, myEmaFast);
const myEmaS = ema(close, myEmaSlow);
const myEmaT = ema(close, myEmaTrend);
const myVwapLine = vwap();
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

const myBullishTrend = for_every(close, myEmaT, myEmaF, myEmaS, (_c, _t, _f, _s) => _c > _t && _f > _s && _s > _t);
const myBearishTrend = for_every(close, myEmaT, myEmaF, myEmaS, (_c, _t, _f, _s) => _c < _t && _f < _s && _s < _t);

// === MOMENTUM FILTER ===
const myRocValue = roc(close, 9);
const myRocEma = ema(myRocValue, 5);
const myRocSD = stdev(myRocValue, 14);
const myMomentumZScore = for_every(myRocEma, myRocSD, (_e, _sd) => _sd !== 0 ? (_e / _sd) : 0);

// === SETUPS ===
const myPullbackToEmaLong = for_every(low, myEmaS, close, (_l, _s, _c) => _l <= _s && _c > _s);
const myPullbackToVwapLong = for_every(low, myVwapLine, close, (_l, _v, _c) => _l <= _v && _c > _v);
const myPullbackToEmaShort = for_every(high, myEmaS, close, (_h, _s, _c) => _h >= _s && _c < _s);
const myPullbackToVwapShort = for_every(high, myVwapLine, close, (_h, _v, _c) => _h >= _v && _c < _v);

const myHighestHighPrev = shift(highest(high, myBreakoutPeriod), 1);
const myLowestLowPrev = shift(lowest(low, myBreakoutPeriod), 1);

const myPrevClose = shift(close, 1);
const myPrevHighestHigh = shift(myHighestHighPrev, 1);
const myPrevLowestLow = shift(myLowestLowPrev, 1);

const myBreakoutLong = for_every(close, myHighestHighPrev, myPrevClose, myPrevHighestHigh,
	(_c, _hh, _pc, _phh) => _c > _hh && _pc <= _phh);
const myBreakoutShort = for_every(close, myLowestLowPrev, myPrevClose, myPrevLowestLow,
	(_c, _ll, _pc, _pll) => _c < _ll && _pc >= _pll);

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

const myBullishCandle = for_every(close, open, myPrevHigh, (_c, _o, _ph) => _c > _o && _c > _ph);
const myBearishCandle = for_every(close, open, myPrevLow, (_c, _o, _pl) => _c < _o && _c < _pl);

const myPrevRsi = shift(myRsi, 1);
const myRsiLong = for_every(myRsi, myPrevRsi, (_r, _pr) => _r > 45 && _r > _pr && _r < 75);
const myRsiShort = for_every(myRsi, myPrevRsi, (_r, _pr) => _r < 55 && _r < _pr && _r > 25);

// === RAW TRIGGERS ===
const myLongTrigger = for_every(
	myBullishTrend, myPullbackToEmaLong, myPullbackToVwapLong, myBullishCandle, myBreakoutLong, myRsiLong,
	(_bt, _pel, _pvl, _bc, _bl, _rl) => _bt && (((_pel || _pvl) && _bc) || _bl) && _rl
);
const myShortTrigger = for_every(
	myBearishTrend, myPullbackToEmaShort, myPullbackToVwapShort, myBearishCandle, myBreakoutShort, myRsiShort,
	(_bt, _pes, _pvs, _bc, _bs, _rs) => _bt && (((_pes || _pvs) && _bc) || _bs) && _rs
);

// === SEQUENTIAL STATE MACHINE (must run in order, cannot be vectorized) ===
const myLongSignalArr = series_of(false);
const myShortSignalArr = series_of(false);
let myTrendState = 'NONE';

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myTrendState === 'LONG_FIRED' && close[myIndex] < myEmaT[myIndex]) {
		myTrendState = 'NONE';
	}
	if (myTrendState === 'SHORT_FIRED' && close[myIndex] > myEmaT[myIndex]) {
		myTrendState = 'NONE';
	}

	const myLongOk = myLongTrigger[myIndex] && myTrendState !== 'LONG_FIRED' && !myHtfBearish[myIndex];
	const myShortOk = myShortTrigger[myIndex] && myTrendState !== 'SHORT_FIRED' && !myHtfBullish[myIndex];

	myLongSignalArr[myIndex] = myLongOk;
	myShortSignalArr[myIndex] = myShortOk;

	if (myLongOk) {
		myTrendState = 'LONG_FIRED';
	}
	if (myShortOk) {
		myTrendState = 'SHORT_FIRED';
	}
}

// === VISUALS ===
paint(myEmaF, { name: 'FastEMA', color: '#00bcd4', thickness: 2 });
paint(myEmaS, { name: 'SlowEMA', color: '#ff9800', thickness: 2 });
paint(myEmaT, { name: 'TrendEMA', color: '#9c27b0', thickness: 3 });
paint(myVwapLine, { name: 'VWAP', color: '#757575', thickness: 1 });

const myBuyMarks = for_every(myLongSignalArr, low, (_sig, _l) => _sig ? _l : null);
const mySellMarks = for_every(myShortSignalArr, high, (_sig, _h) => _sig ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#00e676' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#ff1744' });

register_signal(myLongSignalArr, 'Buy Signal');
register_signal(myShortSignalArr, 'Sell Signal');