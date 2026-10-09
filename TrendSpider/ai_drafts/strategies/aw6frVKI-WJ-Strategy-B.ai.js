describe_indicator('WJ Strategy B', 'lower');

// NOTE: this script converts a Pine Script v6 strategy into a TrendSpider
// indicator. TrendSpider custom scripts can not execute real orders or
// backtests; instead we expose the exact same "Buy" signal condition via
// register_signal(), so it can be used in Scanners, Alerts and the
// Strategy Tester module. We also paint the WJ Score and the entry MA.
const myTabScore = input.tab('Score Settings');
const myBbGroup = myTabScore.group('Bollinger Bands');
const myBbLen = myBbGroup.number('BB Length', 40, { min: 1, max: 500 });
const myBbMult = myBbGroup.number('BB Mult', 2.0, { min: 0.1, max: 10 });

const myMaGroup = myTabScore.group('Moving Averages');
const myMaRow1 = myMaGroup.row();
const myMaLen1 = myMaRow1.number('MA 1 (0.5 pt)', 120, { min: 1, max: 1000 });
const myMaLen2 = myMaRow1.number('MA 2 (1.0 pt)', 240, { min: 1, max: 1000 });
const myMaLen3 = myMaRow1.number('MA 3 (1.5 pt)', 400, { min: 1, max: 1000 });

const myRsiGroup = myTabScore.group('RSI');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 1, max: 200 });

const myTabEntry = input.tab('Entry Settings');
const myEntryGroup = myTabEntry.group('Confirmation');
const myEntryRow = myEntryGroup.row();
const myConfirmDays = myEntryRow.number('Score Decline Days', 2, { min: 1, max: 50 });
const myEntryMaLen = myEntryRow.number('Entry MA Length', 10, { min: 1, max: 200 });

const myTabDate = input.tab('Date Range');
const myDateGroup = myTabDate.group('Start Date');
const myDateRow = myDateGroup.row();
const myStartYear = myDateRow.number('Start Year', 2024, { min: 1990, max: 2100 });
const myStartMonth = myDateRow.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = myDateRow.number('Start Day', 1, { min: 1, max: 31 });

// start_time, in seconds (Pine's `timestamp()` is also seconds since epoch
// for scripts, but internally msec; we normalize to seconds like `time`)
const myStartTimestamp = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0, 0) / 1000;

// --- indicator math (computed once, outside loops) ---
const myMa1 = sma(close, myMaLen1);
const myMa2 = sma(close, myMaLen2);
const myMa3 = sma(close, myMaLen3);
const myRsi = rsi(close, myRsiLen);
const myEntryMa = sma(close, myEntryMaLen);
const myBbBasis = sma(close, myBbLen);
const myBbStdev = stdev(close, myBbLen);
const myBbLower = sub(myBbBasis, mult(myBbStdev, myBbMult));

const myLength = close.length;

// score arrays. Using series_of() instead of "new Array().fill()" because
// the "new" keyword is not allowed by the scripting engine.
const myScoreBb = series_of(0);
const myScoreMa = series_of(0);
const myScoreRsi = series_of(0);
const myFinalScore = series_of(0);

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	myScoreBb[myIndex] = close[myIndex] < myBbLower[myIndex] ? 1.0 : 0.0;

	if (close[myIndex] < myMa3[myIndex]) {
		myScoreMa[myIndex] = 1.5;
	}
	else if (close[myIndex] < myMa2[myIndex]) {
		myScoreMa[myIndex] = 1.0;
	}
	else if (close[myIndex] < myMa1[myIndex]) {
		myScoreMa[myIndex] = 0.5;
	}
	else {
		myScoreMa[myIndex] = 0.0;
	}

	const myRsiValue = myRsi[myIndex];
	if (myRsiValue <= 25) {
		myScoreRsi[myIndex] = 2.0;
	}
	else if (myRsiValue <= 30) {
		myScoreRsi[myIndex] = 1.5;
	}
	else if (myRsiValue <= 35) {
		myScoreRsi[myIndex] = 1.0;
	}
	else if (myRsiValue <= 40) {
		myScoreRsi[myIndex] = 0.5;
	}
	else {
		myScoreRsi[myIndex] = 0.0;
	}

	myFinalScore[myIndex] = myScoreBb[myIndex] + myScoreMa[myIndex] + myScoreRsi[myIndex];
}

// --- sequential state machine (must be a plain loop, mirrors Pine's
// per-bar var state: monitoring / days_maintained) ---
const myBuySignal = series_of(false);
let myMonitoring = false;
let myDaysMaintained = 0;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myInDateRange = time[myIndex] >= myStartTimestamp;
	if (!myInDateRange) {
		continue;
	}

	// A. trigger monitoring
	if (myFinalScore[myIndex] >= 3.0) {
		myMonitoring = true;
		myDaysMaintained = 0;
	}

	// B. act while monitoring and below 3.0
	if (myMonitoring && myFinalScore[myIndex] < 3.0) {
		const myPrevScore = myIndex > 0 ? myFinalScore[myIndex - 1] : myFinalScore[myIndex];

		if (myFinalScore[myIndex] > myPrevScore) {
			myDaysMaintained = 0;
		}
		else {
			myDaysMaintained += 1;
			const myCondDays = myDaysMaintained >= myConfirmDays;
			const myCondMa = close[myIndex] >= myEntryMa[myIndex];

			if (myCondDays && myCondMa) {
				myBuySignal[myIndex] = true;
				myMonitoring = false;
			}
		}
	}
}

// --- painting ---
const myBuyMarkers = myBuySignal.map(_flag => _flag ? 1 : null);

paint(myFinalScore, { name: 'WJ Score', color: '#4DA3FF', thickness: 2 });
paint(horizontal_line(3.0), { name: 'Trigger Level', color: 'gray', style: 'dotted' });
paint(myEntryMa, { name: 'Entry MA', color: '#EF5350', thickness: 1, forceUsePriceAxis: true });
paint(myBuyMarkers, { name: 'WJ Buy', style: 'labels_below', color: '#26A69A', thickness: 3 });

// expose the exact Pine entry condition so it can drive Scanners,
// Alerts and the Strategy Tester
register_signal(myBuySignal, 'WJ Buy Signal');