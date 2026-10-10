// Experimental conversion: TrendSpider has no native "trading session string"
// parser like Pine's input.session(). Sessions are approximated using
// start/end hour inputs (in exchange time zone, via time_of()). This is the
// closest equivalent available in the Custom JS API.
describe_indicator('HRX Prev Daily Weekly Session HL Day Open', 'price');

const myStyleTab = input.tab('Style');
const myLineThickness = myStyleTab.number('Line Thickness', 2, { min: 1, max: 5 });
// Fixed: valid paint() styles are line, column, stacked_column, dotted, ladder,
// labels_above, labels_below. "solid"/"dashed" are not supported, so we map
// to "line" and "dotted" respectively.
const myLineStyleOpt = myStyleTab.select('Line Style', 'line', ['line', 'dotted']);

const myShowTab = input.tab('Show');
const myShowWeekly = myShowTab.boolean('Show Previous Week HL', true);
const myShowDaily = myShowTab.boolean('Show Yesterday HL', true);
const myShowAsia = myShowTab.boolean('Show Asia Session', true);
const myShowLondon = myShowTab.boolean('Show London Session', true);
const myShowNY = myShowTab.boolean('Show NY Session', true);
const myShowDayOpen = myShowTab.boolean('Show Day Open Line', true);

const mySessionTab = input.tab('Sessions');
const myAsiaRow = mySessionTab.row();
const myAsiaStartHour = myAsiaRow.number('Asia Start Hour', 19, { min: 0, max: 23 });
const myAsiaEndHour = myAsiaRow.number('Asia End Hour', 1, { min: 0, max: 23 });

const myLondonRow = mySessionTab.row();
const myLondonStartHour = myLondonRow.number('London Start Hour', 3, { min: 0, max: 23 });
const myLondonEndHour = myLondonRow.number('London End Hour', 6, { min: 0, max: 23 });

const myNYRow = mySessionTab.row();
const myNYStartHour = myNYRow.number('NY Start Hour', 8, { min: 0, max: 23 });
const myNYEndHour = myNYRow.number('NY End Hour', 12, { min: 0, max: 23 });

// ---------------- Previous Week High/Low ----------------
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

const myPrevWeekHigh = series_of(null);
const myPrevWeekLow = series_of(null);
for (let myI = 1; myI < myWeeklyData.time.length; myI += 1) {
	myPrevWeekHigh[myI] = myWeeklyData.high[myI - 1];
	myPrevWeekLow[myI] = myWeeklyData.low[myI - 1];
}

const myPrevWeekHighLanded = land_points_onto_series(myWeeklyData.time, myPrevWeekHigh, time, 'ge');
const myPrevWeekLowLanded = land_points_onto_series(myWeeklyData.time, myPrevWeekLow, time, 'ge');
const myPrevWeekHighSeries = interpolate_sparse_series(myPrevWeekHighLanded, 'constant');
const myPrevWeekLowSeries = interpolate_sparse_series(myPrevWeekLowLanded, 'constant');

// ---------------- Previous Day High/Low ----------------
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myPrevDayHigh = series_of(null);
const myPrevDayLow = series_of(null);
const myDayOpenRaw = series_of(null);
for (let myI = 1; myI < myDailyData.time.length; myI += 1) {
	myPrevDayHigh[myI] = myDailyData.high[myI - 1];
	myPrevDayLow[myI] = myDailyData.low[myI - 1];
	myDayOpenRaw[myI] = myDailyData.open[myI];
}

const myPrevDayHighLanded = land_points_onto_series(myDailyData.time, myPrevDayHigh, time, 'ge');
const myPrevDayLowLanded = land_points_onto_series(myDailyData.time, myPrevDayLow, time, 'ge');
const myDayOpenLanded = land_points_onto_series(myDailyData.time, myDayOpenRaw, time, 'ge');
const myPrevDayHighSeries = interpolate_sparse_series(myPrevDayHighLanded, 'constant');
const myPrevDayLowSeries = interpolate_sparse_series(myPrevDayLowLanded, 'constant');
const myDayOpenSeries = interpolate_sparse_series(myDayOpenLanded, 'constant');

// ---------------- Session High/Low computation ----------------
// Returns { high: series, low: series } containing the running (then frozen
// after session end) High/Low of a given hour-range session, resetting every
// new day. Handles sessions that wrap past midnight (start > end).
function computeSessionRange(_startHour, _endHour) {
	const myHighOut = series_of(null);
	const myLowOut = series_of(null);
	let myCurrentHigh = null;
	let myCurrentLow = null;
	let myLastDay = null;
	let myWasInSession = false;

	for (let myI = 0; myI < time.length; myI += 1) {
		const myTimeInfo = time_of(time[myI]);
		const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;

		if (myDayKey !== myLastDay) {
			myCurrentHigh = null;
			myCurrentLow = null;
			myLastDay = myDayKey;
			myWasInSession = false;
		}

		let myInSession = false;
		if (_startHour <= _endHour) {
			myInSession = myTimeInfo.hours >= _startHour && myTimeInfo.hours < _endHour;
		}
		else {
			myInSession = myTimeInfo.hours >= _startHour || myTimeInfo.hours < _endHour;
		}

		if (myInSession) {
			if (myCurrentHigh === null || high[myI] > myCurrentHigh) {
				myCurrentHigh = high[myI];
			}
			if (myCurrentLow === null || low[myI] < myCurrentLow) {
				myCurrentLow = low[myI];
			}
			myWasInSession = true;
		}

		if (myWasInSession) {
			myHighOut[myI] = myCurrentHigh;
			myLowOut[myI] = myCurrentLow;
		}
	}

	return { high: myHighOut, low: myLowOut };
}

const myAsiaRange = computeSessionRange(myAsiaStartHour, myAsiaEndHour);
const myLondonRange = computeSessionRange(myLondonStartHour, myLondonEndHour);
const myNYRange = computeSessionRange(myNYStartHour, myNYEndHour);

// ---------------- Painting ----------------
const myLineStyleToUse = myLineStyleOpt;

paint(myShowWeekly ? myPrevWeekHighSeries : constants.empty_series, { name: 'WeeklyHigh', color: 'purple', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowWeekly ? myPrevWeekLowSeries : constants.empty_series, { name: 'WeeklyLow', color: 'orange', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowDaily ? myPrevDayHighSeries : constants.empty_series, { name: 'DailyHigh', color: 'green', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowDaily ? myPrevDayLowSeries : constants.empty_series, { name: 'DailyLow', color: 'red', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowDayOpen ? myDayOpenSeries : constants.empty_series, { name: 'DayOpen', color: 'yellow', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowAsia ? myAsiaRange.high : constants.empty_series, { name: 'AsiaHigh', color: 'teal', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowAsia ? myAsiaRange.low : constants.empty_series, { name: 'AsiaLow', color: 'orange', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowLondon ? myLondonRange.high : constants.empty_series, { name: 'LondonHigh', color: 'blue', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowLondon ? myLondonRange.low : constants.empty_series, { name: 'LondonLow', color: 'red', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowNY ? myNYRange.high : constants.empty_series, { name: 'NYHigh', color: 'green', thickness: myLineThickness, style: myLineStyleToUse });
paint(myShowNY ? myNYRange.low : constants.empty_series, { name: 'NYLow', color: 'purple', thickness: myLineThickness, style: myLineStyleToUse });

// ---------------- Scanner / Strategy Signals ----------------
const mySignalCrossAbovePrevDayHigh = for_every(close, myPrevDayHighSeries, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalCrossAbovePrevDayHigh, 'Close Above Prev Day High');

const mySignalCrossBelowPrevDayLow = for_every(close, myPrevDayLowSeries, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalCrossBelowPrevDayLow, 'Close Below Prev Day Low');

const mySignalCrossAbovePrevWeekHigh = for_every(close, myPrevWeekHighSeries, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalCrossAbovePrevWeekHigh, 'Close Above Prev Week High');

const mySignalCrossBelowPrevWeekLow = for_every(close, myPrevWeekLowSeries, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalCrossBelowPrevWeekLow, 'Close Below Prev Week Low');

const mySignalAboveDayOpen = for_every(close, myDayOpenSeries, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalAboveDayOpen, 'Close Above Day Open');

const mySignalBelowDayOpen = for_every(close, myDayOpenSeries, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalBelowDayOpen, 'Close Below Day Open');

const mySignalAboveAsiaHigh = for_every(close, myAsiaRange.high, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalAboveAsiaHigh, 'Close Above Asia High');

const mySignalBelowAsiaLow = for_every(close, myAsiaRange.low, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalBelowAsiaLow, 'Close Below Asia Low');

const mySignalAboveLondonHigh = for_every(close, myLondonRange.high, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalAboveLondonHigh, 'Close Above London High');

const mySignalBelowLondonLow = for_every(close, myLondonRange.low, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalBelowLondonLow, 'Close Below London Low');

const mySignalAboveNYHigh = for_every(close, myNYRange.high, (_c, _l) => _l != null && _c > _l);
register_signal(mySignalAboveNYHigh, 'Close Above NY High');

const mySignalBelowNYLow = for_every(close, myNYRange.low, (_c, _l) => _l != null && _c < _l);
register_signal(mySignalBelowNYLow, 'Close Below NY Low');