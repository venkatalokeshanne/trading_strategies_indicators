describe_indicator('Vela Horaria Vertical Configurable', 'price');

// NOTE: TrendSpider Custom JS API has no direct equivalent to Pine's
// bgcolor() (a vertical background strip). The closest approximation
// available is color_candles(), which colors the candle itself instead
// of painting a background band behind it.
const myMoment = library('moment-timezone');
const myTimeZone = 'America/Argentina/Buenos_Aires';

// ================== Inputs - Vela 1 ==================
const myTab1 = input.tab('Vela 1');
const myHora1 = myTab1.number('Hora vela 1 (ARG, 0-23)', 19, { min: 0, max: 23 });
const myMinuto1 = myTab1.number('Minuto vela 1 (ARG, 0-59)', 0, { min: 0, max: 59 });
const myColor1 = input.color('Color franja 1', 'rgba(0,0,255,0.4)');
const myActivar1 = myTab1.boolean('Activar franja 1', true);

// ================== Inputs - Vela 2 ==================
const myTab2 = input.tab('Vela 2');
const myHora2 = myTab2.number('Hora vela 2 (ARG, 0-23)', 21, { min: 0, max: 23 });
const myMinuto2 = myTab2.number('Minuto vela 2 (ARG, 0-59)', 0, { min: 0, max: 59 });
const myColor2 = input.color('Color franja 2', 'rgba(255,165,0,0.4)');
const myActivar2 = myTab2.boolean('Activar franja 2', true);

// ================== Candle duration (seconds), used to build "barEnd" ==================
const myBarDurations = time.map((_t, _i) => {
	if (_i < time.length - 1) {
		return time[_i + 1] - time[_i];
	}
	else if (_i > 0) {
		return time[_i] - time[_i - 1];
	}
	else {
		return 60;
	}
});

// ================== For each candle, build the anchor timestamps (in Argentina time) ==================
// for the day the candle belongs to, then check if the anchor falls within
// [barStart, barEnd) of that candle, exactly mirroring the Pine logic.
const myEsVela1 = series_of(false);
const myEsVela2 = series_of(false);

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myBarStart = time[myIndex];
	const myBarEnd = myBarStart + myBarDurations[myIndex];

	const myArgMoment = myMoment.tz(myBarStart * 1000, myTimeZone);

	const myAnchorTime1 = myMoment.tz(myTimeZone)
		.year(myArgMoment.year())
		.month(myArgMoment.month())
		.date(myArgMoment.date())
		.hour(myHora1)
		.minute(myMinuto1)
		.second(0)
		.millisecond(0)
		.unix();

	const myAnchorTime2 = myMoment.tz(myTimeZone)
		.year(myArgMoment.year())
		.month(myArgMoment.month())
		.date(myArgMoment.date())
		.hour(myHora2)
		.minute(myMinuto2)
		.second(0)
		.millisecond(0)
		.unix();

	myEsVela1[myIndex] = myActivar1 && myAnchorTime1 >= myBarStart && myAnchorTime1 < myBarEnd;
	myEsVela2[myIndex] = myActivar2 && myAnchorTime2 >= myBarStart && myAnchorTime2 < myBarEnd;
}

// ================== Approximate the background strip by coloring the candle ==================
const myCandleColors = for_every(close, (_c, _prev, _i) => {
	if (myEsVela1[_i]) {
		return myColor1;
	}
	else if (myEsVela2[_i]) {
		return myColor2;
	}
	else {
		return null;
	}
});

color_candles(myCandleColors);

// ================== Signals, usable in Scanners / Alerts / Strategy Tester ==================
register_signal(myEsVela1, 'Vela 1 Horaria');
register_signal(myEsVela2, 'Vela 2 Horaria');