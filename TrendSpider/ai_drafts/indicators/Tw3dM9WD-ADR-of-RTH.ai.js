describe_indicator('RTH ADR', 'price');
// This indicator reproduces the Pine Script "RTH ADR" logic.
// Session detection uses moment-timezone to convert each candle's
// timestamp into Pacific Time, since TrendSpider's built-in session
// helpers work off the exchange timezone, not an arbitrary one.
const myMoment = library('moment-timezone');
const myLookbackDays = input.number('Lookback Days', 14, { min: 1, max: 500 });
const mySessionStart = input.text('RTH Start HHMM', '0630');
const mySessionEnd = input.text('RTH End HHMM', '1310');

function myParseHHMM(_text) {
	const myHours = parseInt(_text.slice(0, 2), 10);
	const myMinutes = parseInt(_text.slice(2, 4), 10);
	return myHours * 60 + myMinutes;
}

const myStartMinutes = myParseHHMM(mySessionStart);
const myEndMinutes = myParseHHMM(mySessionEnd);
const myN = time.length;

// Determine, for every candle, whether it falls inside the Pacific
// Time RTH session window.
// Note: avoided "new Array(...)" (prohibited by the engine), using
// Array(...).fill(...) instead, which does not use the "new" keyword.
const myInSession = Array(myN).fill(false);
for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myPacificTime = myMoment.tz(time[myIndex] * 1000, 'America/Los_Angeles');
	const myMinutesOfDay = myPacificTime.hours() * 60 + myPacificTime.minutes();
	myInSession[myIndex] = myMinutesOfDay >= myStartMinutes && myMinutesOfDay < myEndMinutes;
}

// Track session high/low, completed daily ranges, running average
// of the lookback window, current (live) range and percentage.
const mySessionHighSeries = series_of(null);
const mySessionLowSeries = series_of(null);
const myCurrentRangeSeries = series_of(null);
const myAvgRangeSeries = series_of(null);
const myPctSeries = series_of(null);
const myInSessionSeries = series_of(false);

const myMaxKeep = Math.max(myLookbackDays + 20, 60);
let myRangeArr = [];
let mySessionHigh = null;
let mySessionLow = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myInSessionNow = myInSession[myIndex];
	const myInSessionPrev = myIndex > 0 ? myInSession[myIndex - 1] : false;
	const myNewSession = myInSessionNow && !myInSessionPrev;
	const mySessionEndedNow = !myInSessionNow && myInSessionPrev;

	if (myNewSession) {
		mySessionHigh = high[myIndex];
		mySessionLow = low[myIndex];
	}
	else if (myInSessionNow) {
		mySessionHigh = Math.max(mySessionHigh, high[myIndex]);
		mySessionLow = Math.min(mySessionLow, low[myIndex]);
	}

	if (mySessionEndedNow) {
		const myDayRange = (mySessionHigh != null && mySessionLow != null) ? (mySessionHigh - mySessionLow) : null;
		if (myDayRange != null) {
			myRangeArr.push(myDayRange);
			if (myRangeArr.length > myMaxKeep) {
				myRangeArr.shift();
			}
		}
	}

	const myLookbackCount = Math.min(myLookbackDays, myRangeArr.length);
	let myAvgRange = null;
	if (myLookbackCount > 0) {
		let myTotal = 0;
		for (let myOffset = 0; myOffset < myLookbackCount; myOffset += 1) {
			myTotal += myRangeArr[myRangeArr.length - 1 - myOffset];
		}
		myAvgRange = myTotal / myLookbackCount;
	}

	const myCurrentRange = (mySessionHigh != null && mySessionLow != null) ? (mySessionHigh - mySessionLow) : null;
	const myPct = (myAvgRange != null && myAvgRange !== 0 && myCurrentRange != null) ? (myCurrentRange / myAvgRange) * 100 : null;

	mySessionHighSeries[myIndex] = mySessionHigh;
	mySessionLowSeries[myIndex] = mySessionLow;
	myCurrentRangeSeries[myIndex] = myCurrentRange;
	myAvgRangeSeries[myIndex] = myAvgRange;
	myPctSeries[myIndex] = myPct;
	myInSessionSeries[myIndex] = myInSessionNow;
}

const myLastAvgRange = myAvgRangeSeries[myN - 1];
const myLastCurrentRange = myCurrentRangeSeries[myN - 1];
const myLastPct = myPctSeries[myN - 1];

// Table mirroring the Pine Script's top-right info table.
paint_overlay('RthAdrTable', { position: 'top_right' }, {
	rows: [{
		cells: [
			{ text: 'RTH ADR (' + myLookbackDays + 'd)', color: 'black' },
			{ text: myLastAvgRange == null ? 'n/a' : myLastAvgRange.toFixed(2), color: 'black' }
		]
	}, {
		cells: [
			{ text: 'Todays Range', color: 'black' },
			{ text: myLastCurrentRange == null ? 'n/a' : myLastCurrentRange.toFixed(2), color: 'black' }
		]
	}, {
		cells: [
			{ text: 'Today Percent Of Avg', color: 'black' },
			{ text: myLastPct == null ? 'n/a' : myLastPct.toFixed(2) + '%', color: 'black' }
		]
	}]
});

// Session high/low lines on the price axis for visual reference.
paint(mySessionHighSeries, { name: 'SessionHigh', color: '#26A69A', style: 'ladder' });
paint(mySessionLowSeries, { name: 'SessionLow', color: '#EF5350', style: 'ladder' });

// Signals for scanners/alerts/strategies.
register_signal(myInSessionSeries, 'In RTH Session');
register_signal(for_every(myPctSeries, _p => _p != null && _p > 100), 'Range Above Average');
register_signal(for_every(myPctSeries, _p => _p != null && _p < 50), 'Range Below Half Average');
register_signal(myPctSeries, 'Percent Of Average Range');
register_signal(myCurrentRangeSeries, 'Current Session Range');
register_signal(myAvgRangeSeries, 'Average RTH Range');