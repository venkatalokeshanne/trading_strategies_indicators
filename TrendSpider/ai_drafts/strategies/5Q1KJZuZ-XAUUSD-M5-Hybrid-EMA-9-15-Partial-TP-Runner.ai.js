describe_indicator('XAUUSD M5 Hybrid EMA 9/15', 'price');

// NOTE: TrendSpider Custom JS indicators cannot place broker
// orders or manage strategy exits (stop loss, take profit,
// trailing stops). This script reproduces the Pine Script's
// indicator logic (EMAs, HTF trend filter, rejection candle
// detection and buy/sell conditions) and exposes buy/sell
// signals for scanners, alerts and the Strategy Tester via
// register_signal(). The actual position management (partial
// TP, runner TP, trailing stop, SL) from the original Pine
// strategy() block is not expressible here.

const myEmaFastLen = input.number('EMA Fast Length', 9, { min: 1, max: 200 });
const myEmaSlowLen = input.number('EMA Slow Length', 15, { min: 1, max: 200 });
const mySlBuffer = input.number('SL Buffer', 0.3, { min: 0, max: 100 });

// Current (M5) EMAs
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// Higher timeframe (M15) EMAs, fetched and landed onto the current chart.
// Using 'ge' landing to approximate Pine's request.security() behavior
// (uses the most recently closed HTF bar at or after each candle's time).
const myHtfData = await request.history(current.ticker, '15');
assert(!myHtfData.error, 'Error fetching 15min data: ' + myHtfData.error);

const myEmaFastHtfRaw = ema(myHtfData.close, myEmaFastLen);
const myEmaSlowHtfRaw = ema(myHtfData.close, myEmaSlowLen);

const myEmaFastHtfLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myEmaFastHtfRaw, time, 'ge'),
	'constant'
);
const myEmaSlowHtfLanded = interpolate_sparse_series(
	land_points_onto_series(myHtfData.time, myEmaSlowHtfRaw, time, 'ge'),
	'constant'
);

// Trend conditions
const myBullTrend = for_every(
	myEmaFast, myEmaSlow, myEmaFastHtfLanded, myEmaSlowHtfLanded,
	(_f, _s, _fh, _sh) => _f > _s && _fh > _sh
);
const myBearTrend = for_every(
	myEmaFast, myEmaSlow, myEmaFastHtfLanded, myEmaSlowHtfLanded,
	(_f, _s, _fh, _sh) => _f < _s && _fh < _sh
);

// Rejection candle detection
const myBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myUpperWick = for_every(high, close, open, (_h, _c, _o) => _h - Math.max(_c, _o));
const myLowerWick = for_every(close, open, low, (_c, _o, _l) => Math.min(_c, _o) - _l);

const myBullishRejection = for_every(
	myLowerWick, myBody, close, open,
	(_lw, _b, _c, _o) => _lw > _b * 1.5 && _c > _o
);
const myBearishRejection = for_every(
	myUpperWick, myBody, close, open,
	(_uw, _b, _c, _o) => _uw > _b * 1.5 && _c < _o
);

// Entry conditions
const myBuyCondition = for_every(myBullTrend, myBullishRejection, (_t, _r) => _t && _r);
const mySellCondition = for_every(myBearTrend, myBearishRejection, (_t, _r) => _t && _r);

// Theoretical stop loss levels (informational only, not an actual order)
const myLongSL = sub(myEmaSlow, mySlBuffer);
const myShortSL = add(myEmaFast, mySlBuffer);

// Plot EMAs
paint(myEmaFast, { name: 'EMA Fast', color: '#2ca599', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#ee5451', thickness: 2 });

// Plot informational SL lines (hidden-ish defaults, user can toggle)
paint(myLongSL, { name: 'Long Stop Level', color: '#2ca599', style: 'dotted', thickness: 1 });
paint(myShortSL, { name: 'Short Stop Level', color: '#ee5451', style: 'dotted', thickness: 1 });

// Buy/Sell markers (equivalent of plotshape triangles)
const myBuyMarks = for_every(myBuyCondition, low, (_cond, _l) => _cond ? _l : null);
const mySellMarks = for_every(mySellCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#2ca599' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#ee5451' });

// Signals for scanners, alerts and strategy tester
register_signal(myBuyCondition, 'Buy Condition');
register_signal(mySellCondition, 'Sell Condition');