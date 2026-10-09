describe_indicator('Multi Time Score', 'lower');

// NOTE: this is a signal/indicator conversion of the original Pine Script
// strategy. TrendSpider Custom JS indicators cannot submit broker orders,
// manage position size or run stop/limit exits like a Pine strategy() does.
// We reproduce the Buy/Sell signal logic and the weighted multi-timeframe
// score exactly, and expose Buy/Sell as register_signal() outputs so they
// can be used in Scanners, Alerts and the Strategy Tester module.

const myTab = input.tab('Settings');

const mySensitivity = myTab.number('Sensitivity', 10, { min: 10, max: 30 });
const myIndexPeriod = myTab.number('Index Period', 20, { min: 10, max: 100 });

const myImportanceRow1 = myTab.row();
const myImportance5M = myImportanceRow1.number('5M Importance', 1, { min: 1, max: 10 });
const myImportance15M = myImportanceRow1.number('15M Importance', 2, { min: 1, max: 10 });
const myImportance1H = myImportanceRow1.number('1H Importance', 4, { min: 1, max: 10 });

const myImportanceRow2 = myTab.row();
const myImportance4H = myImportanceRow2.number('4H Importance', 7, { min: 1, max: 10 });
const myImportance1D = myImportanceRow2.number('1D Importance', 9, { min: 1, max: 10 });
const myImportance1W = myImportanceRow2.number('1W Importance', 10, { min: 1, max: 10 });

const myDisplayTab = input.tab('Display');
const myShowScoreLine = myDisplayTab.boolean('Show Score Line', true);
const myShowBackground = myDisplayTab.boolean('Show Background', true);
const myShowSignals = myDisplayTab.boolean('Show Additional Signals', false);

// Fetch all the required timeframes in parallel
const [myData5M, myData15M, myData1H, myData4H, myData1D, myData1W] = await Promise.all([
	request.history(current.ticker, '5'),
	request.history(current.ticker, '15'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'W')
]);

assert(!myData5M.error, `Error fetching 5M data: ${myData5M.error}`);
assert(!myData15M.error, `Error fetching 15M data: ${myData15M.error}`);
assert(!myData1H.error, `Error fetching 1H data: ${myData1H.error}`);
assert(!myData4H.error, `Error fetching 4H data: ${myData4H.error}`);
assert(!myData1D.error, `Error fetching 1D data: ${myData1D.error}`);
assert(!myData1W.error, `Error fetching 1W data: ${myData1W.error}`);

// Computes tfHigh[1] and tfLow[1] (shifted by one bar on that tf, mirroring
// Pine's ta.highest(...)[1] inside request.security with lookahead_off),
// lands the values onto the current chart's time series, and fills gaps
// using "constant" (forward-fill) interpolation to avoid any repainting /
// look-ahead bias.
function myLandTFRange(_tfData) {
	const myTfHigh = shift(highest(_tfData.high, myIndexPeriod), 1);
	const myTfLow = shift(lowest(_tfData.low, myIndexPeriod), 1);

	const myHighLanded = interpolate_sparse_series(
		land_points_onto_series(_tfData.time, myTfHigh, time, 'le'),
		'constant'
	);
	const myLowLanded = interpolate_sparse_series(
		land_points_onto_series(_tfData.time, myTfLow, time, 'le'),
		'constant'
	);

	return { high: myHighLanded, low: myLowLanded };
}

const myRange5M = myLandTFRange(myData5M);
const myRange15M = myLandTFRange(myData15M);
const myRange1H = myLandTFRange(myData1H);
const myRange4H = myLandTFRange(myData4H);
const myRange1D = myLandTFRange(myData1D);
const myRange1W = myLandTFRange(myData1W);

// close[1] of the main chart (shared by every scoreFromRange() call)
const myPrevClose = shift(close, 1);

// score = ((close[1] - tfLow) / (tfHigh - tfLow)) * 100 - 50, or 0 if tfHigh == tfLow
function myScoreFromRange(_myRange) {
	return for_every(myPrevClose, _myRange.high, _myRange.low, (_c, _h, _l) => {
		if (_h === null || _l === null || _c === null) return 0;
		if (_h === _l) return 0;
		return (((_c - _l) / (_h - _l)) * 100.0) - 50.0;
	});
}

const myValue5M = myScoreFromRange(myRange5M);
const myValue15M = myScoreFromRange(myRange15M);
const myValue1H = myScoreFromRange(myRange1H);
const myValue4H = myScoreFromRange(myRange4H);
const myValue1D = myScoreFromRange(myRange1D);
const myValue1W = myScoreFromRange(myRange1W);

const myTotalWeight = myImportance5M + myImportance15M + myImportance1H + myImportance4H + myImportance1D + myImportance1W;

const myTotalRank = for_every(
	myValue5M, myValue15M, myValue1H, myValue4H, myValue1D, myValue1W,
	(_v5, _v15, _v1h, _v4h, _v1d, _v1w) => (
		(_v5 * myImportance5M +
		_v15 * myImportance15M +
		_v1h * myImportance1H +
		_v4h * myImportance4H +
		_v1d * myImportance1D +
		_v1w * myImportance1W) / myTotalWeight
	)
);

const myBuySignal = for_every(myTotalRank, _myRank => _myRank > mySensitivity);
const mySellSignal = for_every(myTotalRank, _myRank => _myRank < 0);

// Lines
paint(myShowScoreLine ? myTotalRank : constants.empty_series, { name: 'TotalScore', color: '#ffbe3c', thickness: 2 });
paint(myValue5M, { name: 'Score5M', hidden: true, color: '#aaaaaa' });
paint(myValue15M, { name: 'Score15M', hidden: true, color: '#aaaaaa' });
paint(myValue1H, { name: 'Score1H', hidden: true, color: '#aaaaaa' });
paint(myValue4H, { name: 'Score4H', hidden: true, color: '#aaaaaa' });
paint(myValue1D, { name: 'Score1D', hidden: true, color: '#aaaaaa' });
paint(myValue1W, { name: 'Score1W', hidden: true, color: '#aaaaaa' });

paint(horizontal_line(mySensitivity), { name: 'BuyLevel', color: '#4da3ff', style: 'dotted' });
paint(horizontal_line(0), { name: 'SellLevel', color: '#ff5a78', style: 'dotted' });

// Background approximation: color candles instead of a chart background,
// since this platform's Custom JS API has no bgcolor()-style full-pane
// background painter.
const myBackgroundColors = for_every(myBuySignal, mySellSignal, (_b, _s) => {
	if (!myShowBackground) return null;
	if (_b) return 'rgba(0,120,255,0.18)';
	if (_s) return 'rgba(255,70,90,0.18)';
	return 'rgba(160,160,170,0.07)';
});
color_candles(myBackgroundColors);

// Optional shape signals
const myBuyMarks = for_every(myBuySignal, _b => (myShowSignals && _b) ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellSignal, _s => (myShowSignals && _s) ? constants.icons.triangle_down : null);
paint(myBuyMarks, { style: 'labels_below', name: 'BuySignal', color: '#00ffaa' });
paint(mySellMarks, { style: 'labels_above', name: 'SellSignal', color: '#ff5a78' });

// Signals for Scanners/Alerts/Strategy Tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');