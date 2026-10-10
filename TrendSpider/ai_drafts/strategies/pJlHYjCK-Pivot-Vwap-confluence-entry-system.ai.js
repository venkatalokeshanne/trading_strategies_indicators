describe_indicator('Pivot VWAP Strategy', 'price');

// NOTE: this is a best-effort conversion of a stateful Pine Script
// strategy. Session/extended-hours detection, and the exact Pine
// `session.ismarket` semantics are approximated (see assumptions
// flagged below). All math (pivots, VWAP, signal logic) is
// reproduced bar-by-bar using a sequential loop, since the original
// script is heavily stateful (counters, position tracking, etc.)
// and cannot be expressed via vectorized built-ins.

const myStartHour = input.number('Window Start Hour', 9, { min: 0, max: 23 });
const myStartMinute = input.number('Window Start Minute', 30, { min: 0, max: 59 });
const myEndHour = input.number('Window End Hour', 14, { min: 0, max: 23 });
const myEndMinute = input.number('Window End Minute', 0, { min: 0, max: 59 });
const myMaxSignalsPerDay = input.number('Max Signals Per Day', 2, { min: 1, max: 10 });

// ------------------------------------------------------------------
// Fetch daily data to compute previous day's High/Low/Close
// ------------------------------------------------------------------
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

// Build "previous day" series aligned to each daily bar's own timestamp,
// so that when landed onto intraday candles of "that day", we get
// prior day's H/L/C (mirrors Pine's request.security(..., high[1])).
const myPrevHighDaily = series_of(null);
const myPrevLowDaily = series_of(null);
const myPrevCloseDaily = series_of(null);

for (let myDayIndex = 1; myDayIndex < myDailyData.time.length; myDayIndex += 1) {
	myPrevHighDaily[myDayIndex] = myDailyData.high[myDayIndex - 1];
	myPrevLowDaily[myDayIndex] = myDailyData.low[myDayIndex - 1];
	myPrevCloseDaily[myDayIndex] = myDailyData.close[myDayIndex - 1];
}

const myPrevHighLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myPrevHighDaily, time, 'le'),
	'constant'
);
const myPrevLowLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myPrevLowDaily, time, 'le'),
	'constant'
);
const myPrevCloseLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myPrevCloseDaily, time, 'le'),
	'constant'
);

// ------------------------------------------------------------------
// Compute pivots, VWAP and signals in one sequential pass
// ------------------------------------------------------------------
const myCandleCount = close.length;

const myDP = series_of(null);
const myDR1 = series_of(null);
const myDR2 = series_of(null);
const myDR3 = series_of(null);
const myDR4 = series_of(null);
const myDR5 = series_of(null);
const myDS1 = series_of(null);
const myDS2 = series_of(null);
const myDS3 = series_of(null);
const myDS4 = series_of(null);
const myDS5 = series_of(null);

const myVwapSeries = series_of(null);

const myLongSignalMarks = series_of(null);
const myShortSignalMarks = series_of(null);

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);
const myInTimeWindow = series_of(false);

let myVwapNum = 0;
let myVwapDen = 0;
let myLastSessionDay = null;
let myDailySignalCount = 0;
let myLastSignalDay = null;
let myPositionSize = 0; // 1 long, -1 short, 0 flat
let myBelowVwapCount = 0;
let myAboveVwapCount = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = myTimeInfo.year * 1000 + myTimeInfo.dayOfYear;

	// Session reset for VWAP (approximation: assumes every candle is a
	// regular market-session candle; extended-hours filtering is not
	// available on the Custom JS API in the same way as Pine's
	// session.ismarket)
	if (myLastSessionDay !== myDayKey) {
		myVwapNum = 0;
		myVwapDen = 0;
		myLastSessionDay = myDayKey;
	}

	myVwapNum += hlc3[myIndex] * volume[myIndex];
	myVwapDen += volume[myIndex];
	const myVwapValue = myVwapDen > 0 ? myVwapNum / myVwapDen : null;
	myVwapSeries[myIndex] = myVwapValue;

	// Pivot levels (previous day based)
	const myPrevHigh = myPrevHighLanded[myIndex];
	const myPrevLow = myPrevLowLanded[myIndex];
	const myPrevClose = myPrevCloseLanded[myIndex];

	let myPivotsReady = myPrevHigh != null && myPrevLow != null && myPrevClose != null;
	let myDpValue = null, myDr1 = null, myDr2 = null, myDr3 = null, myDr4 = null, myDr5 = null;
	let myDs1 = null, myDs2 = null, myDs3 = null, myDs4 = null, myDs5 = null;

	if (myPivotsReady) {
		myDpValue = (myPrevHigh + myPrevLow + myPrevClose) / 3;
		myDr1 = 2 * myDpValue - myPrevLow;
		myDr2 = myDpValue + (myPrevHigh - myPrevLow);
		myDr3 = myPrevHigh + 2 * (myDpValue - myPrevLow);
		myDs1 = 2 * myDpValue - myPrevHigh;
		myDs2 = myDpValue - (myPrevHigh - myPrevLow);
		myDs3 = myPrevLow - 2 * (myPrevHigh - myDpValue);

		const myRange1 = myDr1 - myDs1;
		myDr4 = myDr3 + myRange1;
		myDr5 = myDr4 + myRange1;
		myDs4 = myDs3 - myRange1;
		myDs5 = myDs4 - myRange1;
	}

	myDP[myIndex] = myDpValue;
	myDR1[myIndex] = myDr1;
	myDR2[myIndex] = myDr2;
	myDR3[myIndex] = myDr3;
	myDR4[myIndex] = myDr4;
	myDR5[myIndex] = myDr5;
	myDS1[myIndex] = myDs1;
	myDS2[myIndex] = myDs2;
	myDS3[myIndex] = myDs3;
	myDS4[myIndex] = myDs4;
	myDS5[myIndex] = myDs5;

	// Time window filter (exchange local time, via time_of)
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myStartMinutes = myStartHour * 60 + myStartMinute;
	const myEndMinutes = myEndHour * 60 + myEndMinute;
	const myInTime = myMinutesOfDay >= myStartMinutes && myMinutesOfDay <= myEndMinutes;
	myInTimeWindow[myIndex] = myInTime;

	// Daily signal counter reset
	const myCurrentDayOfMonth = myTimeInfo.dayOfMonth;
	if (myCurrentDayOfMonth !== myLastSignalDay) {
		myDailySignalCount = 0;
	}

	const myCanTrade = myInTime && myDailySignalCount < myMaxSignalsPerDay;

	// Signal logic
	const myCheckLong = _p => myVwapValue != null && _p != null &&
		low[myIndex] < _p && low[myIndex] < myVwapValue &&
		close[myIndex] > _p && close[myIndex] > myVwapValue;

	const myCheckShort = _p => myVwapValue != null && _p != null &&
		high[myIndex] > _p && high[myIndex] > myVwapValue &&
		close[myIndex] < _p && close[myIndex] < myVwapValue;

	const myPivotLevels = [myDpValue, myDr1, myDr2, myDr3, myDr4, myDr5, myDs1, myDs2, myDs3, myDs4, myDs5];

	const myLongSignal = myCanTrade && myPivotLevels.some(myCheckLong);
	const myShortSignal = myCanTrade && myPivotLevels.some(myCheckShort);

	myLongSignalMarks[myIndex] = myLongSignal ? low[myIndex] : null;
	myShortSignalMarks[myIndex] = myShortSignal ? high[myIndex] : null;

	// Entries
	if (myLongSignal && myPositionSize === 0) {
		myLongEntrySignal[myIndex] = true;
		myPositionSize = 1;
		myDailySignalCount += 1;
		myLastSignalDay = myCurrentDayOfMonth;
		myBelowVwapCount = 0;
	}
	else if (myShortSignal && myPositionSize === 0) {
		myShortEntrySignal[myIndex] = true;
		myPositionSize = -1;
		myDailySignalCount += 1;
		myLastSignalDay = myCurrentDayOfMonth;
		myAboveVwapCount = 0;
	}

	// Exits
	if (myPositionSize > 0) {
		if (myVwapValue != null && close[myIndex] < myVwapValue) {
			myBelowVwapCount += 1;
		}
		else {
			myBelowVwapCount = 0;
		}
		if (myBelowVwapCount >= 2) {
			myLongExitSignal[myIndex] = true;
			myPositionSize = 0;
			myBelowVwapCount = 0;
		}
	}

	if (myPositionSize < 0) {
		if (myVwapValue != null && close[myIndex] > myVwapValue) {
			myAboveVwapCount += 1;
		}
		else {
			myAboveVwapCount = 0;
		}
		if (myAboveVwapCount >= 2) {
			myShortExitSignal[myIndex] = true;
			myPositionSize = 0;
			myAboveVwapCount = 0;
		}
	}
}

// ------------------------------------------------------------------
// Painting
// ------------------------------------------------------------------
paint(myVwapSeries, { name: 'VWAP', color: '#f1c40f', thickness: 2, style: 'line' });

paint(myDP, { name: 'P', color: '#ffffff', thickness: 1, style: 'dotted' });
paint(myDR1, { name: 'R1', color: '#e74c3c', thickness: 1, style: 'dotted' });
paint(myDR2, { name: 'R2', color: '#e74c3c', thickness: 1, style: 'dotted' });
paint(myDR3, { name: 'R3', color: '#e74c3c', thickness: 1, style: 'dotted' });
paint(myDR4, { name: 'R4', color: '#e67e22', thickness: 1, style: 'dotted' });
paint(myDR5, { name: 'R5', color: '#e67e22', thickness: 1, style: 'dotted' });
paint(myDS1, { name: 'S1', color: '#2ecc71', thickness: 1, style: 'dotted' });
paint(myDS2, { name: 'S2', color: '#2ecc71', thickness: 1, style: 'dotted' });
paint(myDS3, { name: 'S3', color: '#2ecc71', thickness: 1, style: 'dotted' });
paint(myDS4, { name: 'S4', color: '#00e676', thickness: 1, style: 'dotted' });
paint(myDS5, { name: 'S5', color: '#00e676', thickness: 1, style: 'dotted' });

paint(myLongSignalMarks, { name: 'LongMark', style: 'labels_below', color: '#2ecc71' });
paint(myShortSignalMarks, { name: 'ShortMark', style: 'labels_above', color: '#e74c3c' });

// ------------------------------------------------------------------
// Register signals for scanners / alerts / backtests
// ------------------------------------------------------------------
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');
register_signal(myInTimeWindow, 'In Trading Window');