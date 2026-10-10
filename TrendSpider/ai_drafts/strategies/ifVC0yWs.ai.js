describe_indicator('Reversal Strategy v1', 'price');

// NOTE: This is a best-effort translation of a TradingView Pine Script
// strategy into TrendSpider Custom JS. Position-state tracking (the
// strategy.position_size == 0 check) is approximated with a simple
// stop/target simulation loop. Daily "force close" logic was commented
// out in the original Pine script, so it was not implemented here.

const myLeftBars = input.number('Pivot Left', 3, { min: 1, max: 50 });
const myRightBars = input.number('Pivot Right', 3, { min: 1, max: 50 });
const myConfirmTolTicks = input.number('HTF Confirm Tolerance (Ticks)', 150, { min: 1, max: 5000 });
const myEntryBufferTicks = input.number('Entry Buffer (Ticks)', 100, { min: 1, max: 5000 });
const myStopBufferTicks = input.number('Stop Buffer (Ticks)', 100, { min: 1, max: 5000 });
const myRR = input.number('CRV', 1.0, { min: 0.1, max: 20 });
const myShowZones = input.boolean('Show Zones', true);

// tick size approximation, based on the current symbol decimals
const myTick = Math.pow(10, -current.decimals);
const myConfirmTol = myConfirmTolTicks * myTick;
const myEntryBuffer = myEntryBufferTicks * myTick;
const myStopBuffer = myStopBufferTicks * myTick;

// Fetch H4, D1, W1 history
const [myH4Data, myD1Data, myW1Data] = await Promise.all([
	request.history(current.ticker, '240'),
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'W')
]);

assert(!myH4Data.error, 'Error fetching H4 data: ' + myH4Data.error);
assert(!myD1Data.error, 'Error fetching D1 data: ' + myD1Data.error);
assert(!myW1Data.error, 'Error fetching W1 data: ' + myW1Data.error);

// Builds a "confirmed, non-repainting, persistent last value" series,
// replicating Pine's `ta.pivothigh(...)[1]` plus a `var float` holder
// that keeps the last known value until updated.
function myBuildPersistentPivot(mySourceSeries, myLength, myIsHigh) {
	const myRawPivot = myIsHigh
		? pivot_high(mySourceSeries, myLength, myLength)
		: pivot_low(mySourceSeries, myLength, myLength);

	// Pine applies an extra [1] offset on top of the already-confirmed pivot.
	const myShiftedPivot = shift(myRawPivot, 1);

	// Forward-fill (constant interpolation keeps the indicator backtestable)
	return interpolate_sparse_series(myShiftedPivot, 'constant');
}

const myH4ResPersistent = myBuildPersistentPivot(myH4Data.high, myLeftBars, true);
const myH4SupPersistent = myBuildPersistentPivot(myH4Data.low, myLeftBars, false);
const myD1ResPersistent = myBuildPersistentPivot(myD1Data.high, myLeftBars, true);
const myD1SupPersistent = myBuildPersistentPivot(myD1Data.low, myLeftBars, false);
const myW1ResPersistent = myBuildPersistentPivot(myW1Data.high, myLeftBars, true);
const myW1SupPersistent = myBuildPersistentPivot(myW1Data.low, myLeftBars, false);

// Land each HTF persistent series onto the current chart's time axis
const myH4ResLanded = interpolate_sparse_series(
	land_points_onto_series(myH4Data.time, myH4ResPersistent, time, 'le'),
	'constant'
);
const myH4SupLanded = interpolate_sparse_series(
	land_points_onto_series(myH4Data.time, myH4SupPersistent, time, 'le'),
	'constant'
);
const myD1ResLanded = interpolate_sparse_series(
	land_points_onto_series(myD1Data.time, myD1ResPersistent, time, 'le'),
	'constant'
);
const myD1SupLanded = interpolate_sparse_series(
	land_points_onto_series(myD1Data.time, myD1SupPersistent, time, 'le'),
	'constant'
);
const myW1ResLanded = interpolate_sparse_series(
	land_points_onto_series(myW1Data.time, myW1ResPersistent, time, 'le'),
	'constant'
);
const myW1SupLanded = interpolate_sparse_series(
	land_points_onto_series(myW1Data.time, myW1SupPersistent, time, 'le'),
	'constant'
);

const myCandleCount = close.length;
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

// Position state simulation (mimics strategy.position_size == 0 checks
// plus the bracket stop/limit exit logic from the Pine strategy)
let myPositionSize = 0;
let myStopLevel = null;
let myTargetLevel = null;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	// Process pending exits first (bracket order simulation)
	if (myPositionSize === 1) {
		if (low[myIndex] <= myStopLevel || high[myIndex] >= myTargetLevel) {
			myPositionSize = 0;
			myStopLevel = null;
			myTargetLevel = null;
		}
	}
	else if (myPositionSize === -1) {
		if (high[myIndex] >= myStopLevel || low[myIndex] <= myTargetLevel) {
			myPositionSize = 0;
			myStopLevel = null;
			myTargetLevel = null;
		}
	}

	const myH4Sup = myH4SupLanded[myIndex];
	const myH4Res = myH4ResLanded[myIndex];
	const myD1Sup = myD1SupLanded[myIndex];
	const myD1Res = myD1ResLanded[myIndex];
	const myW1Sup = myW1SupLanded[myIndex];
	const myW1Res = myW1ResLanded[myIndex];

	const myNearSupD1 = myH4Sup != null && myD1Sup != null && Math.abs(myH4Sup - myD1Sup) <= myConfirmTol * 2;
	const myNearSupW1 = myH4Sup != null && myW1Sup != null && Math.abs(myH4Sup - myW1Sup) <= myConfirmTol * 2;
	const myNearResD1 = myH4Res != null && myD1Res != null && Math.abs(myH4Res - myD1Res) <= myConfirmTol * 2;
	const myNearResW1 = myH4Res != null && myW1Res != null && Math.abs(myH4Res - myW1Res) <= myConfirmTol * 2;

	const mySupportConfirmed = myH4Sup != null && (myNearSupD1 || myNearSupW1);
	const myResistanceConfirmed = myH4Res != null && (myNearResD1 || myNearResW1);

	const mySupportTouchedRecent = mySupportConfirmed && myH4Sup != null &&
		(low[myIndex] <= myH4Sup + myEntryBuffer || low[myIndex - 1] <= myH4Sup + myEntryBuffer);
	const myResistanceTouchedRecent = myResistanceConfirmed && myH4Res != null &&
		(high[myIndex] >= myH4Res - myEntryBuffer || high[myIndex - 1] >= myH4Res - myEntryBuffer);

	const myBullishReversal = close[myIndex] > open[myIndex] && close[myIndex] > close[myIndex - 1] && myH4Sup != null && close[myIndex] > myH4Sup;
	const myBearishReversal = close[myIndex] < open[myIndex] && close[myIndex] < close[myIndex - 1] && myH4Res != null && close[myIndex] < myH4Res;

	const myLongCondition = myPositionSize === 0 && mySupportTouchedRecent && myBullishReversal;
	const myShortCondition = myPositionSize === 0 && myResistanceTouchedRecent && myBearishReversal;

	if (myLongCondition) {
		const myLongStop = myH4Sup - myStopBuffer;
		const myLongRisk = close[myIndex] - myLongStop;

		if (myLongRisk > 0) {
			myLongSignal[myIndex] = true;
			myPositionSize = 1;
			myStopLevel = myLongStop;
			myTargetLevel = close[myIndex] + myLongRisk * myRR;
		}
	}
	else if (myShortCondition) {
		const myShortStop = myH4Res + myStopBuffer;
		const myShortRisk = myShortStop - close[myIndex];

		if (myShortRisk > 0) {
			myShortSignal[myIndex] = true;
			myPositionSize = -1;
			myStopLevel = myShortStop;
			myTargetLevel = close[myIndex] - myShortRisk * myRR;
		}
	}
}

// Zones
paint(myShowZones ? myH4SupLanded : constants.empty_series, { name: 'H4 Support', color: '#2ca599', style: 'line', thickness: 2 });
paint(myShowZones ? myH4ResLanded : constants.empty_series, { name: 'H4 Resistance', color: '#ee5451', style: 'line', thickness: 2 });
paint(myShowZones ? myD1SupLanded : constants.empty_series, { name: 'D1 Support', color: '#2ca599', style: 'dotted' });
paint(myShowZones ? myD1ResLanded : constants.empty_series, { name: 'D1 Resistance', color: '#ee5451', style: 'dotted' });
paint(myShowZones ? myW1SupLanded : constants.empty_series, { name: 'W1 Support', color: '#2ca599', style: 'dotted' });
paint(myShowZones ? myW1ResLanded : constants.empty_series, { name: 'W1 Resistance', color: '#ee5451', style: 'dotted' });

// Signal markers
const myLongMarks = for_every(myLongSignal, low, (_signal, _low) => _signal ? _low : null);
const myShortMarks = for_every(myShortSignal, high, (_signal, _high) => _signal ? _high : null);

paint(myLongMarks, { name: 'Long Signal Marker', style: 'labels_below', color: '#2ca599' });
paint(myShortMarks, { name: 'Short Signal Marker', style: 'labels_above', color: '#ee5451' });

// Signals for scanners/alerts/strategies
// Renamed signal names so they no longer collide with the paint() line
// names above - the engine shares one namespace between paint() lines
// and register_signal() outputs, so identical names triggered the
// "already exists" error.
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');