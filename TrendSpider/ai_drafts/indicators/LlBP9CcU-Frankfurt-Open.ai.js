describe_indicator('Frankfurt Open', 'price');

// NOTE: Pine's time(timeframe.period, session, timezone) lets you pick an
// arbitrary IANA timezone for the session window. The Custom JS API only
// gives access to candle timestamps in the exchange's own timezone via
// time_of(). We approximate the session by letting the user set the
// session start/end hours directly as they should appear in the exchange
// timezone of the current chart. This is NOT a true timezone conversion
// to Europe/Berlin; if the exchange timezone differs from the one you
// want, you must adjust the hour inputs manually.

const myStartHour = input.number('Session Start Hour', 8, { min: 0, max: 23 });
const myStartMinute = input.number('Session Start Minute', 0, { min: 0, max: 59 });
const myEndHour = input.number('Session End Hour', 9, { min: 0, max: 23 });
const myEndMinute = input.number('Session End Minute', 0, { min: 0, max: 59 });

const myShowFib = input.boolean('Show Fib Level', true);
const myFibLevel = input.number('Fib Level', 0.5, { min: 0, max: 1 });

// Determine, for every candle, whether it falls inside the session window
const myMinutesOfDay = time.map(_t => {
	const myTimeInfo = time_of(_t);
	return myTimeInfo.hours * 60 + myTimeInfo.minutes;
});

const myStartMinutesOfDay = myStartHour * 60 + myStartMinute;
const myEndMinutesOfDay = myEndHour * 60 + myEndMinute;

const myInSession = myMinutesOfDay.map(_m => _m >= myStartMinutesOfDay && _m < myEndMinutesOfDay);

const myIsStart = series_of(false);
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	myIsStart[myIndex] = myInSession[myIndex] && (myIndex === 0 ? false : !myInSession[myIndex - 1]);
}

// Running high/low of the current session, box top/bottom equivalents
const myTop = series_of(null);
const myBottom = series_of(null);
const myFib = series_of(null);

let myRunningHigh = null;
let myRunningLow = null;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	if (myIsStart[myIndex]) {
		myRunningHigh = high[myIndex];
		myRunningLow = low[myIndex];
	}
	else if (myInSession[myIndex] && myRunningHigh !== null) {
		myRunningHigh = Math.max(myRunningHigh, high[myIndex]);
		myRunningLow = Math.min(myRunningLow, low[myIndex]);
	}

	if (myInSession[myIndex] && myRunningHigh !== null) {
		myTop[myIndex] = myRunningHigh;
		myBottom[myIndex] = myRunningLow;
		myFib[myIndex] = myRunningLow + (myRunningHigh - myRunningLow) * myFibLevel;
	}
}

// Box borders (top/bottom) painted as a ladder (no interpolation between sessions)
const myTopLinePainted = paint(myTop, { name: 'SessionHigh', color: 'gray', style: 'ladder', thickness: 1 });
const myBottomLinePainted = paint(myBottom, { name: 'SessionLow', color: 'gray', style: 'ladder', thickness: 1 });
fill(myTopLinePainted, myBottomLinePainted, 'gray', 0.1);

// Fib level line, shown only when enabled; kept as a constant-shaped output
const myFibToPaint = myShowFib ? myFib : series_of(null);
const myFibLinePainted = paint(myFibToPaint, { name: 'FibLevel', color: 'orange', style: 'ladder', thickness: 1 });
paint_label_at_line(myFibLinePainted, close.length - 1, 'Fib Level', { color: 'orange' });

// Signals for scanners/alerts/strategies
register_signal(myIsStart, 'Session Start');
register_signal(myInSession, 'In Session');