describe_indicator('RG Kenny 2x VWAP', 'price');

// ============================================================
// INPUTS
// ============================================================

const vwapTab = input.tab('VWAP');
const myShowBlue = vwapTab.boolean('Blue VWAP - 1:00 ET', true);
const myShowYellow = vwapTab.boolean('Yellow MultiDay - Monday 1:00 ET', true);

// ============================================================
// TIME INFO (uses exchange time zone of current ticker, which is
// the closest equivalent to Pine's hour(time, "America/New_York")
// available in this scripting engine)
// ============================================================

const myTimeInfo = time.map(_t => time_of(_t));

// ============================================================
// BLUE VWAP - resets daily at/after 01:00 exchange time
// ============================================================

const myBlueVWAP = series_of(null);

let myBluePV = 0;
let myBlueVol = 0;
let myBlueStarted = false;
let myLastBlueDateKey = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myInfo = myTimeInfo[myIndex];
	const myHlc3 = hlc3[myIndex];
	const myVol = volume[myIndex];

	const myAfterBlueAnchor = (myInfo.hours > 1) || (myInfo.hours === 1 && myInfo.minutes >= 0);
	const myBlueDateKey = (myInfo.year * 10000) + ((myInfo.month + 1) * 100) + myInfo.dayOfMonth;

	const myNewBlueAnchor = myAfterBlueAnchor && (myLastBlueDateKey === null || myBlueDateKey !== myLastBlueDateKey);

	if (myNewBlueAnchor) {
		myBluePV = myHlc3 * myVol;
		myBlueVol = myVol;
		myBlueStarted = true;
		myLastBlueDateKey = myBlueDateKey;
	}
	else if (myBlueStarted) {
		myBluePV += myHlc3 * myVol;
		myBlueVol += myVol;
	}

	myBlueVWAP[myIndex] = (myBlueStarted && myBlueVol > 0) ? (myBluePV / myBlueVol) : null;
}

// ============================================================
// YELLOW MULTIDAY VWAP - resets on Monday at/after 01:00 exchange time
// ============================================================

const myYellowVWAP = series_of(null);

let myYellowPV = 0;
let myYellowVol = 0;
let myYellowStarted = false;
let myLastWeekKey = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myInfo = myTimeInfo[myIndex];
	const myHlc3 = hlc3[myIndex];
	const myVol = volume[myIndex];

	const myAfterYellowAnchor = (myInfo.hours > 1) || (myInfo.hours === 1 && myInfo.minutes >= 0);
	const myWeekKey = (myInfo.year * 100) + myInfo.weekOfYear;

	// Pine's dayofweek.monday equals 2 in its own enum, but time_of() here
	// uses ISO day-of-week where Monday = 1.
	const myIsMonday = myInfo.dayOfWeek === 1;

	const myNewYellowAnchor = myIsMonday && myAfterYellowAnchor && (myLastWeekKey === null || myWeekKey !== myLastWeekKey);

	if (myNewYellowAnchor) {
		myYellowPV = myHlc3 * myVol;
		myYellowVol = myVol;
		myYellowStarted = true;
		myLastWeekKey = myWeekKey;
	}
	else if (myYellowStarted) {
		myYellowPV += myHlc3 * myVol;
		myYellowVol += myVol;
	}

	myYellowVWAP[myIndex] = (myYellowStarted && myYellowVol > 0) ? (myYellowPV / myYellowVol) : null;
}

// ============================================================
// PAINTING
// ============================================================

paint(myShowBlue ? myBlueVWAP : series_of(null), { name: 'Blue VWAP', color: '#2962FF', thickness: 3, style: 'line' });
paint(myShowYellow ? myYellowVWAP : series_of(null), { name: 'Yellow VWAP', color: '#FFC107', thickness: 2, style: 'line' });

// ============================================================
// SCANNER / STRATEGY SIGNALS
// ============================================================

const myCloseAboveBlue = for_every(close, myBlueVWAP, (_c, _v) => (_v !== null) && (_c > _v));
const myCloseBelowBlue = for_every(close, myBlueVWAP, (_c, _v) => (_v !== null) && (_c < _v));
const myCloseAboveYellow = for_every(close, myYellowVWAP, (_c, _v) => (_v !== null) && (_c > _v));
const myCloseBelowYellow = for_every(close, myYellowVWAP, (_c, _v) => (_v !== null) && (_c < _v));

register_signal(myCloseAboveBlue, 'Close Above Blue VWAP');
register_signal(myCloseBelowBlue, 'Close Below Blue VWAP');
register_signal(myCloseAboveYellow, 'Close Above Yellow VWAP');
register_signal(myCloseBelowYellow, 'Close Below Yellow VWAP');