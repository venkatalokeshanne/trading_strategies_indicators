describe_indicator('Option Point MA Cross Strategy', 'price');

// ───────────── INPUTS ─────────────
const maTab = input.tab('Moving Average Settings');
const fastRow = maTab.row();
const myFastType = fastRow.select('Fast MA Type', 'ema', ['ema', 'sma', 'wma']);
const myFastLen = fastRow.number('Fast MA Length', 9, { min: 1, max: 500 });
const slowRow = maTab.row();
const mySlowType = slowRow.select('Slow MA Type', 'ema', ['ema', 'sma', 'wma']);
const mySlowLen = slowRow.number('Slow MA Length', 21, { min: 1, max: 500 });

const slopeTab = input.tab('Slope Filter');
const myUseSlopeFilter = slopeTab.boolean('Use Slope Filter', true);
const mySlopeLookback = slopeTab.number('Slope Lookback', 5, { min: 1, max: 200 });
// Shortened input names to satisfy the platform's name length limit
const myFastSlopeThreshold = slopeTab.number('Fast Neg Slope Thresh', 0.05, { min: -100, max: 100, step: 0.01 });
const mySlowSlopeThreshold = slopeTab.number('Slow Neg Slope Thresh', 0.02, { min: -100, max: 100, step: 0.01 });

const intradayTab = input.tab('Intraday Settings');
const myUseIntraday = intradayTab.boolean('Enable Intraday Time Filter', true);
const mySessionStart = intradayTab.text('Session Start (HHMM)', '0915');
const mySessionEnd = intradayTab.text('Session End (HHMM)', '1530');
const myCloseBeforeEnd = intradayTab.boolean('Force Close At Session End', true);

const visualTab = input.tab('Visual Settings');
const myShowExitLabels = visualTab.boolean('Show EXIT Labels', true);

// ───────────── MA FUNCTION ─────────────
function myComputeMA(_myType, _mySrc, _myLen) {
	if (_myType == 'ema') return ema(_mySrc, _myLen);
	if (_myType == 'sma') return sma(_mySrc, _myLen);
	return wma(_mySrc, _myLen);
}

const myFastMA = myComputeMA(myFastType, close, myFastLen);
const mySlowMA = myComputeMA(mySlowType, close, mySlowLen);

// ───────────── SLOPE CALCULATIONS ─────────────
const myFastSlope = div(sub(myFastMA, shift(myFastMA, mySlopeLookback)), mySlopeLookback);
const mySlowSlope = div(sub(mySlowMA, shift(mySlowMA, mySlopeLookback)), mySlopeLookback);

// ───────────── SESSION FILTER ─────────────
// Parses "HHMM" strings into { hours, minutes }
function myParseHHMM(_myStr) {
	const myNum = parseInt(_myStr, 10) || 0;
	return { hours: Math.floor(myNum / 100), minutes: myNum % 100 };
}

const myStartParsed = myParseHHMM(mySessionStart);
const myEndParsed = myParseHHMM(mySessionEnd);

const myInSession = time.map(_myT => {
	const myTimeInfo = time_of(_myT);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMinutes = myStartParsed.hours * 60 + myStartParsed.minutes;
	const myEndMinutes = myEndParsed.hours * 60 + myEndParsed.minutes;
	return myMinutesOfDay >= myStartMinutes && myMinutesOfDay <= myEndMinutes;
});

// ───────────── MAIN LOGIC LOOP ─────────────
// Position tracking is sequential (depends on previous state), so a plain loop
// (not calling indicator functions) is used here, as required.
const myCandleCount = close.length;
const mySellEntryMarks = series_of(null);
const myExitMarks = series_of(null);
const myEodExitMarks = series_of(null);
const mySellSignal = series_of(false);
const myExitSignal = series_of(false);
const myEodExitSignal = series_of(false);

let myPosition = 0; // 0 = flat, -1 = short

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myCrossUnder = myFastMA[myIndex] < mySlowMA[myIndex] && myFastMA[myIndex - 1] >= mySlowMA[myIndex - 1];
	const myCrossOver = myFastMA[myIndex] > mySlowMA[myIndex] && myFastMA[myIndex - 1] <= mySlowMA[myIndex - 1];
	const myFastSlopeBearish = myFastSlope[myIndex] != null && myFastSlope[myIndex] < -myFastSlopeThreshold;
	const mySlowSlopeBearish = mySlowSlope[myIndex] != null && mySlowSlope[myIndex] < -mySlowSlopeThreshold;
	const mySlopeFilterPassed = !myUseSlopeFilter || (myFastSlopeBearish && mySlowSlopeBearish);
	const mySellCondition = myCrossUnder && mySlopeFilterPassed && (!myUseIntraday || myInSession[myIndex]);
	const myExitCondition = myCrossOver;
	const mySessionEnded = myUseIntraday && myCloseBeforeEnd && !myInSession[myIndex] && myInSession[myIndex - 1];

	let mySellFired = false;
	let myExitFired = false;
	let myEodFired = false;

	if (mySellCondition && myPosition == 0) {
		myPosition = -1;
		mySellFired = true;
	}
	if (myExitCondition && myPosition < 0) {
		myPosition = 0;
		myExitFired = true;
	}
	if (mySessionEnded && myPosition < 0) {
		myPosition = 0;
		myEodFired = true;
	}

	mySellSignal[myIndex] = mySellFired;
	myExitSignal[myIndex] = myExitFired;
	myEodExitSignal[myIndex] = myEodFired;

	if (mySellFired) mySellEntryMarks[myIndex] = constants.icons.triangle_down;
	if (myShowExitLabels && myExitFired) myExitMarks[myIndex] = constants.icons.triangle_up;
	if (myEodFired) myEodExitMarks[myIndex] = constants.icons.triangle_up;
}

// ───────────── PLOTS ─────────────
const myFastColor = for_every(myFastMA, mySlowMA, (_myF, _myS) => _myF > _myS ? 'lime' : 'red');
paint(myFastMA, { name: 'FastMA', color: myFastColor, thickness: 2 });
paint(mySlowMA, { name: 'SlowMA', color: 'orange', thickness: 2 });
paint(mySellEntryMarks, { name: 'SellMarks', style: 'labels_above', color: 'red' });
paint(myExitMarks, { name: 'ExitMarks', style: 'labels_below', color: 'green' });
paint(myEodExitMarks, { name: 'EodExitMarks', style: 'labels_below', color: 'orange' });

// ───────────── SIGNALS ─────────────
register_signal(mySellSignal, 'Sell Entry');
register_signal(myExitSignal, 'Exit Short');
register_signal(myEodExitSignal, 'EOD Exit');