// NOTE: this indicator reproduces the "Gold NY Open ORB v11" Pine Script
// logic as closely as the Custom JS API allows. Pine's strategy() engine
// (equity sizing, actual order fills, strategy.close_all) is not available
// here, so this is translated into a plain indicator which recreates the
// exact same bar-by-bar signal conditions (OR building, OR readiness,
// long breakout entry, session-end exit time) and exposes them as
// register_signal() outputs for scanners/alerts/strategy tester, plus
// plots of the Opening Range high/low and the entry marker.
//
// Pine bgcolor() panel shading has no equivalent in this API and is
// therefore omitted.

describe_indicator('Gold NY Open ORB v11', 'price');

assert(!isNaN(current.resolution), 'Only applicable to intraday charts');

const myRiskPct = input.number('Risk per trade (%)', 1.5, { min: 0.1, max: 5.0 });

const myAtr = atr(high, low, close, 14);
const myVolAvg = sma(volume, 20);
const myAtrAvg20 = sma(myAtr, 20);

// === compute UTC-based calendar fields directly from the Unix timestamp ===
// (Unix time is already UTC, so no timezone conversion library is needed)
const myDayIndex = time.map(_t => Math.floor(_t / 86400));
const myDow = myDayIndex.map(_d => (_d + 4) % 7); // 0 = Sunday ... 6 = Saturday
const mySecOfDay = time.map(_t => ((_t % 86400) + 86400) % 86400);
const myHour = mySecOfDay.map(_s => Math.floor(_s / 3600));
const myMinute = mySecOfDay.map(_s => Math.floor((_s % 3600) / 60));

const myIsWkd = myDow.map(_d => _d !== 0 && _d !== 6);
const myIsORPeriod = myHour.map((_h, _i) => myIsWkd[_i] && _h === 13);
const myIsEntryWin = myHour.map((_h, _i) => myIsWkd[_i] && (_h >= 14) && (_h < 16 || (_h === 16 && myMinute[_i] <= 30)));
const myIsSessionEnd = myHour.map((_h, _i) => myIsWkd[_i] && _h === 16 && myMinute[_i] === 30);

const myRegimeOK = for_every(myAtr, myAtrAvg20, (_a, _b) => _a <= _b * 2.0);

// === stateful loop reproducing Pine's `var` persisted state ===
const myOrHighOut = series_of(null);
const myOrLowOut = series_of(null);
const myLongBreakOut = series_of(false);
const mySessionEndOut = series_of(false);

let myOrHigh = null;
let myOrLow = null;
let myOrReady = false;
let myLongFired = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myNewDay = myIndex > 0 && myDayIndex[myIndex] !== myDayIndex[myIndex - 1];

	if (myNewDay) {
		myOrHigh = null;
		myOrLow = null;
		myOrReady = false;
		myLongFired = false;
	}

	if (myIsORPeriod[myIndex]) {
		myOrHigh = (myOrHigh === null) ? high[myIndex] : Math.max(myOrHigh, high[myIndex]);
		myOrLow = (myOrLow === null) ? low[myIndex] : Math.min(myOrLow, low[myIndex]);
	}

	if (!myIsORPeriod[myIndex] && myOrHigh !== null && !myOrReady && myHour[myIndex] >= 14) {
		myOrReady = true;
	}

	const myOrRange = (myOrHigh === null || myOrLow === null) ? null : (myOrHigh - myOrLow);
	const myOrOK = myOrReady && myOrRange !== null && myOrRange <= myAtr[myIndex] * 2.5;

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myLongBreak = myIsEntryWin[myIndex] && myOrOK && myRegimeOK[myIndex] && !myLongFired
		&& myOrHigh !== null
		&& close[myIndex] > myOrHigh
		&& myPrevClose !== null && myPrevClose <= myOrHigh
		&& close[myIndex] > open[myIndex]
		&& volume[myIndex] > myVolAvg[myIndex] * 1.5;

	if (myLongBreak) {
		myLongFired = true;
	}

	myOrHighOut[myIndex] = myOrReady ? myOrHigh : null;
	myOrLowOut[myIndex] = myOrReady ? myOrLow : null;
	myLongBreakOut[myIndex] = myLongBreak;
	mySessionEndOut[myIndex] = myIsSessionEnd[myIndex];
}

// === plots ===
paint(myOrHighOut, { name: 'ORHigh', color: '#2ca599', style: 'ladder' });
paint(myOrLowOut, { name: 'ORLow', color: '#ee5451', style: 'ladder' });

const myEntryMarker = for_every(close, (_c, _prev, _i) => myLongBreakOut[_i] ? low[_i] : null);
paint(myEntryMarker, { name: 'LongEntry', style: 'labels_below', color: 'lime' });

// === scanner / alert / strategy signals ===
register_signal(myLongBreakOut, 'Long Entry');
register_signal(mySessionEndOut, 'Session End Close');