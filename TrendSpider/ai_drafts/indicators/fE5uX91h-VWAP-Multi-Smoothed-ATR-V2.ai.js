describe_indicator('VWAP Multi Smoothed ATR V2', 'price');

// NOTE: TradingView's ta.vwap() resets at the start of each session
// (exchange trading day). TrendSpider's vwap() function computes a
// running VWAP from a given candle index onward; to reproduce the
// "resets daily" behavior we detect new sessions and restart the
// VWAP calculation from the first candle of each session.

const myAtrTimeframe = input.select('ATR Timeframe', '5', constants.time_frames);
const myAtrLength = input.number('ATR Length', 2750, { min: 1, max: 10000 });
const myAtrSmoothLength = input.number('ATR Smooth Length', 2750, { min: 1, max: 10000 });
const myMult1 = input.number('ATR Multiplier 1', 1.0, { min: 0, max: 20, step: 0.1 });
const myMult2 = input.number('ATR Multiplier 2', 1.85, { min: 0, max: 20, step: 0.1 });
const myMult3 = input.number('ATR Multiplier 3', 3.125, { min: 0, max: 20, step: 0.1 });

// Session-based VWAP: find the start of each session on the current chart
// and build a piecewise VWAP that restarts at every new session.
const mySessionIds = time.map(_t => bar_at(_t).session);
const myVwap = series_of(null);

let myCurrentSessionStart = 0;
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	if (myIndex === 0 || mySessionIds[myIndex] !== mySessionIds[myIndex - 1]) {
		myCurrentSessionStart = myIndex;
	}
	const mySessionVwap = vwap(hlc3, volume, myCurrentSessionStart);
	myVwap[myIndex] = mySessionVwap[myIndex];
}

// Fetch the higher timeframe data to compute ATR + EMA smoothing exactly
// as the Pine script does (both ATR and EMA calculated on that timeframe).
const myHtfData = await request.history(current.ticker, myAtrTimeframe);
assert(!myHtfData.error, "Error fetching ATR timeframe data: " + myHtfData.error);

const myHtfAtr = atr(myHtfData.high, myHtfData.low, myHtfData.close, myAtrLength);
const myHtfSmoothAtr = ema(myHtfAtr, myAtrSmoothLength);

// Land the HTF smoothed ATR onto the current chart's candles, using
// constant (non-repainting, backtestable) interpolation.
const mySmoothAtrLanded = land_points_onto_series(myHtfData.time, myHtfSmoothAtr, time, 'le');
const mySmoothAtr = interpolate_sparse_series(mySmoothAtrLanded, 'constant');

const myUpper1 = add(myVwap, mult(mySmoothAtr, myMult1));
const myLower1 = sub(myVwap, mult(mySmoothAtr, myMult1));

const myUpper2 = add(myVwap, mult(mySmoothAtr, myMult2));
const myLower2 = sub(myVwap, mult(mySmoothAtr, myMult2));

const myUpper3 = add(myVwap, mult(mySmoothAtr, myMult3));
const myLower3 = sub(myVwap, mult(mySmoothAtr, myMult3));

paint(myVwap, { name: 'VWAP', color: '#2962FF', thickness: 2 });

paint(myUpper1, { name: 'Upper1ATR', color: '#26A69A' });
paint(myLower1, { name: 'Lower1ATR', color: '#26A69A' });

paint(myUpper2, { name: 'Upper2ATR', color: '#FF9800' });
paint(myLower2, { name: 'Lower2ATR', color: '#FF9800' });

paint(myUpper3, { name: 'Upper3ATR', color: '#9C27B0' });
paint(myLower3, { name: 'Lower3ATR', color: '#9C27B0' });

// Scanning / Strategy signals: price crossing the various bands
const myCrossAboveUpper1 = for_every(close, myUpper1, shift(close, 1), shift(myUpper1, 1),
	(_c, _u, _pc, _pu) => _pc <= _pu && _c > _u);
const myCrossBelowLower1 = for_every(close, myLower1, shift(close, 1), shift(myLower1, 1),
	(_c, _l, _pc, _pl) => _pc >= _pl && _c < _l);

const myCrossAboveUpper2 = for_every(close, myUpper2, shift(close, 1), shift(myUpper2, 1),
	(_c, _u, _pc, _pu) => _pc <= _pu && _c > _u);
const myCrossBelowLower2 = for_every(close, myLower2, shift(close, 1), shift(myLower2, 1),
	(_c, _l, _pc, _pl) => _pc >= _pl && _c < _l);

const myCrossAboveUpper3 = for_every(close, myUpper3, shift(close, 1), shift(myUpper3, 1),
	(_c, _u, _pc, _pu) => _pc <= _pu && _c > _u);
const myCrossBelowLower3 = for_every(close, myLower3, shift(close, 1), shift(myLower3, 1),
	(_c, _l, _pc, _pl) => _pc >= _pl && _c < _l);

const myPriceAboveVwap = for_every(close, myVwap, (_c, _v) => _c > _v);
const myPriceBelowVwap = for_every(close, myVwap, (_c, _v) => _c < _v);

register_signal(myCrossAboveUpper1, 'Cross Above Upper 1 ATR');
register_signal(myCrossBelowLower1, 'Cross Below Lower 1 ATR');
register_signal(myCrossAboveUpper2, 'Cross Above Upper 2 ATR');
register_signal(myCrossBelowLower2, 'Cross Below Lower 2 ATR');
register_signal(myCrossAboveUpper3, 'Cross Above Upper 3 ATR');
register_signal(myCrossBelowLower3, 'Cross Below Lower 3 ATR');
register_signal(myPriceAboveVwap, 'Price Above VWAP');
register_signal(myPriceBelowVwap, 'Price Below VWAP');