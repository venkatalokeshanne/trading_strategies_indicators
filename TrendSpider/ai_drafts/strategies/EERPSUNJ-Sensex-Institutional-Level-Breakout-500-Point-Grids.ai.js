describe_indicator('Sensex 945 Break Even 200pts', 'price');

// --- Inputs ---
const myIncrement = input.number('Round Number Increment', 500, { min: 100 });
const mySlPoints = input.number('Initial Stop Loss Points', 100, { min: 1 });
const myBeTrigger = input.number('Move to BE Trigger Points', 200, { min: 1 });
const myStartHour = input.number('Start Hour', 9, { min: 0, max: 23 });
const myStartMin = input.number('Start Minute', 45, { min: 0, max: 59 });

const myLength = close.length;

// output series
const myUpperLevelArr = series_of(null);
const myLowerLevelArr = series_of(null);
const myTpUpperArr = series_of(null);
const myTpLowerArr = series_of(null);
const mySlArr = series_of(null);
const myLongSignalArr = series_of(false);
const myShortSignalArr = series_of(false);
const myExitSignalArr = series_of(false);

// persistent state across the loop (mirrors Pine "var" semantics)
let myUpperLevel = null;
let myLowerLevel = null;
let myTpUpper = null;
let myTpLower = null;
let myActiveSl = null;
let myTrailActivated = false;
let myPositionSize = 0;
let myPositionAvgPrice = null;

// session window boundaries in minutes-of-day
const mySessionStartMinutes = 9 * 60 + 45;
const mySessionEndMinutes = 15 * 60 + 15;
const myEodCloseStartMinutes = 15 * 60 + 25;
const myEodCloseEndMinutes = 15 * 60 + 30;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myTotalMinutes = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	const myIsStartTime = myTimeInfo.hours === myStartHour && myTimeInfo.minutes === myStartMin;
	const myCanTrade = myTotalMinutes >= mySessionStartMinutes && myTotalMinutes <= mySessionEndMinutes;
	const myIsEodWindow = myTotalMinutes >= myEodCloseStartMinutes && myTotalMinutes <= myEodCloseEndMinutes;

	// --- Level calculation at session start ---
	if (myIsStartTime) {
		const myCurrentPrice = open[myIndex];
		myLowerLevel = Math.floor(myCurrentPrice / myIncrement) * myIncrement;
		myUpperLevel = Math.ceil(myCurrentPrice / myIncrement) * myIncrement;
		myTpUpper = myUpperLevel + myIncrement;
		myTpLower = myLowerLevel - myIncrement;
		myTrailActivated = false;
	}

	let myLongSignal = false;
	let myShortSignal = false;
	let myExitSignal = false;

	// --- Entry conditions (crossunder) ---
	let myLongCondition = false;
	let myShortCondition = false;

	if (myIndex > 0 && myUpperLevel !== null && myLowerLevel !== null) {
		const myPrevClose = close[myIndex - 1];
		const myCurrClose = close[myIndex];

		myLongCondition = myCurrClose < myUpperLevel && myPrevClose >= myUpperLevel && myCanTrade && myPositionSize === 0;
		myShortCondition = myCurrClose < myLowerLevel && myPrevClose >= myLowerLevel && myCanTrade && myPositionSize === 0;
	}

	if (myLongCondition) {
		myPositionSize = 1;
		myPositionAvgPrice = close[myIndex];
		myActiveSl = close[myIndex] - mySlPoints;
		myTrailActivated = false;
		myLongSignal = true;
	}
	else if (myShortCondition) {
		myPositionSize = -1;
		myPositionAvgPrice = close[myIndex];
		myActiveSl = close[myIndex] + mySlPoints;
		myTrailActivated = false;
		myShortSignal = true;
	}

	// --- Break-even logic ---
	if (myPositionSize > 0 && !myTrailActivated && high[myIndex] >= myPositionAvgPrice + myBeTrigger) {
		myActiveSl = myPositionAvgPrice;
		myTrailActivated = true;
	}
	if (myPositionSize < 0 && !myTrailActivated && low[myIndex] <= myPositionAvgPrice - myBeTrigger) {
		myActiveSl = myPositionAvgPrice;
		myTrailActivated = true;
	}

	// --- Exit via SL/TP intrabar touch ---
	if (myPositionSize !== 0) {
		const myTargetPrice = myPositionSize > 0 ? myTpUpper : myTpLower;
		let myHitSl = false;
		let myHitTp = false;

		if (myPositionSize > 0) {
			myHitSl = low[myIndex] <= myActiveSl;
			myHitTp = high[myIndex] >= myTargetPrice;
		}
		else {
			myHitSl = high[myIndex] >= myActiveSl;
			myHitTp = low[myIndex] <= myTargetPrice;
		}

		if (myHitSl || myHitTp) {
			myExitSignal = true;
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myActiveSl = null;
			myTrailActivated = false;
		}
	}

	// --- EOD square-off ---
	if (myIsEodWindow && myPositionSize !== 0) {
		myExitSignal = true;
		myPositionSize = 0;
		myPositionAvgPrice = null;
		myActiveSl = null;
		myTrailActivated = false;
	}

	myUpperLevelArr[myIndex] = myUpperLevel;
	myLowerLevelArr[myIndex] = myLowerLevel;
	myTpUpperArr[myIndex] = myTpUpper;
	myTpLowerArr[myIndex] = myTpLower;
	mySlArr[myIndex] = myPositionSize !== 0 ? myActiveSl : null;
	myLongSignalArr[myIndex] = myLongSignal;
	myShortSignalArr[myIndex] = myShortSignal;
	myExitSignalArr[myIndex] = myExitSignal;
}

// --- Plotting ---
paint(myUpperLevelArr, { name: 'EntryHigh', color: '#26A69A', style: 'ladder', thickness: 2 });
paint(myLowerLevelArr, { name: 'EntryLow', color: '#EF5350', style: 'ladder', thickness: 2 });
paint(myTpUpperArr, { name: 'TargetHigh', color: '#4DA3FF', style: 'ladder', thickness: 1 });
paint(myTpLowerArr, { name: 'TargetLow', color: '#FFA726', style: 'ladder', thickness: 1 });
paint(mySlArr, { name: 'StopLoss', color: '#FF5252', style: 'dotted', thickness: 3 });

// --- Scanner / Alert / Strategy signals ---
register_signal(myLongSignalArr, 'Long Entry');
register_signal(myShortSignalArr, 'Short Entry');
register_signal(myExitSignalArr, 'Exit Position');