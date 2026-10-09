describe_indicator('EMA Cross + 1H Bias + VWAP SLTP', 'price');

// NOTE: This is a translation of a Pine Script strategy into a plotting +
// signal indicator. TrendSpider Custom JS does not support strategy
// entries/exits (strategy.entry / strategy.exit) inside an indicator script,
// so SL/TP levels are computed and exposed as reference lines/signals only.
// ta.vwap() in Pine resets every new trading session automatically; we
// reproduce that by manually accumulating price*volume since the start of
// each session (detected via bar_at().session), using "close" as price
// source (matching `ta.vwap(close)` in the original script).

const myFastLen = input.number('Fast EMA', 10, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA', 20, { min: 1, max: 500 });
const myHtfLen = input.number('HTF EMA (1H)', 20, { min: 1, max: 500 });

// === EMAs on current time frame ===
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);

// === 1H EMA (HTF bias) ===
const myHtfData = await request.history(current.ticker, '60');
assert(!myHtfData.error, `Error fetching 1H data: "${myHtfData.error}"`);

const myHtfEMARaw = ema(myHtfData.close, myHtfLen);

// Land the 1H close and 1H EMA onto the current chart's time axis.
// Using "le" (last known value <= current candle time) avoids look-ahead.
const myHtfCloseLanded = land_points_onto_series(myHtfData.time, myHtfData.close, time, 'le');
const myHtfEMALanded = land_points_onto_series(myHtfData.time, myHtfEMARaw, time, 'le');

// 'constant' interpolation keeps this backtestable (no forward-looking data)
const myHtfClose = interpolate_sparse_series(myHtfCloseLanded, 'constant');
const myHtfEMA = interpolate_sparse_series(myHtfEMALanded, 'constant');

// === Session anchored VWAP, using Close as price source (ta.vwap(close)) ===
const mySessionAtIndex = time.map(myTime => bar_at(myTime).session);
const myVwap = series_of(null);

let myCumPV = 0;
let myCumVol = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewSession = myIndex === 0 || mySessionAtIndex[myIndex] !== mySessionAtIndex[myIndex - 1];

	if (myNewSession) {
		myCumPV = 0;
		myCumVol = 0;
	}

	myCumPV += close[myIndex] * volume[myIndex];
	myCumVol += volume[myIndex];

	myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : close[myIndex];
}

// === Conditions ===
const myBullHTF = for_every(myHtfClose, myHtfEMA, (_c, _e) => _c > _e);
const myBearHTF = for_every(myHtfClose, myHtfEMA, (_c, _e) => _c < _e);

// crossover / crossunder of fastEMA vs slowEMA
const myCrossOver = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast > _slow && myFastEMA[_index - 1] <= mySlowEMA[_index - 1];
});

const myCrossUnder = for_every(myFastEMA, mySlowEMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast < _slow && myFastEMA[_index - 1] >= mySlowEMA[_index - 1];
});

const myLongFinal = for_every(myCrossOver, myBullHTF, close, myVwap, (_co, _bull, _c, _vwap) => _co && _bull && _c > _vwap);
const myShortFinal = for_every(myCrossUnder, myBearHTF, close, myVwap, (_cu, _bear, _c, _vwap) => _cu && _bear && _c < _vwap);

// === SL / TP reference levels (for information only, no actual orders) ===
const myLongSL = myVwap;
const myShortSL = myVwap;
const myLongTP = for_every(close, myLongSL, (_c, _sl) => _c + (_c - _sl));
const myShortTP = for_every(close, myShortSL, (_c, _sl) => _c - (_sl - _c));

const myLongTPLine = for_every(myLongFinal, myLongTP, (_f, _tp) => _f ? _tp : null);
const myLongSLLine = for_every(myLongFinal, myLongSL, (_f, _sl) => _f ? _sl : null);
const myShortTPLine = for_every(myShortFinal, myShortTP, (_f, _tp) => _f ? _tp : null);
const myShortSLLine = for_every(myShortFinal, myShortSL, (_f, _sl) => _f ? _sl : null);

// === Plots ===
paint(myFastEMA, { name: 'Fast EMA', color: '#FF9800', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: '#2196F3', thickness: 2 });
paint(myHtfEMA, { name: 'HTF EMA', color: '#9C27B0', thickness: 2 });
paint(myVwap, { name: 'Vwap', color: '#E91E63', thickness: 2 });

paint(myLongTPLine, { name: 'Long Target', style: 'dotted', color: '#26A69A' });
paint(myLongSLLine, { name: 'Long Stop', style: 'dotted', color: '#EF5350' });
paint(myShortTPLine, { name: 'Short Target', style: 'dotted', color: '#26A69A' });
paint(myShortSLLine, { name: 'Short Stop', style: 'dotted', color: '#EF5350' });

// === Signals for Scanners / Alerts / Strategy Tester ===
register_signal(myLongFinal, 'Long Entry');
register_signal(myShortFinal, 'Short Entry');
register_signal(myBullHTF, 'HTF Bullish Bias');
register_signal(myBearHTF, 'HTF Bearish Bias');