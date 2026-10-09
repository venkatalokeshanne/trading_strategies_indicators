describe_indicator('Moon Phase Strategy', 'price');

// NOTE: This is a faithful re-implementation of the Pine Script astronomical
// moon-phase algorithm (Meeus-style approximation), translated line by line.
// Two unavoidable approximations were made (see errors_and_warnings_flagged):
// 1) Pine uses `time_close` (the close time of the bar); the Custom JS API
//    only exposes bar open `time`, so `time` is used as a proxy for `time_close`.
// 2) Pine's `timestamp(year,month,day,hour,minute,second)` resolves in the
//    exchange/chart timezone; here it is approximated using UTC.

const myWaxingColor = input.color('Waxing Moon', 'blue');
const myWaningColor = input.color('Waning Moon', 'white');

assert(current.resolution !== 'M', 'Unsupported timeframe (Monthly).');

// Converts degrees to radians
function myToRadians(_deg) {
	return (_deg * Math.PI) / 180;
}

// Replicates Pine's getUNIXTimeFromJD(), returns a Unix timestamp (seconds)
function myGetUnixTimeFromJD(_julianDay) {
	const myZ = Math.floor(_julianDay + 0.5);
	const myF = (_julianDay + 0.5) % 1;
	const myAlpha = Math.floor((myZ - 1867216.25) / 36524.25);
	const myA = (myZ < 2299161) ? myZ : (myZ + 1 + myAlpha - Math.floor(myAlpha / 4.0));
	const myB = myA + 1524;
	const myC = Math.floor((myB - 122.1) / 365.25);
	const myD = Math.floor(365.25 * myC);
	const myE = Math.floor((myB - myD) / 30.6001);
	const myDayFloat = myB - myD - Math.floor(30.6001 * myE) + myF;
	const myDay = Math.trunc(myDayFloat);
	const myMonth = (myE < 13.5) ? Math.trunc(myE - 1) : Math.trunc(myE - 13);
	const myYear = (myMonth > 2.5) ? Math.trunc(myC - 4716) : Math.trunc(myC - 4715);
	const mySecondTotal = Math.trunc((myDayFloat % 1) * 60 * 60 * 24);
	const myHour = Math.trunc(mySecondTotal / (60 * 60));
	const myMinute = Math.trunc((mySecondTotal - (myHour * 60 * 60)) / 60);
	const mySecond = mySecondTotal % 60;

	// Approximation: using UTC instead of exchange timezone (see notes above)
	return Date.UTC(myYear, myMonth - 1, myDay, myHour, myMinute, mySecond) / 1000;
}

const myMoonPhase = series_of(null);
const myMoonType = series_of(null);

let myPrevTimeLastMoonPhase = null;
let myPrevFinalTimeLastMoonPhase = null;
let myPrevMoonPhaseAdjusted = null;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTime = time[myIndex];
	const myTimeInfo = time_of(myTime);
	const myYear = myTimeInfo.year;
	const myDayOfYear = myTimeInfo.dayOfYear;

	let myK = (myDayOfYear / 364.25 + myYear - 1900) * 12.3685;
	let myCurrentMoonPhase;

	if ((myK % 1.0) < 0.5) {
		myK = Math.floor(myK);
		myCurrentMoonPhase = 1;
	}
	else {
		myK = Math.floor(myK) + 0.5;
		myCurrentMoonPhase = -1;
	}

	const myAnomalySun = myToRadians(359.2242 + (29.10535608 * myK));
	const myAnomalyMoon = myToRadians(306.0253 + (385.81691806 * myK));

	const myDev = (0.1734 * Math.sin(myAnomalySun)) - (0.4068 * Math.sin(myAnomalyMoon));
	const myJulianDate = 2415020.75933 + (29.53058868 * myK) + myDev;

	const myTimeLastMoonPhaseRaw = myGetUnixTimeFromJD(myJulianDate);

	let myTimeLastMoonPhase;
	if (myTimeLastMoonPhaseRaw >= myTime) {
		myTimeLastMoonPhase = myPrevTimeLastMoonPhase;
	}
	else {
		myTimeLastMoonPhase = myTimeLastMoonPhaseRaw;
	}

	const myIsChangeTimeLastMoonPhase = myPrevFinalTimeLastMoonPhase !== null
		&& myTimeLastMoonPhase !== myPrevFinalTimeLastMoonPhase;

	const myIsFirst = myIndex === 0;

	let myMoonPhaseAdjusted;
	if (myIsFirst || myIsChangeTimeLastMoonPhase) {
		myMoonPhaseAdjusted = myCurrentMoonPhase;
	}
	else {
		myMoonPhaseAdjusted = myPrevMoonPhaseAdjusted;
	}

	let myCurrentMoonType = null;
	if (myPrevMoonPhaseAdjusted !== null && myMoonPhaseAdjusted !== myPrevMoonPhaseAdjusted) {
		myCurrentMoonType = myCurrentMoonPhase;
	}

	myMoonPhase[myIndex] = myMoonPhaseAdjusted;
	myMoonType[myIndex] = myCurrentMoonType;

	myPrevTimeLastMoonPhase = myTimeLastMoonPhaseRaw;
	myPrevFinalTimeLastMoonPhase = myTimeLastMoonPhase;
	myPrevMoonPhaseAdjusted = myMoonPhaseAdjusted;
}

const myLongCondition = for_every(myMoonType, _myType => _myType === 1);
const myShortCondition = for_every(myMoonType, _myType => _myType === -1);

// Candle background coloring (waxing vs waning moon phase)
const myCandleColors = for_every(myMoonPhase, _myPhase => _myPhase === 1 ? myWaxingColor : myWaningColor);
color_candles(myCandleColors);

// New Moon / Full Moon markers
const myNewMoonMarks = for_every(myLongCondition, high, (_myLong, _myHigh) => _myLong ? _myHigh : null);
const myFullMoonMarks = for_every(myShortCondition, low, (_myShort, _myLow) => _myShort ? _myLow : null);

paint(myNewMoonMarks, { name: 'NewMoon', style: 'labels_above', color: '#4D7CFE' });
paint(myFullMoonMarks, { name: 'FullMoon', style: 'labels_below', color: '#CCCCCC' });

// Signals usable in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, 'Long Entry (New Moon)');
register_signal(myShortCondition, 'Short Entry (Full Moon)');