describe_indicator('Donchian Basis Cross with Band TP', 'price');

const myMoment = library('moment-timezone');

// --- Donchian Settings ---
const myDonchianLength = input.number('Donchian Channel Length', 40, { min: 1, max: 500 });

// --- Session Filter Settings ---
const mySessionTab = input.tab('Session Filter');
const myUseSession = mySessionTab.boolean('Use Session Filter', true);
const mySessionRow = mySessionTab.row();
const mySessionStart = mySessionRow.text('Session Start (HHMM)', '0930');
const mySessionEnd = mySessionRow.text('Session End (HHMM)', '1600');
const mySessionTz = mySessionTab.select('Timezone', 'UTC', ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo']);

// --- ATR Settings ---
const myAtrTab = input.tab('ATR Settings');
const myAtrLength = myAtrTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMultiplier = myAtrTab.number('ATR Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });

// --- Time Filter ---
// Shortened input names to satisfy the platform's length limit on
// input() names (the previous names were too long and threw an error).
const myTimeTab = input.tab('Time Filter');
const myStartTimeText = myTimeTab.text('Start Time (UTC)', '2026-01-01 00:00');
const myEndTimeText = myTimeTab.text('End Time (UTC)', '2026-04-03 23:59');

const myStartTimestamp = myMoment.utc(myStartTimeText, 'YYYY-MM-DD HH:mm').unix();
const myEndTimestamp = myMoment.utc(myEndTimeText, 'YYYY-MM-DD HH:mm').unix();

// --- Donchian Channel ---
const myUpperBand = highest(high, myDonchianLength);
const myLowerBand = lowest(low, myDonchianLength);
const myBasis = div(add(myUpperBand, myLowerBand), 2);

// --- ATR ---
const myAtrValue = atr(high, low, close, myAtrLength);

// --- Session check (approximated: uses hour/minute in selected timezone) ---
const myIsInSession = time.map(_t => {
	if (!myUseSession) {
		return true;
	}
	const myTzMoment = myMoment.tz(_t * 1000, mySessionTz);
	const myHHMM = myTzMoment.hours() * 100 + myTzMoment.minutes();
	const myStartHHMM = parseInt(mySessionStart, 10);
	const myEndHHMM = parseInt(mySessionEnd, 10);
	if (myStartHHMM <= myEndHHMM) {
		return myHHMM >= myStartHHMM && myHHMM <= myEndHHMM;
	}
	// session wraps over midnight
	return myHHMM >= myStartHHMM || myHHMM <= myEndHHMM;
});

// --- Time window filter ---
const myIsInWindow = time.map(_t => _t >= myStartTimestamp && _t <= myEndTimestamp);

// --- Crossover / Crossunder conditions ---
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myCrossOver = close[myIndex] > myBasis[myIndex] && close[myIndex - 1] <= myBasis[myIndex - 1];
	const myCrossUnder = close[myIndex] < myBasis[myIndex] && close[myIndex - 1] >= myBasis[myIndex - 1];

	myLongCondition[myIndex] = myCrossOver && myIsInWindow[myIndex] && myIsInSession[myIndex];
	myShortCondition[myIndex] = myCrossUnder && myIsInWindow[myIndex] && myIsInSession[myIndex];
}

// --- Simple state machine simulating strategy.entry/strategy.exit logic ---
// 0 = flat, 1 = long, -1 = short
const mySlSeries = series_of(null);
const myTpSeries = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);

let myPositionState = 0;
let mySlPrice = null;
let myTpPrice = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	// Check exits first, based on current bar's high/low (approximation of
	// intrabar stop/limit fills, since we don't have tick-level simulation)
	if (myPositionState === 1) {
		if (low[myIndex] <= mySlPrice || high[myIndex] >= myTpPrice) {
			myPositionState = 0;
			mySlPrice = null;
			myTpPrice = null;
		}
	}
	else if (myPositionState === -1) {
		if (high[myIndex] >= mySlPrice || low[myIndex] <= myTpPrice) {
			myPositionState = 0;
			mySlPrice = null;
			myTpPrice = null;
		}
	}

	if (myLongCondition[myIndex] && myPositionState === 0) {
		const myRisk = myAtrValue[myIndex] * myAtrMultiplier;
		mySlPrice = close[myIndex] - myRisk;
		myTpPrice = myUpperBand[myIndex];
		myPositionState = 1;
		myLongEntrySignal[myIndex] = true;
	}
	else if (myShortCondition[myIndex] && myPositionState === 0) {
		const myRisk = myAtrValue[myIndex] * myAtrMultiplier;
		mySlPrice = close[myIndex] + myRisk;
		myTpPrice = myLowerBand[myIndex];
		myPositionState = -1;
		myShortEntrySignal[myIndex] = true;
	}

	if (myPositionState === 0) {
		mySlSeries[myIndex] = null;
		myTpSeries[myIndex] = null;
	}
	else {
		mySlSeries[myIndex] = mySlPrice;
		myTpSeries[myIndex] = myTpPrice;
	}
}

// --- Painting ---
paint(myUpperBand, { name: 'Upper Band', color: '#089981', thickness: 1, style: 'line' });
paint(myLowerBand, { name: 'Lower Band', color: '#f23645', thickness: 1, style: 'line' });
paint(myBasis, { name: 'Basis', color: '#5b9cf6', thickness: 2, style: 'line' });
paint(mySlSeries, { name: 'Stop Loss', color: 'red', thickness: 1, style: 'ladder' });
paint(myTpSeries, { name: 'Take Profit', color: 'green', thickness: 1, style: 'ladder' });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');