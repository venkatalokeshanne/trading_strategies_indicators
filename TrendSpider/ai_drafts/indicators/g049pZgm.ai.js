describe_indicator('Horarios Trampa ArelisFX');

// ─────────────────────────────────────────────────────────────────────────
// NOTE: TrendSpider's Custom JS API does not have an equivalent of Pine's
// `time(timeframe, session, timezone)` function, and candle timestamps are
// always expressed/interpreted using the exchange's own timezone via
// time_of(). To reproduce the original Pine logic (which lets the user pick
// an arbitrary timezone) we use the "moment-timezone" library to convert
// each candle's UTC timestamp into the chosen timezone, then test it
// against the session windows manually. This is a faithful reproduction of
// the Pine logic, but relies on a 3rd party library instead of a native
// built-in, since no native built-in supports arbitrary timezone session
// checks.
// ─────────────────────────────────────────────────────────────────────────

const myMoment = library('moment-timezone');

const myTimeZone = input.select('Zona horaria', 'Europe/Madrid', [
	'Europe/Madrid',
	'Europe/London',
	'America/New_York',
	'America/Bogota',
	'America/Mexico_City',
	'UTC'
]);

const myTrapColor = input.color('Color', 'red');

const mySession1Row = input.row();
const mySession1Start = mySession1Row.text('1 Amanecer Inicio', '0600');
const mySession1End = mySession1Row.text('1 Amanecer Fin', '0800');

const mySession2Row = input.row();
const mySession2Start = mySession2Row.text('2 Pausa Londres Inicio', '1300');
const mySession2End = mySession2Row.text('2 Pausa Londres Fin', '1430');

const mySession3Row = input.row();
const mySession3Start = mySession3Row.text('3 Cierre Londres Inicio', '1700');
const mySession3End = mySession3Row.text('3 Cierre Londres Fin', '1830');

// Converts a "HHMM" string into minutes since midnight.
function myMinutesFromHHMM(_hhmm) {
	const myHours = parseInt(_hhmm.slice(0, 2), 10);
	const myMinutes = parseInt(_hhmm.slice(2, 4), 10);
	return (myHours * 60) + myMinutes;
}

const myWindows = [
	{ from: myMinutesFromHHMM(mySession1Start), to: myMinutesFromHHMM(mySession1End) },
	{ from: myMinutesFromHHMM(mySession2Start), to: myMinutesFromHHMM(mySession2End) },
	{ from: myMinutesFromHHMM(mySession3Start), to: myMinutesFromHHMM(mySession3End) }
];

// Pine's "timeframe.isintraday" equivalent: true if the chart's resolution
// is not Daily/Weekly/Monthly (those resolutions are non-numeric strings).
const myIsIntraday = !isNaN(current.resolution);

const myTrapFlags = time.map(_timestamp => {
	if (!myIsIntraday) {
		return false;
	}

	const myLocalMoment = myMoment.tz(_timestamp * 1000, myTimeZone);
	const myMinutesOfDay = (myLocalMoment.hours() * 60) + myLocalMoment.minutes();

	return myWindows.some(_window => myMinutesOfDay >= _window.from && myMinutesOfDay < _window.to);
});

// Colors candles to approximate Pine's bgcolor() highlight (TrendSpider's
// Custom JS API has no direct equivalent of chart-wide background
// coloring, color_candles() is the closest available substitute).
const myCandleColors = myTrapFlags.map(_flag => _flag ? myTrapColor : null);
color_candles(myCandleColors);

// Exposes the trap condition as a scanner/alert/strategy-ready signal.
register_signal(myTrapFlags, 'Horario Trampa');