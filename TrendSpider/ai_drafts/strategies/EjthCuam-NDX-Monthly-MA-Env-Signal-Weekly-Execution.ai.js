describe_indicator('NDX Monthly MA Envelope Signal (Weekly Execution)', 'price');

// This indicator reproduces a TradingView strategy that trades NDX using
// Weekly closes crossing above/below a Monthly SMA(10) envelope, filtered
// by a Weekly 200 EMA. Since the original is a strategy (stateful position
// tracking), the "position_size > 0" state is simulated here with a simple
// sequential loop over the weekly series.

const myShowDebug = input.boolean('Show Debug', false);

// Fetch Weekly and Monthly data for the chosen symbol, exactly as
// request.security() does in Pine. Defaulting to the current chart ticker
// instead of a hardcoded "NDX" string, since an invalid/unsupported ticker
// string is what was causing request.history() to return an error object
// (which previously surfaced as the opaque "[object Object]" error).
const myTicker = input.symbol('Symbol', current.ticker);

const [myWeeklyData, myMonthlyData] = await Promise.all([
	request.history(myTicker, 'W'),
	request.history(myTicker, 'M')
]);

// Error objects returned by request.history() can themselves be objects
// (not plain strings), which is why stringifying them explicitly here
// prevents the generic, unhelpful "[object Object]" message.
assert(!myWeeklyData.error, 'Error fetching Weekly data: ' + JSON.stringify(myWeeklyData.error || 'unknown error'));
assert(!myMonthlyData.error, 'Error fetching Monthly data: ' + JSON.stringify(myMonthlyData.error || 'unknown error'));

// Also guard against "no data returned" cases (empty arrays), which some
// data providers surface as a successful-but-empty response rather than
// an explicit error field.
assert(myWeeklyData.close && myWeeklyData.close.length > 0, 'No Weekly data returned for symbol: ' + myTicker);
assert(myMonthlyData.close && myMonthlyData.close.length > 0, 'No Monthly data returned for symbol: ' + myTicker);

// Monthly SMA(10) and envelope bands, computed on Monthly resolution
const myMonthlyMedianRaw = sma(myMonthlyData.close, 10);
const myMonthlyTopRaw = mult(myMonthlyMedianRaw, 1.05);
const myMonthlyBottomRaw = mult(myMonthlyMedianRaw, 0.95);
const myMonthlyLowRaw = myMonthlyData.low;

// Weekly 200 EMA, computed on Weekly resolution
const myWeekly200EMARaw = ema(myWeeklyData.close, 200);
const myWeeklyCloseRaw = myWeeklyData.close;

// Land Monthly series onto Weekly timestamps, using "le" (the most recent
// completed Monthly bar at or before a given Weekly bar time), then fill
// gaps using "constant" interpolation (no forward-looking / repainting).
const myMonthlyMedianOnWeekly = interpolate_sparse_series(
	land_points_onto_series(myMonthlyData.time, myMonthlyMedianRaw, myWeeklyData.time, 'le'),
	'constant'
);
const myMonthlyTopOnWeekly = interpolate_sparse_series(
	land_points_onto_series(myMonthlyData.time, myMonthlyTopRaw, myWeeklyData.time, 'le'),
	'constant'
);
const myMonthlyBottomOnWeekly = interpolate_sparse_series(
	land_points_onto_series(myMonthlyData.time, myMonthlyBottomRaw, myWeeklyData.time, 'le'),
	'constant'
);
const myMonthlyLowOnWeekly = interpolate_sparse_series(
	land_points_onto_series(myMonthlyData.time, myMonthlyLowRaw, myWeeklyData.time, 'le'),
	'constant'
);

// Compute crossover / crossunder on the Weekly series, plus the stateful
// "position_size > 0" simulation, in a single sequential pass.
const myBuySignalWeekly = [];
const mySellSignalWeekly = [];
let myPositionOpen = false;

for (let myIndex = 0; myIndex < myWeeklyCloseRaw.length; myIndex += 1) {
	const myClose = myWeeklyCloseRaw[myIndex];
	const myPrevClose = myIndex > 0 ? myWeeklyCloseRaw[myIndex - 1] : null;
	const myMedian = myMonthlyMedianOnWeekly[myIndex];
	const myPrevMedian = myIndex > 0 ? myMonthlyMedianOnWeekly[myIndex - 1] : null;
	const myEma200 = myWeekly200EMARaw[myIndex];
	const myLow = myMonthlyLowOnWeekly[myIndex];
	const myPrevLow = myIndex > 0 ? myMonthlyLowOnWeekly[myIndex - 1] : null;
	const myBottom = myMonthlyBottomOnWeekly[myIndex];
	const myPrevBottom = myIndex > 0 ? myMonthlyBottomOnWeekly[myIndex - 1] : null;

	const myCrossover = myPrevClose != null && myPrevMedian != null &&
		myClose > myMedian && myPrevClose <= myPrevMedian;

	const myCrossunder = myPrevLow != null && myPrevBottom != null &&
		myLow != null && myBottom != null &&
		myLow < myBottom && myPrevLow >= myPrevBottom;

	const myBuySignal = myCrossover && myEma200 != null && myClose > myEma200;
	const mySellSignal = myPositionOpen && myCrossunder;

	if (myBuySignal) {
		myPositionOpen = true;
	}
	if (mySellSignal) {
		myPositionOpen = false;
	}

	myBuySignalWeekly.push(myBuySignal);
	mySellSignalWeekly.push(mySellSignal);
}

// Land everything (visuals + signals) onto the current chart's time axis.
// "le" picks the most recently completed Weekly bar for each chart candle.
const myWeeklyCloseOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myWeeklyCloseRaw, time, 'le'),
	'constant'
);
const myMonthlyMedianOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myMonthlyMedianOnWeekly, time, 'le'),
	'constant'
);
const myMonthlyTopOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myMonthlyTopOnWeekly, time, 'le'),
	'constant'
);
const myMonthlyBottomOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myMonthlyBottomOnWeekly, time, 'le'),
	'constant'
);
const myWeekly200EMAOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myWeekly200EMARaw, time, 'le'),
	'constant'
);
const myBuySignalOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myBuySignalWeekly.map(myVal => myVal ? 1 : 0), time, 'le'),
	'constant'
);
const mySellSignalOnChart = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, mySellSignalWeekly.map(myVal => myVal ? 1 : 0), time, 'le'),
	'constant'
);

// Visuals, mirroring the Pine plot() calls
paint(myWeeklyCloseOnChart, { name: 'WeeklyClose', color: '#2962FF', thickness: 1 });
paint(myMonthlyMedianOnChart, { name: 'MonthlySMA10', color: '#FF9800', thickness: 2 });

const myTopLinePainted = paint(myMonthlyTopOnChart, { name: 'EnvTop', color: '#26A69A', thickness: 1 });
const myBottomLinePainted = paint(myMonthlyBottomOnChart, { name: 'EnvBottom', color: '#EF5350', thickness: 1 });
fill(myTopLinePainted, myBottomLinePainted, 'gray', 0.08);

paint(myWeekly200EMAOnChart, { name: 'Weekly200EMA', color: '#2962FF', thickness: 1 });

// Buy / Sell markers (equivalent of the Pine debug label, shown as markers)
const myBuyMarker = for_every(myBuySignalOnChart, low, (myBuy, myLow) => myBuy > 0 ? myLow : null);
const mySellMarker = for_every(mySellSignalOnChart, high, (mySell, myHigh) => mySell > 0 ? myHigh : null);

paint(myShowDebug ? myBuyMarker : constants.empty_series, { name: 'BuyMarker', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShowDebug ? mySellMarker : constants.empty_series, { name: 'SellMarker', style: 'labels_above', color: '#EF5350', thickness: 3 });

// Signals for Scanner / Alerts / Strategy Tester
register_signal(for_every(myBuySignalOnChart, myVal => myVal > 0), 'Buy Signal');
register_signal(for_every(mySellSignalOnChart, myVal => myVal > 0), 'Sell Signal');