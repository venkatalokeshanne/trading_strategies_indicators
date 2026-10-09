describe_indicator('AmberWaves SPY vs SPX', 'price');

// Inputs mirroring the original Pine script. Note: TrendSpider
// auto generates color/thickness controls for painted lines, so
// those Pine inputs (trendLineColor, trendLineWidth, box colors)
// are not re-exposed here; we hardcode sensible defaults instead.
const myPrimarySymbol = input.symbol('Primary Symbol', 'SPX');
const myOppositeSymbol = input.symbol('Opposite Symbol', 'SPY');
const myShowTrendLine = input.boolean('Show trend line', true);
const myShowCandleLines = input.boolean('Show converted O/H/L/C lines', false);
const myBoxTab = input.tab('Value Box');
const myBoxPosition = myBoxTab.select('Value box position', 'Top Right', ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right', 'Off']);

// Pine's getTickerName(): takes the part after "EXCHANGE:"
function myTickerNameOf(_mySymbolId) {
	const myParts = _mySymbolId.split(':');
	return myParts.length > 1 ? myParts[1] : _mySymbolId;
}

const myPrimaryName = myTickerNameOf(myPrimarySymbol);
const myOppositeName = myTickerNameOf(myOppositeSymbol);
const myIsPrimaryChart = current.ticker === myPrimaryName;
const myIsOppositeChart = current.ticker === myOppositeName;

// Helper to turn whatever request.history() put into ".error"
// (or any thrown/rejected value) into a readable string. Errors
// coming back from the API are frequently plain objects without a
// useful toString(), and some of them contain circular references
// which make JSON.stringify() throw - this previously fell back to
// String(_myErr), which for a plain object just prints
// "[object Object]". This version checks common message-bearing
// fields first, and uses a circular-safe stringify as a last resort.
function mySafeStringify(_myValue) {
	const mySeen = [];
	try {
		return JSON.stringify(_myValue, (_myKey, _myVal) => {
			if (typeof _myVal === 'object' && _myVal !== null) {
				if (mySeen.indexOf(_myVal) !== -1) {
					return '[circular]';
				}
				mySeen.push(_myVal);
			}
			return _myVal;
		});
	}
	catch (myErr) {
		return null;
	}
}

function myErrorTextOf(_myErr) {
	if (!_myErr) return '';
	if (typeof _myErr === 'string') return _myErr;
	if (_myErr instanceof Error) return _myErr.message || String(_myErr);

	if (typeof _myErr === 'object') {
		if (typeof _myErr.message === 'string' && _myErr.message) return _myErr.message;
		if (typeof _myErr.error === 'string' && _myErr.error) return _myErr.error;
		if (typeof _myErr.reason === 'string' && _myErr.reason) return _myErr.reason;
		if (typeof _myErr.error === 'object' && _myErr.error) return myErrorTextOf(_myErr.error);

		const myStringified = mySafeStringify(_myErr);
		if (myStringified) return myStringified;
	}

	try {
		return String(_myErr);
	}
	catch (myErr) {
		return 'Unknown error';
	}
}

// Fetch both symbols on the current resolution. request.history()
// can both reject (throw) or resolve with an { error } object
// depending on the failure mode, so we guard against both here
// instead of assuming a clean resolved value.
let myPrimaryData = null;
let myOppositeData = null;
let myFetchErrorText = null;

try {
	const myResults = await Promise.all([
		request.history(myPrimarySymbol, current.resolution),
		request.history(myOppositeSymbol, current.resolution)
	]);
	myPrimaryData = myResults[0];
	myOppositeData = myResults[1];
}
catch (myErr) {
	myFetchErrorText = myErrorTextOf(myErr);
}

assert(!myFetchErrorText, 'Error fetching history: ' + myFetchErrorText);
assert(!!myPrimaryData && !myPrimaryData.error, 'Error fetching primary symbol: ' + myErrorTextOf(myPrimaryData && myPrimaryData.error));
assert(!!myOppositeData && !myOppositeData.error, 'Error fetching opposite symbol: ' + myErrorTextOf(myOppositeData && myOppositeData.error));

// Land both data sets onto the current chart's time axis (constant
// interpolation keeps this backtestable / non-repainting, matching
// request.security's gaps_off behavior as closely as possible).
function myLand(_myData, _mySeries) {
	const myLanded = land_points_onto_series(_myData.time, _mySeries, time, 'le');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myPOpen = myLand(myPrimaryData, myPrimaryData.open);
const myPHigh = myLand(myPrimaryData, myPrimaryData.high);
const myPLow = myLand(myPrimaryData, myPrimaryData.low);
const myPClose = myLand(myPrimaryData, myPrimaryData.close);

const myOOpen = myLand(myOppositeData, myOppositeData.open);
const myOHigh = myLand(myOppositeData, myOppositeData.high);
const myOLow = myLand(myOppositeData, myOppositeData.low);
const myOClose = myLand(myOppositeData, myOppositeData.close);

// Build the converted OHLC + the "other symbol raw value" per Pine logic
let myConvOpen = constants.empty_series;
let myConvHigh = constants.empty_series;
let myConvLow = constants.empty_series;
let myConvClose = constants.empty_series;
let myRawOtherValue = constants.empty_series;
const myRawOtherLabel = myIsPrimaryChart ? myOppositeName : (myIsOppositeChart ? myPrimaryName : null);

if (myIsPrimaryChart) {
	const myRatio = div(myPClose, myOClose);
	myConvOpen = mult(myOOpen, myRatio);
	myConvHigh = mult(myOHigh, myRatio);
	myConvLow = mult(myOLow, myRatio);
	myConvClose = mult(myOClose, myRatio);
	myRawOtherValue = myOClose;
}
else if (myIsOppositeChart) {
	const myRatio = div(myOClose, myPClose);
	myConvOpen = mult(myPOpen, myRatio);
	myConvHigh = mult(myPHigh, myRatio);
	myConvLow = mult(myPLow, myRatio);
	myConvClose = mult(myPClose, myRatio);
	myRawOtherValue = myPClose;
}

// Trend line (converted close), toggleable per Pine's showTrendLine
paint(myShowTrendLine ? myConvClose : series_of(null), { name: 'ConvertedLine', color: 'orange', thickness: 2 });

// Approximation of plotcandle(): TrendSpider's Custom JS API has no
// function to paint an independent candlestick series, so the
// converted O/H/L/C are approximated as four plain lines instead.
paint(myShowCandleLines ? myConvOpen : series_of(null), { name: 'ConvertedOpen', color: 'gray', style: 'dotted' });
paint(myShowCandleLines ? myConvHigh : series_of(null), { name: 'ConvertedHigh', color: 'green', style: 'dotted' });
paint(myShowCandleLines ? myConvLow : series_of(null), { name: 'ConvertedLow', color: 'red', style: 'dotted' });
paint(myShowCandleLines ? myConvClose : series_of(null), { name: 'ConvertedClose', color: 'blue', style: 'dotted' });

// Value box, approximated via paint_overlay (TrendSpider has no
// table.cell equivalent; this renders similarly as a small panel).
const myLastValidIndex = myRawOtherValue.length - 1;
const myLastRawValue = myRawOtherValue[myLastValidIndex];
const myBoxText = (myIsPrimaryChart || myIsOppositeChart)
	? (myRawOtherLabel + ': ' + (myLastRawValue == null ? 'n/a' : myLastRawValue.toFixed(current.decimals)))
	: ('Chart must be ' + myPrimaryName + ' or ' + myOppositeName);

const myOverlayPositionMap = {
	'Top Left': 'top_left',
	'Top Right': 'top_right',
	'Bottom Left': 'bottom_left',
	'Bottom Right': 'bottom_right',
	'Off': 'top_right'
};

paint_overlay('ValueBox', { position: myOverlayPositionMap[myBoxPosition] }, {
	rows: myBoxPosition === 'Off' ? [] : [{
		cells: [{ text: myBoxText, color: 'white', background_color: 'rgba(0,0,0,0.7)' }]
	}]
});

// Signals for scanning / alerts / strategy testing
register_signal(myIsPrimaryChart || myIsOppositeChart, 'Chart Is Primary Or Opposite Symbol');
register_signal(myIsPrimaryChart, 'Chart Is Primary Symbol');
register_signal(myIsOppositeChart, 'Chart Is Opposite Symbol');
register_signal(for_every(myConvClose, myConvOpen, (_c, _o) => _c != null && _o != null && _c >= _o), 'Converted Candle Bullish');
register_signal(for_every(myConvClose, myConvOpen, (_c, _o) => _c != null && _o != null && _c < _o), 'Converted Candle Bearish');