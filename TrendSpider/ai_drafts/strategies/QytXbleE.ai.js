describe_indicator('Weekend Trend Trader - Presets', 'price');

// Preset selector, mirrors the Pine "preset" input
const myPreset = input.select('Preset', 'Original', ['Original', 'Performance']);
const mySpxTicker = input.symbol('Index Symbol ($SPX)', 'SPX');

// This script only makes sense on Weekly charts, just like the Pine original.
// Instead of throwing a hard error (which breaks the whole indicator and
// shows a scary error to the user), we now just skip the calculation when
// the chart is not weekly, and paint empty series instead. This keeps the
// number and names of paint()/register_signal() calls constant.
const myIsWeekly = current.resolution === 'W';

// Preset parameters (direct port of the Pine switch statement)
let myRocThreshold = 30;
let myRocLength = 20;
let myMaLength = 10;
let myBreakoutLength = 20;
let myInitialStopPct = 40;
let myTightStopPct = 10;

if (myPreset === 'Performance') {
	myRocThreshold = 40;
	myRocLength = 10;
	myMaLength = 10;
	myBreakoutLength = 30;
	myInitialStopPct = 50;
	myTightStopPct = 30;
}

// Default (empty) outputs, used whenever the chart is not weekly
let myBreakoutLevel = constants.empty_series;
let myTrailingStopOut = constants.empty_series;
let mySpxTrendIcon = constants.empty_series;
let mySpxTrendColor = constants.empty_series;
let myBuySignal = series_of(false);
let myCloseSignal = series_of(false);
let myLongCondition = series_of(false);
let myMomentumOk = series_of(false);
let myIndexUp = series_of(false);

if (myIsWeekly) {
	// === SPX filter ===
	const mySpxData = await request.history(mySpxTicker, 'W');
	assert(!mySpxData.error, `Error fetching ${mySpxTicker}: ${mySpxData.error}`);

	const mySpxMA = sma(mySpxData.close, myMaLength);
	const mySpxCloseLanded = interpolate_sparse_series(
		land_points_onto_series(mySpxData.time, mySpxData.close, time, 'le'),
		'constant'
	);
	const mySpxMALanded = interpolate_sparse_series(
		land_points_onto_series(mySpxData.time, mySpxMA, time, 'le'),
		'constant'
	);
	myIndexUp = for_every(mySpxCloseLanded, mySpxMALanded, (_c, _m) => _c > _m);

	// === Breakout ===
	myBreakoutLevel = highest(high, myBreakoutLength);
	const myBreakoutLevelPrev = shift(myBreakoutLevel, 1);
	const myIsBreakout = for_every(close, myBreakoutLevelPrev, (_c, _b) => _c > _b);

	// === ROC / Momentum ===
	const myRoc = roc(close, myRocLength);
	myMomentumOk = for_every(myRoc, _r => _r > myRocThreshold);

	// === Entry condition ===
	myLongCondition = for_every(myIsBreakout, myMomentumOk, (_b, _m) => _b && _m);

	// === Trailing stop state machine (sequential, mirrors Pine var state) ===
	myTrailingStopOut = series_of(null);
	myBuySignal = series_of(false);
	myCloseSignal = series_of(false);

	let myHighestHigh = null;
	let myTrailingStop = null;
	let myPositionSize = 0;

	for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
		const myLc = myLongCondition[myIndex];

		if (myPositionSize > 0) {
			myHighestHigh = myHighestHigh === null ? high[myIndex] : Math.max(myHighestHigh, high[myIndex]);
			const myStopPct = myIndexUp[myIndex] ? myInitialStopPct : myTightStopPct;
			const myNewStop = myHighestHigh * (1 - myStopPct / 100);
			myTrailingStop = myTrailingStop === null ? myNewStop : Math.max(myTrailingStop, myNewStop);

			if (close[myIndex] < myTrailingStop) {
				myCloseSignal[myIndex] = true;
				myPositionSize = 0;
			}
		}
		else if (myLc) {
			myHighestHigh = high[myIndex];
			const myStopPct = myIndexUp[myIndex] ? myInitialStopPct : myTightStopPct;
			myTrailingStop = high[myIndex] * (1 - myStopPct / 100);
			myBuySignal[myIndex] = true;
			myPositionSize = 1;
		}
		else {
			myHighestHigh = null;
			myTrailingStop = null;
		}

		myTrailingStopOut[myIndex] = (myPositionSize > 0 || myLc) ? myTrailingStop : null;
	}

	// SPX trend marker (replaces plotshape "SPX Trend" at bottom)
	mySpxTrendIcon = for_every(myIndexUp, _u => constants.icons.square);
	mySpxTrendColor = for_every(myIndexUp, _u => _u ? '#26a69a' : '#ef5350');
}

// === Visuals ===
paint(myBreakoutLevel, { name: 'Breakout High', color: '#00bcd4', thickness: 1, style: 'line' });
paint(myTrailingStopOut, { name: 'Trailing Stop', color: '#ef5350', thickness: 2, style: 'line' });
paint(mySpxTrendIcon, { name: 'SPX Trend', style: 'labels_below', color: mySpxTrendColor });

// === Signals for scanner/strategy/alerts ===
register_signal(myBuySignal, 'Buy Entry');
register_signal(myCloseSignal, 'Close Position');
register_signal(myLongCondition, 'Long Condition');
register_signal(myMomentumOk, 'Momentum OK');
register_signal(myIndexUp, 'SPX Above MA');