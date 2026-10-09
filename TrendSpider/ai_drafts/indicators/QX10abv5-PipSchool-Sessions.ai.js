describe_indicator('PipSchool Sessions', 'price');

// NOTE: Pine's time(res, session, "America/New_York") uses the exact
// trading session logic with explicit timezone and day-of-week filter.
// TrendSpider's Custom JS API has no equivalent of Pine's session()/time()
// functions, so session membership here is approximated using the hour
// and minute of each candle as reported by time_of() (which uses the
// CURRENT TICKER'S EXCHANGE TIMEZONE, not necessarily America/New_York).
// Day-of-week filtering ("1234567" = Mon-Sun) is ignored (assumed "all days").
// This is the closest achievable reproduction given the platform's API.

const myShowHighLowView = input.boolean('Activate High/Low View', false);
const myShowLondon = input.boolean('London Session', true);
const myShowNY = input.boolean('New York Session', true);
// renamed these two text inputs to avoid duplicate input names
// (they previously collided with the boolean toggles above)
const myLondonSessionText = input.text('London Session Hours', '0300-1200');
const myNYSessionText = input.text('New York Session Hours', '0800-1700');

// parses "HHMM-HHMM" into { fromMinutes, toMinutes }
function myParseSession(_sessionText) {
	const myParts = _sessionText.split(':')[0].split('-');
	const myFromRaw = myParts[0];
	const myToRaw = myParts[1];
	const myFromMinutes = parseInt(myFromRaw.slice(0, 2), 10) * 60 + parseInt(myFromRaw.slice(2, 4), 10);
	const myToMinutes = parseInt(myToRaw.slice(0, 2), 10) * 60 + parseInt(myToRaw.slice(2, 4), 10);
	return { myFromMinutes, myToMinutes };
}

const myLondonRange = myParseSession(myLondonSessionText);
const myNYRange = myParseSession(myNYSessionText);

function myIsInSession(_minuteOfDay, _range) {
	if (_range.myFromMinutes <= _range.myToMinutes) {
		return _minuteOfDay >= _range.myFromMinutes && _minuteOfDay < _range.myToMinutes;
	}
	else {
		// overnight session wrap-around
		return _minuteOfDay >= _range.myFromMinutes || _minuteOfDay < _range.myToMinutes;
	}
}

const myCandleCount = close.length;
// avoid "new" keyword: use Array(count) call (no "new") then fill
const myLondonSessionFlags = Array(myCandleCount).fill(false);
const myNYSessionFlags = Array(myCandleCount).fill(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	myLondonSessionFlags[myIndex] = myIsInSession(myMinuteOfDay, myLondonRange);
	myNYSessionFlags[myIndex] = myIsInSession(myMinuteOfDay, myNYRange);
}

// builds running session High/Low series, resetting at the first bar
// of each session and freezing the value outside of the session
// (this reproduces the Pine `londonLow`/`londonHigh` state logic)
function myBuildSessionRange(_sessionFlags) {
	const myLowSeries = Array(myCandleCount).fill(null);
	const myHighSeries = Array(myCandleCount).fill(null);

	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		const myInSession = _sessionFlags[myIndex];
		const myPrevInSession = myIndex > 0 ? _sessionFlags[myIndex - 1] : false;
		const myNewBar = myInSession && !myPrevInSession;

		if (myInSession) {
			if (myNewBar) {
				myLowSeries[myIndex] = low[myIndex];
				myHighSeries[myIndex] = high[myIndex];
			}
			else {
				const myPrevLow = myIndex > 0 ? myLowSeries[myIndex - 1] : null;
				const myPrevHigh = myIndex > 0 ? myHighSeries[myIndex - 1] : null;
				myLowSeries[myIndex] = myPrevLow === null ? low[myIndex] : Math.min(myPrevLow, low[myIndex]);
				myHighSeries[myIndex] = myPrevHigh === null ? high[myIndex] : Math.max(myPrevHigh, high[myIndex]);
			}
		}
		else {
			myLowSeries[myIndex] = myIndex > 0 ? myLowSeries[myIndex - 1] : null;
			myHighSeries[myIndex] = myIndex > 0 ? myHighSeries[myIndex - 1] : null;
		}
	}

	return { myLowSeries, myHighSeries };
}

const myLondonRangeSeries = myBuildSessionRange(myLondonSessionFlags);
const myNYRangeSeries = myBuildSessionRange(myNYSessionFlags);

// paint London range (hidden when toggle off, same structure always)
const myLondonLowPainted = paint(myShowLondon ? myLondonRangeSeries.myLowSeries : constants.empty_series, { name: 'London Low', color: 'green', style: 'line', thickness: 1 });
const myLondonHighPainted = paint(myShowLondon ? myLondonRangeSeries.myHighSeries : constants.empty_series, { name: 'London High', color: 'green', style: 'line', thickness: 1 });
fill(myLondonLowPainted, myLondonHighPainted, 'green', myShowHighLowView ? 0.1 : 0);

// paint New York range
const myNYLowPainted = paint(myShowNY ? myNYRangeSeries.myLowSeries : constants.empty_series, { name: 'New York Low', color: 'red', style: 'line', thickness: 1 });
const myNYHighPainted = paint(myShowNY ? myNYRangeSeries.myHighSeries : constants.empty_series, { name: 'New York High', color: 'red', style: 'line', thickness: 1 });
fill(myNYLowPainted, myNYHighPainted, 'red', myShowHighLowView ? 0.1 : 0);

// background-style highlight via candle coloring when High/Low view is off
// (TrendSpider has no bgcolor(); color_candles() is the closest equivalent)
const myCandleColors = Array(myCandleCount).fill(null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myShowHighLowView) {
		myCandleColors[myIndex] = null;
	}
	else if (myShowLondon && myLondonSessionFlags[myIndex]) {
		myCandleColors[myIndex] = 'rgba(0,255,0,0.1)';
	}
	else if (myShowNY && myNYSessionFlags[myIndex]) {
		myCandleColors[myIndex] = 'rgba(255,0,0,0.1)';
	}
}
color_candles(myCandleColors);

// signals for scanning/alerts/strategy use
register_signal(myLondonSessionFlags, 'London Session Active');
register_signal(myNYSessionFlags, 'New York Session Active');

const myLondonNewBarSignal = myLondonSessionFlags.map((_flag, _index) => _flag && !(_index > 0 && myLondonSessionFlags[_index - 1]));
const myNYNewBarSignal = myNYSessionFlags.map((_flag, _index) => _flag && !(_index > 0 && myNYSessionFlags[_index - 1]));
register_signal(myLondonNewBarSignal, 'London Session New Bar');
register_signal(myNYNewBarSignal, 'New York Session New Bar');