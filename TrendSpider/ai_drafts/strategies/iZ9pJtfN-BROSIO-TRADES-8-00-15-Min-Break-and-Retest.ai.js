describe_indicator('MNQ Midpoint Retest (7x2R and 3xRunner)', 'price');

// NOTE: This indicator reproduces the SIGNAL logic of the original Pine
// strategy (range building, breakout detection, mid-point retest entries).
// Full strategy money-management (partial exits, breakeven stop, position
// sizing, pyramiding, pending orders) cannot be simulated in a plain
// indicator context - TrendSpider Custom JS indicators do not manage
// positions or orders. We only reproduce entry trigger bars and plot the
// range levels, exactly matching the Pine entry logic bar-for-bar.
assert(!isNaN(current.resolution), 'Only applicable to intraday charts');

// Session times are evaluated using the exchange's local calendar time
// (time_of uses the exchange time zone). The original script hardcodes
// "America/New_York" - we assume the chart's exchange time zone IS New
// York (true for CME futures like MNQ). If run on a different exchange
// time zone this will not match exactly.
const myRangeStartMin = 8 * 60 + 0;
const myRangeEndMin = 8 * 60 + 15;
const myTradeStartMin = 9 * 60 + 45;
const myTradeEndMin = 11 * 60 + 0;

const myN = close.length;

const myDayId = time.map(_t => bar_at(_t).session);

const myMinuteOfDay = time.map(_t => {
	const myParts = time_of(_t);
	return myParts.hours * 60 + myParts.minutes;
});

const myRangeSession = myMinuteOfDay.map(_m => _m >= myRangeStartMin && _m < myRangeEndMin);
const myTradeSession = myMinuteOfDay.map(_m => _m >= myTradeStartMin && _m < myTradeEndMin);

const myRangeHighArr = series_of(null);
const myRangeLowArr = series_of(null);
const myMidArr = series_of(null);
const myAboveRangeArr = series_of(false);
const myBelowRangeArr = series_of(false);
const myTouchLongArr = series_of(false);
const myTouchShortArr = series_of(false);

let myRHigh = null;
let myRLow = null;
let myMid = null;
let myRangeLocked = false;
let myEntry = null;
let myLockedForDay = false;
let myBreakoutState = 0;

// Approximation: Pine's "strategy.opentrades == 0" can't be known without
// real position tracking. We approximate "one trade only" as "no entry has
// fired yet today", resetting once per new trading day.
let myHasEnteredToday = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myNewDay = myIndex === 0 || myDayId[myIndex] !== myDayId[myIndex - 1];

	if (myNewDay) {
		myRHigh = null;
		myRLow = null;
		myMid = null;
		myRangeLocked = false;
		myEntry = null;
		myLockedForDay = false;
		myHasEnteredToday = false;
	}

	// range build
	if (myRangeSession[myIndex] && !myRangeLocked) {
		myRHigh = (myRHigh === null) ? high[myIndex] : Math.max(myRHigh, high[myIndex]);
		myRLow = (myRLow === null) ? low[myIndex] : Math.min(myRLow, low[myIndex]);
	}

	if (!myRangeSession[myIndex] && !myRangeLocked && myRHigh !== null && myRLow !== null) {
		myMid = (myRHigh + myRLow) / 2;
		myRangeLocked = true;
	}

	// breakout (sticky across the whole dataset, exactly like Pine's var int)
	const myAboveRange = myRangeLocked && close[myIndex] > myRHigh;
	const myBelowRange = myRangeLocked && close[myIndex] < myRLow;

	if (myAboveRange) {
		myBreakoutState = 1;
	}
	if (myBelowRange) {
		myBreakoutState = -1;
	}

	const myCanTrade = myRangeLocked && !myLockedForDay && myTradeSession[myIndex];

	const myTouchLong = myCanTrade && myBreakoutState === 1 && low[myIndex] <= myMid;
	const myTouchShort = myCanTrade && myBreakoutState === -1 && high[myIndex] >= myMid;

	const myOneTradeOnly = !myHasEnteredToday;

	const myEnterLong = myTouchLong && myOneTradeOnly;
	const myEnterShort = myTouchShort && myOneTradeOnly;

	if (myEnterLong || myEnterShort) {
		myHasEnteredToday = true;
		myEntry = close[myIndex];
	}

	myRangeHighArr[myIndex] = myRangeLocked ? myRHigh : null;
	myRangeLowArr[myIndex] = myRangeLocked ? myRLow : null;
	myMidArr[myIndex] = myRangeLocked ? myMid : null;
	myAboveRangeArr[myIndex] = myAboveRange;
	myBelowRangeArr[myIndex] = myBelowRange;
	myTouchLongArr[myIndex] = myEnterLong;
	myTouchShortArr[myIndex] = myEnterShort;
}

paint(myRangeHighArr, { name: 'RangeHigh', color: '#2ecc71', style: 'line' });
paint(myRangeLowArr, { name: 'RangeLow', color: '#e74c3c', style: 'line' });
paint(myMidArr, { name: 'Mid', color: '#3498db', style: 'line' });

const myAboveShapeArr = myAboveRangeArr.map(_v => _v ? constants.icons.triangle_up : null);
const myBelowShapeArr = myBelowRangeArr.map(_v => _v ? constants.icons.triangle_down : null);

paint(myAboveShapeArr, { name: 'AboveRange', style: 'labels_below', color: '#2ecc71' });
paint(myBelowShapeArr, { name: 'BelowRange', style: 'labels_above', color: '#e74c3c' });

register_signal(myTouchLongArr, 'Long Entry');
register_signal(myTouchShortArr, 'Short Entry');