describe_indicator('Thai Gold Price (96.5 Percent) Converter', 'lower', { decimals: 0 });

// NOTE: TrendSpider Custom JS has no plotcandle() equivalent that can
// draw a brand new candlestick series with independent OHLC values.
// color_candles() only recolors the EXISTING chart candles (same OHLC),
// it cannot repaint candles with different open/high/low/close values.
// So this version paints the converted Thai Gold Open/High/Low/Close as
// lines (High/Low as a filled band, Open/Close as lines) plus the SMA,
// which reproduces the same values and signal logic as the Pine script.

const myPurityPercent = input.number('Gold Purity Percent', 96.5, { min: 0, max: 100 });
const myFxTicker = input.text('USDTHB Ticker', 'USDTHB');
const myShowMA = input.boolean('Show Moving Average', true);
const myMaLength = input.number('MA Length', 9, { min: 1, max: 500 });

const myGramsPerOz = 31.1034768;
const myGramsPerBaht = 15.244;
const myConversionFactor = (myGramsPerBaht / myGramsPerOz) * (myPurityPercent / 100);

// Helper to turn any thrown/rejected value into a readable string.
// Some failure modes from request.history() reject with a plain object
// that has no "message" property and stringifies poorly (hence the
// "[object Object]" the customer saw), so we try several fallbacks.
function myDescribeError(_err) {
	if (!_err) return 'Unknown error';
	if (typeof _err === 'string') return _err;
	if (_err.message) return _err.message;
	if (_err.error) return typeof _err.error === 'string' ? _err.error : JSON.stringify(_err.error);
	try {
		const myKeys = Object.keys(_err);
		if (myKeys.length > 0) {
			return myKeys.map(_k => _k + ': ' + _err[_k]).join(', ');
		}
	}
	catch (myIgnored) {}
	return String(_err);
}

// fetch USDTHB on the current resolution. "FX_IDC:USDTHB" is not a
// recognized symbol on this platform, which is the root cause of the
// original error; the plain ticker "USDTHB" is used instead. request.history()
// can either return an object with `.error` set, or throw synchronously,
// so both failure modes are handled here.
let myFxData;
try {
	myFxData = await request.history(myFxTicker, current.resolution);
}
catch (myFetchError) {
	throw 'Error fetching FX data for ' + myFxTicker + ': ' + myDescribeError(myFetchError);
}

assert(!myFxData.error, 'Error fetching FX data for ' + myFxTicker + ': ' + myDescribeError(myFxData.error));
assert(myFxData.time && myFxData.time.length > 0, 'No FX history data returned for ticker ' + myFxTicker + ' at resolution ' + current.resolution);

// land FX closes onto the current chart's time axis and fill gaps
const myFxLanded = land_points_onto_series(myFxData.time, myFxData.close, time, 'le');
const myUsdThb = interpolate_sparse_series(myFxLanded, 'constant');

// convert OHLC into Thai Gold THB terms
const myThaiOpen = mult(open, myUsdThb, myConversionFactor);
const myThaiHigh = mult(high, myUsdThb, myConversionFactor);
const myThaiLow = mult(low, myUsdThb, myConversionFactor);
const myThaiClose = mult(close, myUsdThb, myConversionFactor);

// bullish/bearish color logic (close >= open)
const myIsBullish = for_every(myThaiClose, myThaiOpen, (_c, _o) => _c >= _o);
const myCandleColors = for_every(myIsBullish, _b => _b ? '#089981' : '#f23645');

// color the actual chart candles using the Thai Gold direction
color_candles(myCandleColors);

// paint High/Low band and Open/Close lines
const myHighLine = paint(myThaiHigh, { name: 'Thai Gold High', color: '#089981', style: 'line', thickness: 1 });
const myLowLine = paint(myThaiLow, { name: 'Thai Gold Low', color: '#f23645', style: 'line', thickness: 1 });
fill(myHighLine, myLowLine, '#f2a900', 0.1);

const myCloseLine = paint(myThaiClose, { name: 'Thai Gold Close', color: '#f2a900', style: 'line', thickness: 2 });
paint(myThaiOpen, { name: 'Thai Gold Open', color: '#9e9e9e', style: 'dotted', thickness: 1 });

// moving average
const myMaValue = sma(myThaiClose, myMaLength);
paint(myShowMA ? myMaValue : constants.empty_series, { name: 'SMA', color: 'blue', style: 'line', thickness: 1 });

// label with last close value (rounded), colored by direction
const myLastIndex = myThaiClose.length - 1;
const myLastColor = myIsBullish[myLastIndex] ? 'green' : 'red';
paint_label_at_line(myCloseLine, myLastIndex, Math.round(myThaiClose[myLastIndex]) + ' THB', { color: myLastColor });

// signals for scanner / alerts / strategy tester
register_signal(myIsBullish, 'Thai Gold Bullish Candle');
register_signal(for_every(myIsBullish, _b => !_b), 'Thai Gold Bearish Candle');