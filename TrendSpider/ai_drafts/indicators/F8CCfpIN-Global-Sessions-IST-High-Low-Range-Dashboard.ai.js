describe_indicator('Global Sessions IST - High/Low and Range Dashboard', 'price');
// NOTE: This is a best-effort conversion of a Pine Script v6 indicator.
// TrendSpider's Custom JS API has no equivalent of Pine's box.new()/table
// drawing primitives tied to the price axis, and no native session()
// time-matching function. Session High/Low "boxes" are approximated here
// using lines + fill() limited to the session span, and the dashboard is
// implemented with paint_overlay() instead of a Pine table.
const myMoment = library('moment-timezone');

// ---------------- Display options ----------------
const myDisplayTab = input.tab('Display Style');
const myShowBox = myDisplayTab.boolean('Draw Session Lines', true);
const myShowDash = myDisplayTab.boolean('Show Info Dashboard', true);

// ---------------- Timezone configuration ----------------
const myTimeTab = input.tab('Timezone Configuration');
// Shortened input name to satisfy the platform's input name length limit.
const myDST = myTimeTab.boolean('Enable DST Offset', false);

// ---------------- Session configuration ----------------
const myAsiaGroup = input.tab('1. Asian Session (Tokyo/HK)');
const myAsiaTime = myAsiaGroup.text('Asian Time Range', '0530-1330:23456');
const myAsiaColor = 'purple';

const myLondonGroup = input.tab('2. London Session');
const myLondonTime = myLondonGroup.text('London Time Range', '1230-2100:23456');
const myLondonColor = 'blue';

const myNYGroup = input.tab('3. New York Session');
const myNYTime = myNYGroup.text('New York Time Range', '1830-0230:23456');
const myNYColor = 'orange';

// DST-adjusted London/NY session strings (hardcoded shift as per original script)
const myLondonTimeFinal = myDST ? '1330-2200:23456' : myLondonTime;
const myNYTimeFinal = myDST ? '1930-0330:23456' : myNYTime;

// ---------------- Session string parser ----------------
// Parses "HHMM-HHMM:days" where days use Pine convention: 1=Sun,2=Mon,...,7=Sat
function myParseSession(_sessionString) {
	const mySplit = _sessionString.split(':');
	const myRange = mySplit[0];
	const myDaysString = mySplit[1] || '1234567';
	const myRangeParts = myRange.split('-');
	const myStartHHMM = myRangeParts[0];
	const myEndHHMM = myRangeParts[1];
	const myStartMinutes = parseInt(myStartHHMM.substring(0, 2), 10) * 60 + parseInt(myStartHHMM.substring(2, 4), 10);
	const myEndMinutes = parseInt(myEndHHMM.substring(0, 2), 10) * 60 + parseInt(myEndHHMM.substring(2, 4), 10);
	// Convert Pine day codes (1=Sun..7=Sat) to ISO weekday (1=Mon..7=Sun)
	const myPineToIso = { 1: 7, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6 };
	const myAllowedIsoDays = myDaysString.split('').map(_d => myPineToIso[parseInt(_d, 10)]);
	return { startMinutes: myStartMinutes, endMinutes: myEndMinutes, allowedIsoDays: myAllowedIsoDays };
}

const myAsiaSession = myParseSession(myAsiaTime);
const myLondonSession = myParseSession(myLondonTimeFinal);
const myNYSession = myParseSession(myNYTimeFinal);

// ---------------- Compute per-candle IST time info ----------------
const myISTMinutesArray = time.map(_t => {
	const myMomentIST = myMoment.tz(_t * 1000, 'Asia/Kolkata');
	return myMomentIST.hours() * 60 + myMomentIST.minutes();
});

const myISODayArray = time.map(_t => {
	const myMomentIST = myMoment.tz(_t * 1000, 'Asia/Kolkata');
	return myMomentIST.isoWeekday();
});

const myPrevISODayArray = time.map((_t, _i) => {
	const myMomentPrevDay = myMoment.tz(_t * 1000, 'Asia/Kolkata').subtract(1, 'days');
	return myMomentPrevDay.isoWeekday();
});

// ---------------- Session active detection (handles overnight wrap) ----------------
function myIsSessionActive(_sessionDef, _candleIndex) {
	const myMinutesNow = myISTMinutesArray[_candleIndex];
	const myStart = _sessionDef.startMinutes;
	const myEnd = _sessionDef.endMinutes;

	if (myStart < myEnd) {
		return myMinutesNow >= myStart && myMinutesNow < myEnd && _sessionDef.allowedIsoDays.includes(myISODayArray[_candleIndex]);
	}
	else {
		const myAfterStartToday = myMinutesNow >= myStart && _sessionDef.allowedIsoDays.includes(myISODayArray[_candleIndex]);
		const myBeforeEndFromPrevDay = myMinutesNow < myEnd && _sessionDef.allowedIsoDays.includes(myPrevISODayArray[_candleIndex]);
		return myAfterStartToday || myBeforeEndFromPrevDay;
	}
}

const myInAsiaArray = time.map((_t, _i) => myIsSessionActive(myAsiaSession, _i));
const myInLondonArray = time.map((_t, _i) => myIsSessionActive(myLondonSession, _i));
const myInNYArray = time.map((_t, _i) => myIsSessionActive(myNYSession, _i));

// ---------------- Session High/Low/Range state machine (mirrors Pine f_processSession) ----------------
function myProcessSession(_activeArray) {
	const myRunningHigh = series_of(null);
	const myRunningLow = series_of(null);
	const myLastHigh = series_of(null);
	const myLastLow = series_of(null);
	const myLastRange = series_of(null);

	let myStateHigh = null;
	let myStateLow = null;
	let myStateLastHigh = null;
	let myStateLastLow = null;
	let myStateLastRange = null;

	for (let myIndex = 0; myIndex < _activeArray.length; myIndex += 1) {
		const myActiveNow = _activeArray[myIndex];
		const myActivePrev = myIndex > 0 ? _activeArray[myIndex - 1] : false;

		if (myActiveNow && !myActivePrev) {
			// Session start
			myStateHigh = high[myIndex];
			myStateLow = low[myIndex];
		}
		else if (myActiveNow) {
			// During session
			myStateHigh = Math.max(myStateHigh, high[myIndex]);
			myStateLow = Math.min(myStateLow, low[myIndex]);
		}
		else if (!myActiveNow && myActivePrev) {
			// Session close
			myStateLastHigh = myStateHigh;
			myStateLastLow = myStateLow;
			myStateLastRange = myStateHigh - myStateLow;
		}

		myRunningHigh[myIndex] = myActiveNow ? myStateHigh : null;
		myRunningLow[myIndex] = myActiveNow ? myStateLow : null;
		myLastHigh[myIndex] = myStateLastHigh;
		myLastLow[myIndex] = myStateLastLow;
		myLastRange[myIndex] = myStateLastRange;
	}

	return { runningHigh: myRunningHigh, runningLow: myRunningLow, lastHigh: myLastHigh, lastLow: myLastLow, lastRange: myLastRange };
}

const myAsiaResult = myProcessSession(myInAsiaArray);
const myLondonResult = myProcessSession(myInLondonArray);
const myNYResult = myProcessSession(myInNYArray);

// ---------------- Painting session High/Low lines (box approximation) ----------------
const myAsiaHighLine = myShowBox ? myAsiaResult.runningHigh : series_of(null);
const myAsiaLowLine = myShowBox ? myAsiaResult.runningLow : series_of(null);
const myLondonHighLine = myShowBox ? myLondonResult.runningHigh : series_of(null);
const myLondonLowLine = myShowBox ? myLondonResult.runningLow : series_of(null);
const myNYHighLine = myShowBox ? myNYResult.runningHigh : series_of(null);
const myNYLowLine = myShowBox ? myNYResult.runningLow : series_of(null);

const myAsiaHighPainted = paint(myAsiaHighLine, { name: 'AsiaHigh', color: myAsiaColor, style: 'ladder', thickness: 1 });
const myAsiaLowPainted = paint(myAsiaLowLine, { name: 'AsiaLow', color: myAsiaColor, style: 'ladder', thickness: 1 });
fill(myAsiaHighPainted, myAsiaLowPainted, myAsiaColor, 0.15);

const myLondonHighPainted = paint(myLondonHighLine, { name: 'LondonHigh', color: myLondonColor, style: 'ladder', thickness: 1 });
const myLondonLowPainted = paint(myLondonLowLine, { name: 'LondonLow', color: myLondonColor, style: 'ladder', thickness: 1 });
fill(myLondonHighPainted, myLondonLowPainted, myLondonColor, 0.15);

const myNYHighPainted = paint(myNYHighLine, { name: 'NewYorkHigh', color: myNYColor, style: 'ladder', thickness: 1 });
const myNYLowPainted = paint(myNYLowLine, { name: 'NewYorkLow', color: myNYColor, style: 'ladder', thickness: 1 });
fill(myNYHighPainted, myNYLowPainted, myNYColor, 0.15);

// ---------------- Dashboard (top right) ----------------
const myLastIndex = close.length - 1;

function myFormatValue(_value) {
	return _value === null || _value === undefined || isNaN(_value) ? '-' : _value.toFixed(2);
}

const myAsiaDashHigh = myInAsiaArray[myLastIndex] ? myAsiaResult.runningHigh[myLastIndex] : myAsiaResult.lastHigh[myLastIndex];
const myAsiaDashLow = myInAsiaArray[myLastIndex] ? myAsiaResult.runningLow[myLastIndex] : myAsiaResult.lastLow[myLastIndex];
const myAsiaDashRange = myInAsiaArray[myLastIndex] ? (myAsiaDashHigh - myAsiaDashLow) : myAsiaResult.lastRange[myLastIndex];

const myLondonDashHigh = myInLondonArray[myLastIndex] ? myLondonResult.runningHigh[myLastIndex] : myLondonResult.lastHigh[myLastIndex];
const myLondonDashLow = myInLondonArray[myLastIndex] ? myLondonResult.runningLow[myLastIndex] : myLondonResult.lastLow[myLastIndex];
const myLondonDashRange = myInLondonArray[myLastIndex] ? (myLondonDashHigh - myLondonDashLow) : myLondonResult.lastRange[myLastIndex];

const myNYDashHigh = myInNYArray[myLastIndex] ? myNYResult.runningHigh[myLastIndex] : myNYResult.lastHigh[myLastIndex];
const myNYDashLow = myInNYArray[myLastIndex] ? myNYResult.runningLow[myLastIndex] : myNYResult.lastLow[myLastIndex];
const myNYDashRange = myInNYArray[myLastIndex] ? (myNYDashHigh - myNYDashLow) : myNYResult.lastRange[myLastIndex];

paint_overlay('SessionDashboard', { position: 'top_right' }, {
	rows: myShowDash ? [
		{
			cells: [
				{ text: 'Session', color: 'white', background_color: 'gray' },
				{ text: 'High', color: 'white', background_color: 'gray' },
				{ text: 'Low', color: 'white', background_color: 'gray' },
				{ text: 'Range', color: 'white', background_color: 'gray' }
			]
		},
		{
			cells: [
				{ text: 'Asia', color: myAsiaColor },
				{ text: myFormatValue(myAsiaDashHigh), color: 'white' },
				{ text: myFormatValue(myAsiaDashLow), color: 'white' },
				{ text: myFormatValue(myAsiaDashRange), color: 'white' }
			]
		},
		{
			cells: [
				{ text: 'London', color: myLondonColor },
				{ text: myFormatValue(myLondonDashHigh), color: 'white' },
				{ text: myFormatValue(myLondonDashLow), color: 'white' },
				{ text: myFormatValue(myLondonDashRange), color: 'white' }
			]
		},
		{
			cells: [
				{ text: 'New York', color: myNYColor },
				{ text: myFormatValue(myNYDashHigh), color: 'white' },
				{ text: myFormatValue(myNYDashLow), color: 'white' },
				{ text: myFormatValue(myNYDashRange), color: 'white' }
			]
		}
	] : []
});

// ---------------- Scanner/Strategy/Alert signals ----------------
register_signal(myInAsiaArray, 'Asia Session Active');
register_signal(myInLondonArray, 'London Session Active');
register_signal(myInNYArray, 'New York Session Active');