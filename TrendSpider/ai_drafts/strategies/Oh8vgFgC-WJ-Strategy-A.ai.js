describe_indicator('WJ Strategy A Score and Signal', 'lower');

// ==========================================
// Inputs
// ==========================================
const myBBTab = input.tab('Bollinger / MA / RSI');
const myBBGroup = myBBTab.group('Bollinger Bands');
const myBBLen = myBBGroup.number('BB Length', 40, { min: 1, max: 500 });
const myBBMult = myBBGroup.number('BB Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const myMAGroup = myBBTab.group('Moving Averages');
const myMARow1 = myMAGroup.row();
const myMALen1 = myMARow1.number('MA 1 (0.5pt)', 120, { min: 1, max: 1000 });
const myMALen2 = myMARow1.number('MA 2 (1.0pt)', 240, { min: 1, max: 1000 });
const myMALen3 = myMARow1.number('MA 3 (1.5pt)', 400, { min: 1, max: 1000 });

const myRSIGroup = myBBTab.group('RSI');
const myRSILen = myRSIGroup.number('RSI Length', 14, { min: 1, max: 200 });

const myEntryTab = input.tab('Entry Logic');
const myConfirmDays = myEntryTab.number('Score Downtrend Confirm Days', 2, { min: 1, max: 50 });
const myEntryMALen = myEntryTab.number('Entry MA Length', 10, { min: 1, max: 500 });

const myDateGroup = myEntryTab.group('Start Date Filter');
const myDateRow = myDateGroup.row();
const myStartYear = myDateRow.number('Start Year', 2024, { min: 1990, max: 2100 });
const myStartMonth = myDateRow.number('Start Month', 1, { min: 1, max: 12 });
const myStartDay = myDateRow.number('Start Day', 1, { min: 1, max: 31 });

// Start timestamp (UTC based, in seconds), approximating Pine's exchange-time timestamp()
const myStartTimestamp = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0, 0) / 1000;

// ==========================================
// Score computation (vectorized)
// ==========================================
const myBBBasis = sma(close, myBBLen);
const myBBDev = mult(stdev(close, myBBLen), myBBMult);
const myBBLower = sub(myBBBasis, myBBDev);

const myMA1 = sma(close, myMALen1);
const myMA2 = sma(close, myMALen2);
const myMA3 = sma(close, myMALen3);

const myRSI = rsi(close, myRSILen);
const myEntryMA = sma(close, myEntryMALen);

const myScoreBB = for_every(close, myBBLower, (_c, _bbl) => _c < _bbl ? 1.0 : 0.0);

const myScoreMA = for_every(close, myMA1, myMA2, myMA3, (_c, _m1, _m2, _m3) => {
	if (_c < _m3) return 1.5;
	if (_c < _m2) return 1.0;
	if (_c < _m1) return 0.5;
	return 0.0;
});

const myScoreRSI = for_every(myRSI, _r => {
	if (_r <= 25) return 2.0;
	if (_r <= 30) return 1.5;
	if (_r <= 35) return 1.0;
	if (_r <= 40) return 0.5;
	return 0.0;
});

const myFinalScore = add(myScoreBB, add(myScoreMA, myScoreRSI));

// ==========================================
// Strategy state machine (sequential logic, loop is over logic only,
// not indicator functions - allowed per engine rules)
// ==========================================
const myBuySignal = series_of(false);
const myFinalScoreOut = series_of(null);
let myMonitoring = false;
let myDaysMaintained = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myFinalScoreOut[myIndex] = myFinalScore[myIndex];
	const myInDateRange = time[myIndex] >= myStartTimestamp;
	let myBuyHere = false;

	if (myInDateRange) {
		// A. Trigger monitoring
		if (myFinalScore[myIndex] >= 2.0) {
			myMonitoring = true;
			myDaysMaintained = 0;
		}

		// B. Monitoring state
		if (myMonitoring && myFinalScore[myIndex] < 2.0) {
			const myPrevScore = myIndex > 0 ? myFinalScore[myIndex - 1] : null;

			if (myPrevScore !== null && myFinalScore[myIndex] > myPrevScore) {
				myDaysMaintained = 0;
			}
			else if (myPrevScore !== null) {
				myDaysMaintained += 1;
				const myCondDays = myDaysMaintained >= myConfirmDays;
				const myCondMA = close[myIndex] >= myEntryMA[myIndex];

				if (myCondDays && myCondMA) {
					myBuyHere = true;
					myMonitoring = false;
				}
			}
		}
	}

	myBuySignal[myIndex] = myBuyHere;
}

// ==========================================
// Painting
// ==========================================
// NOTE: a paint() line and a register_signal() must not share the same
// name, otherwise the engine throws a duplicate name error. The painted
// marker line is now named differently from the registered signal.
paint(myFinalScoreOut, { name: 'WJ Final Score', color: '#4DA3FF', thickness: 2 });
paint(horizontal_line(2.0), { name: 'Trigger Level', color: 'gray', style: 'dotted' });

const myBuyMarks = for_every(myBuySignal, _b => _b ? true : null);
paint(myBuyMarks, { name: 'WJ Buy Marker', style: 'labels_below', color: '#26A69A', thickness: 3 });

// Signal for scanners, alerts and backtests
register_signal(myBuySignal, 'WJ Buy Signal');