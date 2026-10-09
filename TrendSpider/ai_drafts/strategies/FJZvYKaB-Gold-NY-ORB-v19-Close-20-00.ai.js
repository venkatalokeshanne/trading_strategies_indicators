describe_indicator('Gold NY ORB v19 Ahmed', 'price');

// This indicator reproduces the Pine Script's OR (Opening Range) logic,
// using UTC hour/minute derived directly from each candle's Unix timestamp.
// Strategy order management (position sizing, stop/limit exits) is not
// expressible in a Custom JS indicator, so this script only reproduces
// the long entry signal, the OR High/Low lines, and a session-end signal.

const myStartTimestamp = 1704067200; // 2024-01-01 00:00 UTC

const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 100 });
const myVolAvgLength = input.number('Volume Avg Length', 20, { min: 1, max: 200 });
const myAtrAvgLength = input.number('ATR Avg Length', 20, { min: 1, max: 200 });
const myRegimeMult = input.number('Regime ATR Mult', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myOrRangeMult = input.number('OR Range ATR Mult', 2.5, { min: 0.1, max: 10, step: 0.1 });
const myVolMult = input.number('Volume Spike Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myRRMult = input.number('Reward To Risk Mult', 2.5, { min: 0.1, max: 10, step: 0.1 });

const myAtr = atr(high, low, close, myAtrLength);
const myVolAvg = sma(volume, myVolAvgLength);
const myAtrAvg = sma(myAtr, myAtrAvgLength);

const myOrHighOut = series_of(null);
const myOrLowOut = series_of(null);
const myLongBreakOut = series_of(false);
const mySessionEndOut = series_of(false);

let myOrHigh = null;
let myOrLow = null;
let myOrReady = false;
let myLongFired = false;
let myPrevUtcDay = null;
let myPositionOpen = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myTs = time[myIndex];
	const myEpochDay = Math.floor(myTs / 86400);
	// Day of week: 0 = Sunday ... 6 = Saturday (Jan 1 1970 was Thursday = 4)
	const myDayOfWeek = (myEpochDay + 4) % 7;
	const myIsWeekday = myDayOfWeek !== 0 && myDayOfWeek !== 6;

	const mySecOfDay = ((myTs % 86400) + 86400) % 86400;
	const myHour = Math.floor(mySecOfDay / 3600);
	const myMinute = Math.floor((mySecOfDay % 3600) / 60);

	const myIsOrPeriod = myIsWeekday && myHour === 13;
	const myIsEntryWin = myIsWeekday && myHour >= 14 && (myHour < 16 || (myHour === 16 && myMinute <= 30));
	const myIsSessionEnd = myIsWeekday && myHour === 20 && myMinute === 0;

	const myIsNewDay = myPrevUtcDay !== null && myPrevUtcDay !== myEpochDay;
	myPrevUtcDay = myEpochDay;

	if (myIsNewDay) {
		myOrHigh = null;
		myOrLow = null;
		myOrReady = false;
		myLongFired = false;
	}

	if (myIsOrPeriod) {
		myOrHigh = myOrHigh === null ? high[myIndex] : Math.max(myOrHigh, high[myIndex]);
		myOrLow = myOrLow === null ? low[myIndex] : Math.min(myOrLow, low[myIndex]);
	}

	if (!myIsOrPeriod && myOrHigh !== null && !myOrReady && myHour >= 14) {
		myOrReady = true;
	}

	const myOrRange = (myOrHigh === null || myOrLow === null) ? null : (myOrHigh - myOrLow);
	const myAtrValue = myAtr[myIndex];
	const myAtrAvgValue = myAtrAvg[myIndex];
	const myVolAvgValue = myVolAvg[myIndex];

	const myRegimeOK = (myAtrValue != null && myAtrAvgValue != null) ? (myAtrValue <= myAtrAvgValue * myRegimeMult) : false;
	const myOrOK = myOrReady && myOrRange !== null && myAtrValue != null && (myOrRange <= myAtrValue * myOrRangeMult);

	const myInDate = myTs >= myStartTimestamp;
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;

	const myLongBreak = myInDate && myIsEntryWin && myOrOK && myRegimeOK && !myLongFired
		&& myOrHigh !== null && close[myIndex] > myOrHigh
		&& myPrevClose !== null && myPrevClose <= myOrHigh
		&& close[myIndex] > open[myIndex]
		&& myVolAvgValue != null && volume[myIndex] > myVolAvgValue * myVolMult;

	if (myLongBreak) {
		myLongFired = true;
		myPositionOpen = true;
	}

	if (myIsSessionEnd && myPositionOpen) {
		myPositionOpen = false;
		mySessionEndOut[myIndex] = true;
	}

	myOrHighOut[myIndex] = myOrReady ? myOrHigh : null;
	myOrLowOut[myIndex] = myOrReady ? myOrLow : null;
	myLongBreakOut[myIndex] = myLongBreak;
}

paint(myOrHighOut, { name: 'OR High', color: '#2ca599', style: 'line', thickness: 1 });
paint(myOrLowOut, { name: 'OR Low', color: '#ee5451', style: 'line', thickness: 1 });

const myLongMarkerSeries = for_every(myLongBreakOut, (_myFlag) => _myFlag ? constants.icons.triangle_up : null);
paint(myLongMarkerSeries, { name: 'Long Entry', style: 'labels_below', color: '#d946ef' });

register_signal(myLongBreakOut, 'Long Entry Signal');
register_signal(mySessionEndOut, 'Session End Close Signal');