describe_indicator('SRT Panel', 'price');

// This indicator reproduces the "SRT Panel" Pine Script concept:
// SRT (Stock Relative to Trend) = Close / SMA(124).
// It also exposes signals so SRT levels can be used in
// Scanners, Alerts and Strategy Tester.
const mySmaLength = 124;
const myVixTicker = input.text('India VIX Ticker', 'INDIAVIX');

const mySma = sma(close, mySmaLength);
const mySrt = div(close, mySma);

// Pine's request.security('INDIAVIX', 'D', close) is reproduced here
// via request.history(). This requires the ticker to exist on the
// platform under the exact symbol provided. We wrap this call in a
// try/catch because request.history() can reject with a non-string
// error (an object), which previously caused "history: [object Object]"
// to be thrown when passed straight into assert()/throw. Now, if the
// VIX ticker is invalid or the request otherwise fails, we simply
// fall back to a series of nulls instead of crashing the indicator.
let myVixInterpolated = series_of(null);

try {
	const myVixData = await request.history(myVixTicker, 'D');

	if (myVixData && !myVixData.error) {
		const myVixLanded = land_points_onto_series(myVixData.time, myVixData.close, time, 'le');
		myVixInterpolated = interpolate_sparse_series(myVixLanded, 'constant');
	}
}
catch (myError) {
	// Swallow the error gracefully; VIX panel row will show "N/A".
	myVixInterpolated = series_of(null);
}

const myCurrentClose = close[close.length - 1];
const myCurrentSma = mySma[mySma.length - 1];
const myCurrentSrt = mySrt[mySrt.length - 1];
const myCurrentVix = myVixInterpolated[myVixInterpolated.length - 1];

const myFormat = _value => (_value === null || _value === undefined || isNaN(_value)) ? 'N/A' : _value.toFixed(2);

paint_overlay('SRTPanel', { position: 'top_right' }, {
	rows: [
		{
			cells: [
				{ text: 'Current Level', color: 'white', background_color: '#00d47c' },
				{ text: myFormat(myCurrentClose), color: 'black', background_color: 'white' }
			]
		},
		{
			cells: [
				{ text: 'SMA 124', color: 'white', background_color: '#00d47c' },
				{ text: myFormat(myCurrentSma), color: 'black', background_color: 'white' }
			]
		},
		{
			cells: [
				{ text: 'SRT Value', color: 'white', background_color: '#00d47c' },
				{ text: myFormat(myCurrentSrt), color: 'black', background_color: 'white' }
			]
		},
		{
			cells: [
				{ text: 'India VIX', color: 'white', background_color: '#00d47c' },
				{ text: myFormat(myCurrentVix), color: 'black', background_color: 'white' }
			]
		}
	]
});

// Signals for scanning / alerts / strategy testing
const mySrtAboveOne = for_every(mySrt, _s => _s > 1);
const mySrtBelowOne = for_every(mySrt, _s => _s < 1);
const mySrtCrossAboveOne = for_every(mySrt, (_s, _prev, _i) => _i > 0 && _s > 1 && mySrt[_i - 1] <= 1);
const mySrtCrossBelowOne = for_every(mySrt, (_s, _prev, _i) => _i > 0 && _s < 1 && mySrt[_i - 1] >= 1);

register_signal(mySrtAboveOne, 'SRT Above One');
register_signal(mySrtBelowOne, 'SRT Below One');
register_signal(mySrtCrossAboveOne, 'SRT Crossed Above One');
register_signal(mySrtCrossBelowOne, 'SRT Crossed Below One');