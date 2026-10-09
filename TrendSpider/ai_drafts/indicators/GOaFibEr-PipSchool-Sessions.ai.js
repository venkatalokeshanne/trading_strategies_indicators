describe_indicator('PipSchool Sessions', 'price');

// NOTE: TrendSpider's Custom JS API has no direct equivalent of Pine's
// time(resolution, session, timezone) function, which can evaluate an
// arbitrary session string in an arbitrary timezone (here NY) regardless
// of the chart's exchange timezone. time_of() always uses the exchange
// timezone of the current ticker. This script approximates Pine's
// behavior by assuming the chart's exchange timezone is America/New_York.
// If the current ticker is not NY-based, session detection will be off.
// Also, day-of-week filtering from the session string (the "1234567" part)
// is ignored; sessions are evaluated for every day of the week.

const myShowHighLowView = input.boolean('Activate High/Low View', false);
const myShowLondon = input.boolean('London Session', true);
const myShowNY = input.boolean('New York Session', true);

const myLondonSessionText = input.text('London Session Hours', '0300-1200');
const myNySessionText = input.text('New York Session Hours', '0800-1700');

function myParseSession(_sessionString) {
	const myParts = _sessionString.split('-');
	assert(myParts.length === 2, 'Session string must be formatted like 0300-1200');
	const myStartH = parseInt(myParts[0].slice(0, 2), 10);
	const myStartM = parseInt(myParts[0].slice(2, 4), 10);
	const myEndH = parseInt(myParts[1].slice(0, 2), 10);
	const myEndM = parseInt(myParts[1].slice(2, 4), 10);
	return { myStartH, myStartM, myEndH, myEndM };
}

function myIsInSession(_hour, _minute, _sessionDef) {
	const myCurrentMinutes = _hour * 60 + _minute;
	const myStartMinutes = _sessionDef.myStartH * 60 + _sessionDef.myStartM;
	const myEndMinutes = _sessionDef.myEndH * 60 + _sessionDef.myEndM;

	if (myStartMinutes <= myEndMinutes) {
		return myCurrentMinutes >= myStartMinutes && myCurrentMinutes < myEndMinutes;
	}
	else {
		// overnight session, wraps past midnight
		return myCurrentMinutes >= myStartMinutes || myCurrentMinutes < myEndMinutes;
	}
}

const myLondonDef = myParseSession(myLondonSessionText);
const myNyDef = myParseSession(myNySessionText);

const myLondonSessionFlags = [];
const myNySessionFlags = [];
const myLondonLow = series_of(null);
const myLondonHigh = series_of(null);
const myNyLow = series_of(null);
const myNyHigh = series_of(null);

let myPrevLondonInSession = false;
let myPrevNyInSession = false;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);

	const myInLondon = myIsInSession(myTimeInfo.hours, myTimeInfo.minutes, myLondonDef);
	const myInNy = myIsInSession(myTimeInfo.hours, myTimeInfo.minutes, myNyDef);

	myLondonSessionFlags[myIndex] = myInLondon;
	myNySessionFlags[myIndex] = myInNy;

	const myLondonNewBar = myInLondon && !myPrevLondonInSession;
	const myNyNewBar = myInNy && !myPrevNyInSession;

	if (myInLondon) {
		if (myLondonNewBar) {
			myLondonLow[myIndex] = low[myIndex];
			myLondonHigh[myIndex] = high[myIndex];
		}
		else {
			myLondonLow[myIndex] = Math.min(myLondonLow[myIndex - 1], low[myIndex]);
			myLondonHigh[myIndex] = Math.max(myLondonHigh[myIndex - 1], high[myIndex]);
		}
	}
	else {
		myLondonLow[myIndex] = myLondonLow[myIndex - 1] ?? null;
		myLondonHigh[myIndex] = myLondonHigh[myIndex - 1] ?? null;
	}

	if (myInNy) {
		if (myNyNewBar) {
			myNyLow[myIndex] = low[myIndex];
			myNyHigh[myIndex] = high[myIndex];
		}
		else {
			myNyLow[myIndex] = Math.min(myNyLow[myIndex - 1], low[myIndex]);
			myNyHigh[myIndex] = Math.max(myNyHigh[myIndex - 1], high[myIndex]);
		}
	}
	else {
		myNyLow[myIndex] = myNyLow[myIndex - 1] ?? null;
		myNyHigh[myIndex] = myNyHigh[myIndex - 1] ?? null;
	}

	myPrevLondonInSession = myInLondon;
	myPrevNyInSession = myInNy;
}

// Hidden lines used only to anchor the fill() between session high and low
const myLondonLowLine = paint(myLondonLow, { name: 'LondonLow', color: 'transparent', hidden: true });
const myLondonHighLine = paint(myLondonHigh, { name: 'LondonHigh', color: 'transparent', hidden: true });
fill(myLondonLowLine, myLondonHighLine, 'green', 0.1);

const myNyLowLine = paint(myNyLow, { name: 'NewYorkLow', color: 'transparent', hidden: true });
const myNyHighLine = paint(myNyHigh, { name: 'NewYorkHigh', color: 'transparent', hidden: true });
fill(myNyLowLine, myNyHighLine, 'red', 0.1);

// Pine's bgcolor() highlights the whole chart background per bar; the
// Custom JS API has no equivalent for overlay indicators, so candle
// coloring (color_candles) is used instead as the closest substitute
// when "Activate High/Low View" is off.
const myCandleColors = for_every(
	series_of(0),
	(_v, _prev, _index) => {
		if (!myShowHighLowView) {
			if (myShowLondon && myLondonSessionFlags[_index]) return 'rgba(0,180,0,0.15)';
			if (myShowNY && myNySessionFlags[_index]) return 'rgba(255,0,0,0.15)';
		}
		return null;
	}
);
color_candles(myCandleColors);

const myLondonSessionSignal = for_every(series_of(0), (_v, _prev, _index) => myShowLondon && myLondonSessionFlags[_index]);
const myNySessionSignal = for_every(series_of(0), (_v, _prev, _index) => myShowNY && myNySessionFlags[_index]);
register_signal(myLondonSessionSignal, 'London Session Active');
register_signal(myNySessionSignal, 'New York Session Active');