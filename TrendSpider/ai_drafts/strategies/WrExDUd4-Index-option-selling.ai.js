describe_indicator('Option Point', 'price');

// ━━━━━━━━━━ INPUTS ━━━━━━━━━━
const maTab = input.tab('Moving Averages');
const fastRow = maTab.row();
const myFastType = fastRow.select('Fast MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const myFastLen = fastRow.number('Fast MA Length', 9, { min: 1, max: 500 });
const slowRow = maTab.row();
const mySlowType = slowRow.select('Slow MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const mySlowLen = slowRow.number('Slow MA Length', 21, { min: 1, max: 500 });

const slopeTab = input.tab('Slope Filter');
const myUseSlopeFilter = slopeTab.boolean('Use Slope Filter', true);
const mySlopeLookback = slopeTab.number('Slope Lookback', 5, { min: 1, max: 200 });
// Shortened names to satisfy the input() name length limit
const myFastSlopeThreshold = slopeTab.number('Fast Slope Threshold', 0.05, { min: -100, max: 100, step: 0.01 });
const mySlowSlopeThreshold = slopeTab.number('Slow Slope Threshold', 0.02, { min: -100, max: 100, step: 0.01 });

const intradayTab = input.tab('Intraday Settings');
const myUseIntraday = intradayTab.boolean('Enable Intraday Time Filter', true);
const mySessionText = intradayTab.text('Trading Session (HHMM-HHMM)', '0920-1520');
const myCloseBeforeMarketEnd = intradayTab.boolean('Force Close At Session End', true);

const visualTab = input.tab('Visual Settings');
const myShowExitLabels = visualTab.boolean('Show EXIT Labels', true);

// ━━━━━━━━━━ MA FUNCTION ━━━━━━━━━━
function myComputeMA(_myType, _mySrc, _myLen) {
	if (_myType === 'EMA') return ema(_mySrc, _myLen);
	if (_myType === 'SMA') return sma(_mySrc, _myLen);
	return wma(_mySrc, _myLen);
}

const myFastMA = myComputeMA(myFastType, close, myFastLen);
const mySlowMA = myComputeMA(mySlowType, close, mySlowLen);

// ━━━━━━━━━━ SLOPE CALCULATIONS ━━━━━━━━━━
const myFastSlope = div(sub(myFastMA, shift(myFastMA, mySlopeLookback)), mySlopeLookback);
const mySlowSlope = div(sub(mySlowMA, shift(mySlowMA, mySlopeLookback)), mySlopeLookback);

// ━━━━━━━━━━ SESSION PARSING ━━━━━━━━━━
// Parses a session string formatted as "HHMM-HHMM" into minutes-of-day boundaries.
const mySessionParts = mySessionText.split('-');
assert(mySessionParts.length === 2, 'Session must be formatted as HHMM-HHMM');
const mySessionStartMinutes = parseInt(mySessionParts[0].slice(0, 2), 10) * 60 + parseInt(mySessionParts[0].slice(2, 4), 10);
const mySessionEndMinutes = parseInt(mySessionParts[1].slice(0, 2), 10) * 60 + parseInt(mySessionParts[1].slice(2, 4), 10);

function myIsInSession(_myTimestamp) {
	const myTimeData = time_of(_myTimestamp);
	const myMinutesOfDay = myTimeData.hours * 60 + myTimeData.minutes;
	return myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes;
}

// ━━━━━━━━━━ MAIN LOOP: position tracking, signals, EOD exit ━━━━━━━━━━
const mySellSignal = series_of(null);
const myExitSignal = series_of(null);
const myEodExitSignal = series_of(null);
const myPositionSizeSeries = series_of(0);
let myPositionSize = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myInSession = myIsInSession(time[myIndex]);
	const myPrevInSession = myIndex > 0 ? myIsInSession(time[myIndex - 1]) : myInSession;

	const myHasPrev = myIndex > 0 &&
		myFastMA[myIndex] != null && myFastMA[myIndex - 1] != null &&
		mySlowMA[myIndex] != null && mySlowMA[myIndex - 1] != null;

	const myCrossUnder = myHasPrev &&
		myFastMA[myIndex] < mySlowMA[myIndex] &&
		myFastMA[myIndex - 1] >= mySlowMA[myIndex - 1];

	const myCrossOver = myHasPrev &&
		myFastMA[myIndex] > mySlowMA[myIndex] &&
		myFastMA[myIndex - 1] <= mySlowMA[myIndex - 1];

	const myFastSlopeBearish = myFastSlope[myIndex] != null && myFastSlope[myIndex] < -myFastSlopeThreshold;
	const mySlowSlopeBearish = mySlowSlope[myIndex] != null && mySlowSlope[myIndex] < -mySlowSlopeThreshold;
	const mySlopeFilterPassed = !myUseSlopeFilter || (myFastSlopeBearish && mySlowSlopeBearish);

	const mySellCondition = myCrossUnder && mySlopeFilterPassed && (!myUseIntraday || myInSession);
	const myExitCondition = myCrossOver;
	const mySessionEnded = myUseIntraday && myCloseBeforeMarketEnd && !myInSession && myPrevInSession;

	// ENTRY
	if (mySellCondition && myPositionSize === 0) {
		myPositionSize = -1;
		mySellSignal[myIndex] = true;
	}

	// NORMAL EXIT
	if (myExitCondition && myPositionSize < 0) {
		myPositionSize = 0;
		myExitSignal[myIndex] = true;
	}

	// FORCE EXIT AT SESSION END
	if (mySessionEnded && myPositionSize < 0) {
		myPositionSize = 0;
		myEodExitSignal[myIndex] = true;
	}

	myPositionSizeSeries[myIndex] = myPositionSize;
}

// ━━━━━━━━━━ MA COLORS ━━━━━━━━━━
const myFastColor = for_every(myFastMA, mySlowMA, (_f, _s) => (_f != null && _s != null && _f > _s) ? 'lime' : 'red');

// ━━━━━━━━━━ PLOTS ━━━━━━━━━━
paint(myFastMA, { name: 'Fast MA', color: myFastColor, thickness: 2, forceUsePriceAxis: true });
paint(mySlowMA, { name: 'Slow MA', color: 'orange', thickness: 2, forceUsePriceAxis: true });

// ━━━━━━━━━━ SELL / EXIT / EOD LABELS ━━━━━━━━━━
const mySellMarks = for_every(mySellSignal, _s => _s ? constants.icons.arrow_down : null);
const myExitMarks = for_every(myExitSignal, _e => (myShowExitLabels && _e) ? constants.icons.arrow_up : null);
const myEodExitMarks = for_every(myEodExitSignal, _e => _e ? constants.icons.arrow_up : null);

paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });
paint(myExitMarks, { name: 'Exit', style: 'labels_below', color: 'green' });
paint(myEodExitMarks, { name: 'EodExit', style: 'labels_below', color: 'orange' });

// ━━━━━━━━━━ SIGNALS FOR SCANNER STRATEGY AND ALERTS ━━━━━━━━━━
register_signal(for_every(mySellSignal, _s => !!_s), 'Sell Entry Signal');
register_signal(for_every(myExitSignal, _e => !!_e), 'Exit Signal');
register_signal(for_every(myEodExitSignal, _e => !!_e), 'EOD Exit Signal');
register_signal(for_every(myPositionSizeSeries, _p => _p < 0), 'In Short Position');