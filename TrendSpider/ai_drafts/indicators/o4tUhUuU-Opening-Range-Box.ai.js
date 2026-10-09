describe_indicator('Opening Range Box', 'price');

// NOTE: this is an approximation of the original Pine Script.
// TrendSpider Custom JS has no box/line drawing objects and no
// request.security() with lookahead control, so the Opening
// Range box is reproduced using two painted lines (top/bottom)
// filled between them, active only during the post-OR window.
// Session/day grouping uses bar_at() which uses the exchange
// timezone automatically (equivalent to Pine's "America/New_York"
// session logic).

const mySessionTab = input.tab('Session');
const myOrStart = mySessionTab.text('OR Start (HHMM)', '0930');
const myOrEnd = mySessionTab.text('OR End (HHMM)', '0945');
const mySessionEnd = mySessionTab.text('Session End (HHMM)', '1600');

const myAppearanceTab = input.tab('Appearance');
const myShowMidline = myAppearanceTab.boolean('Show Midline', true);
const myFillOpacity = myAppearanceTab.number('Fill Opacity', 0.15, { min: 0, max: 1, step: 0.01 });

const myAlertsTab = input.tab('Alerts');
const myEnableUpAlert = myAlertsTab.boolean('Enable Breakout Up Signal', true);
const myEnableDownAlert = myAlertsTab.boolean('Enable Breakout Down Signal', true);

// parses "HHMM" into minutes since midnight
function myParseHHMM(_hhmmText) {
	const myHours = parseInt(_hhmmText.slice(0, 2), 10);
	const myMinutes = parseInt(_hhmmText.slice(2, 4), 10);
	return myHours * 60 + myMinutes;
}

const myOrStartMin = myParseHHMM(myOrStart);
const myOrEndMin = myParseHHMM(myOrEnd);
const mySessionEndMin = myParseHHMM(mySessionEnd);

// 1-minute data is used to compute the exact OR high/low regardless
// of the chart's current resolution, matching the Pine helper
// which always sampled the "1" timeframe.
const myOneMinData = await request.history(current.ticker, '1', { ext_session: true });
assert(!myOneMinData.error, 'Error fetching 1-minute data: ' + myOneMinData.error);

const myOrByDay = {};

for (let myIndex = 0; myIndex < myOneMinData.time.length; myIndex += 1) {
	const myTimestamp = myOneMinData.time[myIndex];
	const myDayKey = bar_at(myTimestamp).session;
	const myTimeInfo = time_of(myTimestamp);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	if (myMinutesOfDay >= myOrStartMin && myMinutesOfDay < myOrEndMin) {
		if (!myOrByDay[myDayKey]) {
			myOrByDay[myDayKey] = {
				high: myOneMinData.high[myIndex],
				low: myOneMinData.low[myIndex]
			};
		}
		else {
			myOrByDay[myDayKey].high = Math.max(myOrByDay[myDayKey].high, myOneMinData.high[myIndex]);
			myOrByDay[myDayKey].low = Math.min(myOrByDay[myDayKey].low, myOneMinData.low[myIndex]);
		}
	}
}

// main chart loop: paints box lines during the post-OR window,
// and fires breakout signals once per day per direction
const myTopLine = series_of(null);
const myBottomLine = series_of(null);
const myMidLine = series_of(null);
const myBreakUpSignal = series_of(false);
const myBreakDownSignal = series_of(false);

const myFiredUpByDay = {};
const myFiredDownByDay = {};

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDayKey = bar_at(time[myIndex]).session;
	const myTimeInfo = time_of(time[myIndex]);
	const myMinutesOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myDayOR = myOrByDay[myDayKey];
	const myIsPostOR = myMinutesOfDay >= myOrEndMin && myMinutesOfDay < mySessionEndMin;

	if (myDayOR && myIsPostOR) {
		myTopLine[myIndex] = myDayOR.high;
		myBottomLine[myIndex] = myDayOR.low;

		if (myShowMidline) {
			myMidLine[myIndex] = (myDayOR.high + myDayOR.low) / 2;
		}

		if (close[myIndex] > myDayOR.high && !myFiredUpByDay[myDayKey]) {
			myFiredUpByDay[myDayKey] = true;
			if (myEnableUpAlert) {
				myBreakUpSignal[myIndex] = true;
			}
		}

		if (close[myIndex] < myDayOR.low && !myFiredDownByDay[myDayKey]) {
			myFiredDownByDay[myDayKey] = true;
			if (myEnableDownAlert) {
				myBreakDownSignal[myIndex] = true;
			}
		}
	}
}

const myTopLinePainted = paint(myTopLine, { name: 'OR High', color: 'blue', style: 'ladder', thickness: 1 });
const myBottomLinePainted = paint(myBottomLine, { name: 'OR Low', color: 'blue', style: 'ladder', thickness: 1 });
fill(myTopLinePainted, myBottomLinePainted, 'blue', myFillOpacity, 'Opening Range');

paint(myMidLine, { name: 'OR Midline', color: 'gray', style: 'dotted', thickness: 1 });

register_signal(myBreakUpSignal, 'Breakout Above OR High');
register_signal(myBreakDownSignal, 'Breakout Below OR Low');