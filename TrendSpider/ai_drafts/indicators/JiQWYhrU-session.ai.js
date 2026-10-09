describe_indicator('Session Highlighter', 'price');

// NOTE: The Custom JS API has no bgcolor() function and no way to
// convert timestamps into an arbitrary UTC offset chosen by the user.
// time_of() only gives hours/minutes in the exchange's own timezone.
// So instead of a background color, we color candles that fall
// inside each session, and we approximate "timezone" by using the
// exchange timezone only (the tz_input selector from Pine is dropped).

const myShowUsa = input.boolean('USA Session', true);
const myShowAsia = input.boolean('Asia Session', true);
const myShowEur = input.boolean('Europe Session', true);

const myColorUsa = input.color('USA Color', 'rgba(149,253,204,0.35)');
const myColorAsia = input.color('Asia Color', 'rgba(252,145,131,0.35)');
const myColorEur = input.color('Europe Color', 'rgba(90,78,253,0.35)');

const myIncludeWeekends = input.boolean('Include Weekends', false);

// Session windows, HHMM format, matching the Pine defaults
const mySessionUsaStart = input.number('USA Start (HHMM)', 1330, { min: 0, max: 2359 });
const mySessionUsaEnd = input.number('USA End (HHMM)', 2200, { min: 0, max: 2359 });
const mySessionAsiaStart = input.number('Asia Start (HHMM)', 0, { min: 0, max: 2359 });
const mySessionAsiaEnd = input.number('Asia End (HHMM)', 900, { min: 0, max: 2359 });
const mySessionEurStart = input.number('Europe Start (HHMM)', 600, { min: 0, max: 2359 });
const mySessionEurEnd = input.number('Europe End (HHMM)', 1500, { min: 0, max: 2359 });

// Converts a HHMM integer into total minutes since midnight
function myMinutesOf(_hhmm) {
	const myHours = Math.floor(_hhmm / 100);
	const myMinutes = _hhmm % 100;
	return myHours * 60 + myMinutes;
}

// Checks whether a given minute-of-day falls inside a session window,
// handling sessions that wrap past midnight (like Asia 0000-0900 does not wrap,
// but USA 1330-2200 could in other setups)
function myIsInSession(_minuteOfDay, _startMinutes, _endMinutes) {
	if (_startMinutes <= _endMinutes) {
		return _minuteOfDay >= _startMinutes && _minuteOfDay < _endMinutes;
	}
	else {
		return _minuteOfDay >= _startMinutes || _minuteOfDay < _endMinutes;
	}
}

const myUsaStartMinutes = myMinutesOf(mySessionUsaStart);
const myUsaEndMinutes = myMinutesOf(mySessionUsaEnd);
const myAsiaStartMinutes = myMinutesOf(mySessionAsiaStart);
const myAsiaEndMinutes = myMinutesOf(mySessionAsiaEnd);
const myEurStartMinutes = myMinutesOf(mySessionEurStart);
const myEurEndMinutes = myMinutesOf(mySessionEurEnd);

const myInUsaSession = series_of(null);
const myInAsiaSession = series_of(null);
const myInEurSession = series_of(null);

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	// Pine's "weekends" flag ":23456" means "only Mon(2)-Fri(6)" in Pine's
	// day numbering; here dayOfWeek is ISO (1=Mon...7=Sun), so weekend is 6,7
	const myIsWeekend = myTimeInfo.dayOfWeek === 6 || myTimeInfo.dayOfWeek === 7;
	const myWeekendAllowed = myIncludeWeekends || !myIsWeekend;

	myInUsaSession[myIndex] = myWeekendAllowed && myIsInSession(myMinuteOfDay, myUsaStartMinutes, myUsaEndMinutes);
	myInAsiaSession[myIndex] = myWeekendAllowed && myIsInSession(myMinuteOfDay, myAsiaStartMinutes, myAsiaEndMinutes);
	myInEurSession[myIndex] = myWeekendAllowed && myIsInSession(myMinuteOfDay, myEurStartMinutes, myEurEndMinutes);
}

// Picks a candle color based on which sessions are active, with a
// priority order (USA, then Asia, then Europe) since candles can only
// have one color at a time, unlike Pine's stacked bgcolor() calls
const myCandleColors = for_every(series_of(0), (_v, _p, _index) => {
	if (myShowUsa && myInUsaSession[_index]) return myColorUsa;
	if (myShowAsia && myInAsiaSession[_index]) return myColorAsia;
	if (myShowEur && myInEurSession[_index]) return myColorEur;
	return null;
});

color_candles(myCandleColors);

// Signals for scanners, alerts and strategies
register_signal(for_every(series_of(0), (_v, _p, _index) => myShowUsa && myInUsaSession[_index]), 'In USA Session');
register_signal(for_every(series_of(0), (_v, _p, _index) => myShowAsia && myInAsiaSession[_index]), 'In Asia Session');
register_signal(for_every(series_of(0), (_v, _p, _index) => myShowEur && myInEurSession[_index]), 'In Europe Session');