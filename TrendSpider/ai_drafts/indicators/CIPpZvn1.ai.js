describe_indicator('RS vs VNINDEX', 'lower');

// NOTE: TrendSpider does not support TradingView's "INDEX:" prefix.
// We request VNINDEX history directly by its ticker symbol as the
// closest equivalent to request.security("INDEX:VNINDEX", ...).
const myIndexTicker = input.symbol('Reference Index', 'VNINDEX');
const myFastLength = input.number('Fast EMA Length', 9, { min: 1, max: 200 });
const mySlowLength = input.number('Slow EMA Length', 20, { min: 1, max: 200 });

// Helper to turn any thrown/returned error value into a readable
// string. Some error objects don't serialize well with
// JSON.stringify (e.g. Error instances, or objects with
// non-enumerable properties), which was producing the unreadable
// "[object Object]" message the customer saw. We now try several
// extraction strategies before falling back to a generic message.
function myExtractErrorText(_myErrorValue) {
	if (!_myErrorValue) {
		return null;
	}
	if (typeof _myErrorValue === 'string') {
		return _myErrorValue;
	}
	if (_myErrorValue.message && typeof _myErrorValue.message === 'string') {
		return _myErrorValue.message;
	}
	if (_myErrorValue.error) {
		return myExtractErrorText(_myErrorValue.error);
	}
	try {
		const myStringified = JSON.stringify(_myErrorValue);
		if (myStringified && myStringified !== '{}') {
			return myStringified;
		}
	}
	catch (_myStringifyError) {
		// ignore, fall through to generic text below
	}
	return 'Unknown error (possibly an invalid or unsupported ticker symbol)';
}

let myIndexData = null;
let myIndexErrorText = null;

try {
	myIndexData = await request.history(myIndexTicker, current.resolution);
}
catch (_myCaughtError) {
	myIndexErrorText = myExtractErrorText(_myCaughtError);
}

if (!myIndexErrorText && myIndexData && myIndexData.error) {
	myIndexErrorText = myExtractErrorText(myIndexData.error);
}

assert(!myIndexErrorText, "Error fetching index data for ticker " + myIndexTicker + ": " + myIndexErrorText);
assert(myIndexData.close && myIndexData.close.length > 0, "Index data returned no candles for ticker: " + myIndexTicker);

// Land the index close values onto the current chart's time series
const myIndexLanded = land_points_onto_series(myIndexData.time, myIndexData.close, time, 'le');
const myIndexClose = interpolate_sparse_series(myIndexLanded, 'constant');

// Relative Strength = Close / Index Close
const myRS = div(close, myIndexClose);
const mySigFast = ema(myRS, myFastLength);
const mySigSlow = ema(myRS, mySlowLength);

paint(myRS, { name: 'RS', color: '#2962FF', thickness: 2 });
paint(mySigFast, { name: 'EMA Fast', color: '#FF9800', thickness: 1 });
paint(mySigSlow, { name: 'EMA Slow', color: '#FFEB3B', thickness: 1 });

// Signals for scanners, alerts and strategies
const myBullishCross = for_every(mySigFast, mySigSlow, (_fast, _slow, _prev, _i) => {
	return _i > 0 && _fast > _slow && mySigFast[_i - 1] <= mySigSlow[_i - 1];
});

const myBearishCross = for_every(mySigFast, mySigSlow, (_fast, _slow, _prev, _i) => {
	return _i > 0 && _fast < _slow && mySigFast[_i - 1] >= mySigSlow[_i - 1];
});

const myRSAboveSlow = for_every(myRS, mySigSlow, (_rs, _slow) => _rs > _slow);

register_signal(myBullishCross, "RS Fast EMA Crosses Above Slow EMA");
register_signal(myBearishCross, "RS Fast EMA Crosses Below Slow EMA");
register_signal(myRSAboveSlow, "RS Above Slow EMA");