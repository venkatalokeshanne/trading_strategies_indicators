describe_indicator('Option Point MA Cross Strategy', 'price');

// ───────────── INPUTS ─────────────
const maTab = input.tab('Moving Average Settings');
const maRow1 = maTab.row();
const myFastType = maRow1.select('Fast MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const myFastLen = maRow1.number('Fast MA Length', 9, { min: 1, max: 500 });
const maRow2 = maTab.row();
const mySlowType = maRow2.select('Slow MA Type', 'EMA', ['EMA', 'SMA', 'WMA']);
const mySlowLen = maRow2.number('Slow MA Length', 21, { min: 1, max: 500 });

const slopeTab = input.tab('Slope Filter');
const myUseSlopeFilter = slopeTab.boolean('Use Slope Filter', true);
const mySlopeLookback = slopeTab.number('Slope Lookback', 3, { min: 1, max: 100 });
// Shortened titles below (previous titles were too long for the input() name field)
const myFastSlopeThreshold = slopeTab.number('Fast Slope Threshold', 0.05, { min: -100, max: 100, step: 0.01 });
const mySlowSlopeThreshold = slopeTab.number('Slow Slope Threshold', 0.02, { min: -100, max: 100, step: 0.01 });

const intradayTab = input.tab('Intraday Settings');
const myUseIntraday = intradayTab.boolean('Enable Intraday Filter', true);
const mySessionTime = intradayTab.text('Session (HHMM-HHMM)', '0920-1520');
const myCloseBeforeMarketEnd = intradayTab.boolean('Force Close At End', true);

const visualTab = input.tab('Visual Settings');
const myShowExitLabels = visualTab.boolean('Show EXIT Labels', true);
const myShowBackground = visualTab.boolean('Trend Candle Coloring', false);

// ───────────── MA FUNCTION ─────────────
function myComputeMA(myType, mySrc, myLen) {
	if (myType === 'EMA') return ema(mySrc, myLen);
	if (myType === 'SMA') return sma(mySrc, myLen);
	return wma(mySrc, myLen);
}

const myFastMA = myComputeMA(myFastType, close, myFastLen);
const mySlowMA = myComputeMA(mySlowType, close, mySlowLen);

// ───────────── SLOPE CALCULATIONS ─────────────
const myFastSlope = div(sub(myFastMA, shift(myFastMA, mySlopeLookback)), mySlopeLookback);
const mySlowSlope = div(sub(mySlowMA, shift(mySlowMA, mySlopeLookback)), mySlopeLookback);

// ───────────── SESSION PARSING ─────────────
// Parses "HHMM-HHMM" format into minutes-of-day boundaries.
const mySessionParts = mySessionTime.split('-');
assert(mySessionParts.length === 2, 'Session format must be HHMM-HHMM');
const mySessionStartMinutes = parseInt(mySessionParts[0].slice(0, 2), 10) * 60 + parseInt(mySessionParts[0].slice(2, 4), 10);
const mySessionEndMinutes = parseInt(mySessionParts[1].slice(0, 2), 10) * 60 + parseInt(mySessionParts[1].slice(2, 4), 10);

const myInSession = time.map(myTimestamp => {
	const myTimeInfo = time_of(myTimestamp);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	return myMinutesOfDay >= mySessionStartMinutes && myMinutesOfDay <= mySessionEndMinutes;
});

// ───────────── CROSS CONDITIONS ─────────────
const myCrossUnder = series_of(false);
const myCrossOver = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myCrossUnder[myIndex] = myFastMA[myIndex] < mySlowMA[myIndex] && myFastMA[myIndex - 1] >= mySlowMA[myIndex - 1];
	myCrossOver[myIndex] = myFastMA[myIndex] > mySlowMA[myIndex] && myFastMA[myIndex - 1] <= mySlowMA[myIndex - 1];
}

// ───────────── SIGNAL AND POSITION SIMULATION ─────────────
const mySellSignal = series_of(false);
const myExitSignal = series_of(false);
const myEodExitSignal = series_of(false);
let myPositionSize = 0;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myFastSlopeBearish = myFastSlope[myIndex] < -myFastSlopeThreshold;
	const mySlowSlopeBearish = mySlowSlope[myIndex] < -mySlowSlopeThreshold;
	const mySlopeFilterPassed = !myUseSlopeFilter || (myFastSlopeBearish && mySlowSlopeBearish);
	const mySellCondition = myCrossUnder[myIndex] && mySlopeFilterPassed && (!myUseIntraday || myInSession[myIndex]);
	const myExitCondition = myCrossOver[myIndex];
	const mySessionEnded = myUseIntraday && myCloseBeforeMarketEnd && !myInSession[myIndex] && myInSession[myIndex - 1];

	if (mySellCondition && myPositionSize === 0) {
		mySellSignal[myIndex] = true;
		myPositionSize = -1;
	}
	if (myExitCondition && myPositionSize < 0) {
		myExitSignal[myIndex] = true;
		myPositionSize = 0;
	}
	if (mySessionEnded && myPositionSize < 0) {
		myEodExitSignal[myIndex] = true;
		myPositionSize = 0;
	}
}

// ───────────── COLORS ─────────────
const myFastColor = for_every(myFastMA, mySlowMA, (_fast, _slow) => _fast > _slow ? 'lime' : 'red');

// ───────────── CANDLE COLORING (approximation of background shading) ─────────────
const myCandleColors = for_every(myFastMA, mySlowMA, (_fast, _slow) => myShowBackground ? (_fast < _slow ? 'rgba(255,0,0,0.08)' : 'rgba(0,255,0,0.08)') : null);
color_candles(myCandleColors);

// ───────────── PLOTS ─────────────
paint(myFastMA, { name: 'Fast MA', color: myFastColor, thickness: 2 });
paint(mySlowMA, { name: 'Slow MA', color: 'orange', thickness: 2 });

// ───────────── LABELS ─────────────
const mySellLabels = for_every(mySellSignal, _sell => _sell ? constants.icons.arrow_down : null);
paint(mySellLabels, { name: 'Sell Label', style: 'labels_above', color: 'red' });

const myExitLabels = for_every(myExitSignal, _exit => (myShowExitLabels && _exit) ? constants.icons.arrow_up : null);
paint(myExitLabels, { name: 'Exit Label', style: 'labels_below', color: 'green' });

const myEodExitLabels = for_every(myEodExitSignal, _eod => _eod ? constants.icons.arrow_up : null);
paint(myEodExitLabels, { name: 'Eod Exit Label', style: 'labels_below', color: 'orange' });

// ───────────── SIGNALS FOR SCANNER STRATEGY ALERT ─────────────
register_signal(mySellSignal, 'Sell Signal');
register_signal(myExitSignal, 'Exit Signal');
register_signal(myEodExitSignal, 'Eod Exit Signal');