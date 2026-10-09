describe_indicator('VWAP Slope Trend Filter', 'price');

const myVwapSourceOption = input.select('VWAP Source', 'hlc3', constants.price_source_options);
const mySlopeLength = input.number('Slope Length', 5, { min: 1, max: 500 });
const myMinSlope = input.number('Minimum Slope', 0.03, { min: -10, max: 10, step: 0.01 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
const myShowBackground = input.boolean('Show Trend Background', true);
const myShowSignals = input.boolean('Show Trend Change Signals', true);

const mySrc = market[myVwapSourceOption];

// Pine's ta.vwap resets at the start of every session (daily by default).
// TrendSpider's vwap() needs an explicit "from candle index", so we rebuild
// a session-anchored VWAP by stitching together per-session vwap() calls.
const mySessionIdAtIndex = time.map(_t => bar_at(_t).session);

const myVwapValue = series_of(null);
let mySessionStartIndex = 0;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myIsNewSession = myIndex === 0 || mySessionIdAtIndex[myIndex] !== mySessionIdAtIndex[myIndex - 1];
	if (myIsNewSession) {
		mySessionStartIndex = myIndex;
	}
}

// Build vwap per contiguous session block
let myBlockStart = 0;
for (let myIndex = 1; myIndex <= time.length; myIndex += 1) {
	const myIsBoundary = myIndex === time.length || mySessionIdAtIndex[myIndex] !== mySessionIdAtIndex[myBlockStart];
	if (myIsBoundary) {
		const myBlockVwap = vwap(mySrc, volume, myBlockStart, myIndex - 1);
		for (let myFillIndex = myBlockStart; myFillIndex < myIndex; myFillIndex += 1) {
			myVwapValue[myFillIndex] = myBlockVwap[myFillIndex];
		}
		myBlockStart = myIndex;
	}
}

const myAtrValue = atr(high, low, close, myAtrLength);

// Raw slope: change in VWAP over slopeLength candles, normalized by ATR
const myRawSlope = sub(myVwapValue, shift(myVwapValue, mySlopeLength));
const myNormalizedSlope = for_every(myRawSlope, myAtrValue, (_rawSlope, _atrValue) => {
	return _atrValue !== 0 && _atrValue !== null ? _rawSlope / _atrValue : 0;
});

const myBullTrend = for_every(myNormalizedSlope, _slope => _slope > myMinSlope);
const myBearTrend = for_every(myNormalizedSlope, _slope => _slope < -myMinSlope);

const myVwapColor = for_every(myBullTrend, myBearTrend, (_bull, _bear) => _bull ? 'lime' : (_bear ? 'red' : 'gray'));

paint(myVwapValue, { name: 'VWAP', color: myVwapColor, thickness: 3 });

// Background approximation using candle coloring, since bgcolor() is not
// available in Custom JS API. This colors candles instead of the background.
const myBackgroundColor = for_every(myBullTrend, myBearTrend, (_bull, _bear) => {
	if (!myShowBackground) {
		return null;
	}
	return _bull ? 'rgba(0,255,0,0.08)' : (_bear ? 'rgba(255,0,0,0.08)' : 'rgba(128,128,128,0.06)');
});
color_candles(myBackgroundColor);

// Trend change detection
const myBullStart = for_every(myBullTrend, (_bull, _prev, _index) => _bull && !(_index > 0 && myBullTrend[_index - 1]));
const myBearStart = for_every(myBearTrend, (_bear, _prev, _index) => _bear && !(_index > 0 && myBearTrend[_index - 1]));

const myBullSignal = for_every(myBullStart, _start => (myShowSignals && _start) ? constants.icons.triangle_up : null);
const myBearSignal = for_every(myBearStart, _start => (myShowSignals && _start) ? constants.icons.triangle_down : null);

paint(myBullSignal, { name: 'Bull Trend Start', style: 'labels_below', color: 'lime' });
paint(myBearSignal, { name: 'Bear Trend Start', style: 'labels_above', color: 'red' });

// Signals for scanner, alerts, strategy tester
register_signal(for_every(myBullStart, _start => !!_start), 'VWAP Bull Trend Start');
register_signal(for_every(myBearStart, _start => !!_start), 'VWAP Bear Trend Start');
register_signal(myBullTrend, 'VWAP Bull Trend Active');
register_signal(myBearTrend, 'VWAP Bear Trend Active');