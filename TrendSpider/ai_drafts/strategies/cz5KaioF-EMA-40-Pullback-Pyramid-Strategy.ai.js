describe_indicator('EMA 40 Pullback Pyramid Strategy', 'price');

// ───── Inputs ─────
const myDateTab = input.tab('Date Range');
const myStartDateText = myDateTab.text('Start Date', '2018-01-01');
const myEndDateText = myDateTab.text('End Date', '2069-12-31');

const myMaGroup = input.group('Moving Average');
const myFastLen = myMaGroup.number('Fast EMA length', 40, { min: 1, max: 500 });

const myDmiGroup = input.group('DMI / ADX');
const myDiLen = myDmiGroup.number('DI length', 14, { min: 1, max: 100 });
const myAdxSmooth = myDmiGroup.number('ADX smoothing', 14, { min: 1, max: 100 });
const myAdxThresh = myDmiGroup.number('ADX min. to trade', 20, { min: 0, max: 100 });

const myPullbackGroup = input.group('Pullback Re-entry');
const myUsePullback = myPullbackGroup.boolean('Enable pullback re-entry', true);
const myPullbackAtr = myPullbackGroup.number('Pullback distance x ATR', 1.0, { min: 0, max: 20, step: 0.1 });
const myAtrLen = myPullbackGroup.number('ATR length', 14, { min: 1, max: 100 });

const mySignalGroup = input.group('Signal Control');
const myMinBarsBetweenEntries = mySignalGroup.number('Minimum bars between entries', 5, { min: 0, max: 500 });

const myEmaCrossGroup = input.group('EMA 40 Cross Signals');
const myUseEmaCrossSignals = myEmaCrossGroup.boolean('Use EMA 40 cross buy/sell signals', true);
const myEmaCrossMode = myEmaCrossGroup.select('EMA cross detection mode', 'Close', ['Close', 'Wick']);
const myEmaCrossForOrders = myEmaCrossGroup.boolean('Use EMA cross signals in strategy orders', true);

// ───── Date range (parsed as UTC seconds) ─────
const myStartTimestamp = Date.parse(myStartDateText) / 1000;
const myEndTimestamp = Date.parse(myEndDateText) / 1000;
assert(!isNaN(myStartTimestamp) && !isNaN(myEndTimestamp), 'Invalid date format, use YYYY-MM-DD');

// ───── Core series ─────
const myFast = ema(close, myFastLen);
const myAtrV = atr(high, low, close, myAtrLen);

// NOTE: the Custom JS adx() implementation only exposes one period parameter,
// so diLen and adxSmooth cannot be configured independently like in Pine.
// We use diLen as the single period for both DI and ADX smoothing.
const myAdxObject = indicators.adx(myDiLen);
const myAdxV = myAdxObject.adx;

const myN = close.length;

const myColUp = series_of(false);
const myColDown = series_of(false);
const myBullFlip = series_of(false);
const myBearFlip = series_of(false);
const myTrendIn = series_of(false);
const myBaseEntry = series_of(false);
const myTouchedFast = series_of(false);
const myRecovered = series_of(false);

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myPrevColUp = myIndex > 0 ? myColUp[myIndex - 1] : false;
	const myPrevColDown = myIndex > 0 ? myColDown[myIndex - 1] : false;

	myColUp[myIndex] = myIndex > 0 && myFast[myIndex] > myFast[myIndex - 1];
	myColDown[myIndex] = myIndex > 0 && myFast[myIndex] < myFast[myIndex - 1];

	myBullFlip[myIndex] = myColUp[myIndex] && !myPrevColUp;
	myBearFlip[myIndex] = myColDown[myIndex] && !myPrevColDown;

	myTrendIn[myIndex] = myColUp[myIndex] && myAdxV[myIndex] > myAdxThresh;
	myBaseEntry[myIndex] = myBullFlip[myIndex] && myAdxV[myIndex] > myAdxThresh;

	myTouchedFast[myIndex] = low[myIndex] <= myFast[myIndex] + myAtrV[myIndex] * myPullbackAtr;
	myRecovered[myIndex] = close[myIndex] > myFast[myIndex] && close[myIndex] > open[myIndex];
}

// EMA 40 breakout / breakdown logic
const myEmaBuyClose = series_of(false);
const myEmaSellClose = series_of(false);
const myEmaBuyWick = series_of(false);
const myEmaSellWick = series_of(false);
const myTimeCondition = series_of(false);

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : close[myIndex];
	const myPrevFast = myIndex > 0 ? myFast[myIndex - 1] : myFast[myIndex];

	myEmaBuyClose[myIndex] = close[myIndex] > myFast[myIndex] && myPrevClose <= myPrevFast;
	myEmaSellClose[myIndex] = close[myIndex] < myFast[myIndex] && myPrevClose >= myPrevFast;

	myEmaBuyWick[myIndex] = low[myIndex] <= myFast[myIndex] && close[myIndex] > myFast[myIndex];
	myEmaSellWick[myIndex] = high[myIndex] >= myFast[myIndex] && close[myIndex] < myFast[myIndex];

	myTimeCondition[myIndex] = time[myIndex] >= myStartTimestamp && time[myIndex] <= myEndTimestamp;
}

const myEmaBuySignal = series_of(false);
const myEmaSellSignal = series_of(false);
for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myBuyBase = myEmaCrossMode === 'Close' ? myEmaBuyClose[myIndex] : myEmaBuyWick[myIndex];
	const mySellBase = myEmaCrossMode === 'Close' ? myEmaSellClose[myIndex] : myEmaSellWick[myIndex];
	myEmaBuySignal[myIndex] = myUseEmaCrossSignals && myTimeCondition[myIndex] && myBuyBase;
	myEmaSellSignal[myIndex] = myUseEmaCrossSignals && myTimeCondition[myIndex] && mySellBase;
}

const myExitSignal = myBearFlip;

// ───── Stateful loop: pullback armed state, lastEntryBar, canEnter, orders ─────
const myPullbackCandidate = series_of(false);
const myCanEnter = series_of(false);
const myLongCond = series_of(false);
const myExitCond = series_of(false);

let myLastEntryBar = null;
let myPullbackArmed = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myPrevArmed = myPullbackArmed;

	const myPullbackCand = myUsePullback && myTrendIn[myIndex] &&
		(myPrevArmed || myTouchedFast[myIndex]) &&
		myRecovered[myIndex] && !myBaseEntry[myIndex];

	myPullbackCandidate[myIndex] = myPullbackCand;

	const myExitC = (myExitSignal[myIndex] || (myEmaCrossForOrders && myEmaSellSignal[myIndex])) && myTimeCondition[myIndex];
	myExitCond[myIndex] = myExitC;

	const myCanEnterNow = myLastEntryBar === null || (myIndex - myLastEntryBar) >= myMinBarsBetweenEntries;
	myCanEnter[myIndex] = myCanEnterNow;

	const myLongC = (myBaseEntry[myIndex] || myPullbackCand || (myEmaCrossForOrders && myEmaBuySignal[myIndex])) &&
		myCanEnterNow && myTimeCondition[myIndex];
	myLongCond[myIndex] = myLongC;

	if (myLongC) {
		myLastEntryBar = myIndex;
	}

	if (!myTrendIn[myIndex] || myExitC) {
		myPullbackArmed = false;
	}
	else if (myPullbackCand) {
		myPullbackArmed = false;
	}
	else if (myTouchedFast[myIndex]) {
		myPullbackArmed = true;
	}
	else {
		myPullbackArmed = myPrevArmed;
	}
}

// ───── Plots ─────
const myFastColor = for_every(myColUp, myColDown, (_up, _down) => _up ? 'green' : _down ? 'red' : 'gray');
paint(myFast, { name: 'Fast EMA', color: myFastColor, thickness: 3 });

const myBaseEntryMarks = series_of(null);
const myPullbackMarks = series_of(null);
const myExitMarks = series_of(null);
const myEmaBuyMarks = series_of(null);
const myEmaSellMarks = series_of(null);

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	myBaseEntryMarks[myIndex] = (myBaseEntry[myIndex] && myCanEnter[myIndex] && myTimeCondition[myIndex]) ? constants.icons.triangle_up : null;
	myPullbackMarks[myIndex] = (myPullbackCandidate[myIndex] && myCanEnter[myIndex] && myTimeCondition[myIndex]) ? constants.icons.triangle_up : null;
	myExitMarks[myIndex] = (myExitSignal[myIndex] && myTimeCondition[myIndex]) ? constants.icons.triangle_down : null;
	myEmaBuyMarks[myIndex] = myEmaBuySignal[myIndex] ? constants.icons.triangle_up : null;
	myEmaSellMarks[myIndex] = myEmaSellSignal[myIndex] ? constants.icons.triangle_down : null;
}

paint(myBaseEntryMarks, { name: 'BaseEntry', style: 'labels_below', color: 'green' });
paint(myPullbackMarks, { name: 'PullbackEntry', style: 'labels_below', color: 'aqua' });
paint(myExitMarks, { name: 'OriginalExit', style: 'labels_above', color: 'red' });
paint(myEmaBuyMarks, { name: 'EmaBuySignal', style: 'labels_below', color: 'blue' });
paint(myEmaSellMarks, { name: 'EmaSellSignal', style: 'labels_above', color: 'orange' });

// ───── Signals for scanners / alerts / strategies ─────
register_signal(myBaseEntry.map((_v, _i) => _v && myCanEnter[_i] && myTimeCondition[_i]), 'Base Entry');
register_signal(myPullbackCandidate.map((_v, _i) => _v && myCanEnter[_i] && myTimeCondition[_i]), 'Pullback Entry');
register_signal(myExitSignal.map((_v, _i) => _v && myTimeCondition[_i]), 'Original Exit');
register_signal(myEmaBuySignal, 'Ema Buy Signal');
register_signal(myEmaSellSignal, 'Ema Sell Signal');
register_signal(myLongCond, 'Long Entry Order');
register_signal(myExitCond, 'Exit All Order');