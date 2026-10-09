describe_indicator('My Custom No Trading Shield', 'price');

// This indicator reproduces a Pine Script that shades the chart
// background during defined "No Trade" windows, computed in
// Dubai time (UTC+4), regardless of the chart's own time zone.
//
// NOTE: TrendSpider's Custom JS API has no direct equivalent of
// Pine's bgcolor(). As a substitute, this script colors the
// candles themselves during No Trade Zone periods (color_candles),
// and also exposes a register_signal() so the condition can be
// used in Scanners, Alerts and the Strategy Tester.

const myNoTradeColor = input.color('No Trade Zone Color', 'rgba(255,0,0,0.35)');

// Pine's time()/hour()/minute()/dayofweek() with "GMT+4" shift the
// raw UTC epoch by 4 hours and extract calendar fields from that.
// We reproduce this manually, since time_of() uses the exchange's
// own time zone, not an arbitrary fixed offset.
const DUBAI_OFFSET_SECONDS = 4 * 3600;

const myDubaiFields = time.map(_t => {
	const myShifted = _t + DUBAI_OFFSET_SECONDS;
	const myDays = Math.floor(myShifted / 86400);
	const mySecondsOfDay = myShifted - myDays * 86400;
	const myHour = Math.floor(mySecondsOfDay / 3600);
	const myMinute = Math.floor((mySecondsOfDay % 3600) / 60);

	// Pine dayofweek convention: Sunday = 1 ... Saturday = 7.
	// Epoch day 0 (1 Jan 1970) was a Thursday (Pine value 5).
	const myDow = (((myDays + 4) % 7) + 7) % 7 + 1;

	return { hour: myHour, minute: myMinute, dow: myDow };
});

const myNoTradeFlags = myDubaiFields.map(_f => {
	// Rule 1: Friday (dow 6) from 16:00 onward.
	const myIsFridayAfternoon = _f.dow === 6 && (_f.hour > 16 || (_f.hour === 16 && _f.minute >= 0));

	// Rule 2: Full weekend (Saturday = 7, Sunday = 1).
	const myIsWeekend = _f.dow === 7 || _f.dow === 1;

	// Rule 3: All of Monday (dow 2).
	const myIsMonday = _f.dow === 2;

	// Rule 4: Tuesday morning before 11:00 (dow 3).
	const myIsTuesdayMorning = _f.dow === 3 && _f.hour < 11;

	return myIsFridayAfternoon || myIsWeekend || myIsMonday || myIsTuesdayMorning;
});

const myNoTradeColors = myNoTradeFlags.map(_isNoTrade => _isNoTrade ? myNoTradeColor : null);
color_candles(myNoTradeColors);

// Signal usable in Scanners, Alerts and Strategy Tester.
register_signal(myNoTradeFlags, 'No Trade Zone');