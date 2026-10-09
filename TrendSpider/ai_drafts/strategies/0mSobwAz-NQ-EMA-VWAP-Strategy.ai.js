describe_indicator('NQ EMA VWAP Strategy', 'price');

// Converted from a TradingView Pine Script strategy.
// NOTE: Pine's ta.vwap() resets automatically at the start of
// each new trading session (day). The Custom JS API's vwap()
// function does not auto-reset per session, so we manually
// rebuild a session-anchored VWAP below to match Pine's behavior.

const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);

// Build session-anchored VWAP (resets at the start of each day),
// matching Pine Script's default ta.vwap() behavior.
const mySessionAtIndex = time.map(_t => bar_at(_t).session);
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

	myVwap[myIndex] = myCumVol !== 0 ? myCumPV / myCumVol : null;
}

// Long condition: EMA20 crosses above EMA50 while price is above VWAP
// Short condition: EMA20 crosses below EMA50 while price is below VWAP
const myLongCondition = for_every(myEma20, myEma50, close, myVwap, (_e20, _e50, _c, _v, _prev, _i) => {
	if (_i === 0) {
		return false;
	}
	return _e20 > _e50 && myEma20[_i - 1] <= myEma50[_i - 1] && _c > _v;
});

const myShortCondition = for_every(myEma20, myEma50, close, myVwap, (_e20, _e50, _c, _v, _prev, _i) => {
	if (_i === 0) {
		return false;
	}
	return _e20 < _e50 && myEma20[_i - 1] >= myEma50[_i - 1] && _c < _v;
});

register_signal(myLongCondition, "Long Entry");
register_signal(myShortCondition, "Short Entry");

paint(myEma20, { name: 'EMA20', color: '#26A69A', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#EF5350', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#4DA3FF', thickness: 2, style: 'line' });

const myLongMarks = for_every(myLongCondition, _l => _l ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortCondition, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: '#26A69A' });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: '#EF5350' });