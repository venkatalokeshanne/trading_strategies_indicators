describe_indicator('Andrew Malek Trading - Clean ORB', 'price');

// NOTE: TrendSpider Custom JS does not support Pine's time()/session string
// matching or custom timezones. We approximate sessions using start/end
// hour:minute inputs evaluated against the exchange's own timezone (as
// returned by time_of()). The "Session Timezone" selector from the Pine
// script cannot be reproduced.

const myOrbTab = input.tab('ORB Settings');

const myOrbRow = myOrbTab.row();
const myOrbStartHour = myOrbRow.number('ORB Start Hour', 9, { min: 0, max: 23 });
const myOrbStartMinute = myOrbRow.number('ORB Start Min', 30, { min: 0, max: 59 });

const myOrbEndRow = myOrbTab.row();
const myOrbEndHour = myOrbEndRow.number('ORB End Hour', 9, { min: 0, max: 23 });
const myOrbEndMinute = myOrbEndRow.number('ORB End Min', 45, { min: 0, max: 59 });

const myDisplayRow = myOrbTab.row();
const myDisplayStartHour = myDisplayRow.number('Display Start Hour', 9, { min: 0, max: 23 });
const myDisplayStartMinute = myDisplayRow.number('Display Start Min', 30, { min: 0, max: 59 });

const myDisplayEndRow = myOrbTab.row();
const myDisplayEndHour = myDisplayEndRow.number('Display End Hour', 16, { min: 0, max: 23 });
const myDisplayEndMinute = myDisplayEndRow.number('Display End Min', 0, { min: 0, max: 59 });

const myDisplayTab = input.tab('Display');
const myShowHigh = myDisplayTab.boolean('Show ORB High', true);
const myShowLow = myDisplayTab.boolean('Show ORB Low', true);
const myShowMidline = myDisplayTab.boolean('Show ORB Midline', true);
const myShowLabels = myDisplayTab.boolean('Show Labels', false);
const myShowFill = myDisplayTab.boolean('Fill ORB Range', false);

const myOrbStartMinOfDay = myOrbStartHour * 60 + myOrbStartMinute;
const myOrbEndMinOfDay = myOrbEndHour * 60 + myOrbEndMinute;
const myDisplayStartMinOfDay = myDisplayStartHour * 60 + myDisplayStartMinute;
const myDisplayEndMinOfDay = myDisplayEndHour * 60 + myDisplayEndMinute;

const myBarCount = close.length;

const myInOrb = series_of(false);
const myInDisplay = series_of(false);

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	myInOrb[myIndex] = myMinuteOfDay >= myOrbStartMinOfDay && myMinuteOfDay < myOrbEndMinOfDay;
	myInDisplay[myIndex] = myMinuteOfDay >= myDisplayStartMinOfDay && myMinuteOfDay < myDisplayEndMinOfDay;
}

const myOrbHigh = series_of(null);
const myOrbLow = series_of(null);
const myOrbStartFlag = series_of(false);

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myPrevInOrb = myIndex > 0 ? myInOrb[myIndex - 1] : false;
	const myIsOrbStart = myInOrb[myIndex] && !myPrevInOrb;
	myOrbStartFlag[myIndex] = myIsOrbStart;

	if (myIsOrbStart) {
		myOrbHigh[myIndex] = high[myIndex];
		myOrbLow[myIndex] = low[myIndex];
	}
	else if (myInOrb[myIndex]) {
		const myPrevHigh = myIndex > 0 ? myOrbHigh[myIndex - 1] : null;
		const myPrevLow = myIndex > 0 ? myOrbLow[myIndex - 1] : null;
		myOrbHigh[myIndex] = myPrevHigh === null ? high[myIndex] : Math.max(myPrevHigh, high[myIndex]);
		myOrbLow[myIndex] = myPrevLow === null ? low[myIndex] : Math.min(myPrevLow, low[myIndex]);
	}
	else {
		myOrbHigh[myIndex] = myIndex > 0 ? myOrbHigh[myIndex - 1] : null;
		myOrbLow[myIndex] = myIndex > 0 ? myOrbLow[myIndex - 1] : null;
	}
}

const myOrbMid = series_of(null);
const myDisplayHigh = series_of(null);
const myDisplayLow = series_of(null);
const myDisplayMid = series_of(null);
const myLabelMarks = series_of(null);

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	const myHasRange = myOrbHigh[myIndex] !== null && myOrbLow[myIndex] !== null;
	myOrbMid[myIndex] = myHasRange ? (myOrbHigh[myIndex] + myOrbLow[myIndex]) / 2 : null;

	myDisplayHigh[myIndex] = myInDisplay[myIndex] ? myOrbHigh[myIndex] : null;
	myDisplayLow[myIndex] = myInDisplay[myIndex] ? myOrbLow[myIndex] : null;
	myDisplayMid[myIndex] = myInDisplay[myIndex] ? myOrbMid[myIndex] : null;

	myLabelMarks[myIndex] = (myShowLabels && myOrbStartFlag[myIndex]) ? constants.icons.flag : null;
}

const myHighLine = paint(myShowHigh ? myDisplayHigh : constants.empty_series, { name: 'ORBHigh', color: '#2ca599', thickness: 2, style: 'line' });
const myLowLine = paint(myShowLow ? myDisplayLow : constants.empty_series, { name: 'ORBLow', color: '#ee5451', thickness: 2, style: 'line' });
paint(myShowMidline ? myDisplayMid : constants.empty_series, { name: 'ORBMidline', color: 'gray', thickness: 1, style: 'line' });

paint(myLabelMarks, { name: 'ORBStartLabel', style: 'labels_above', color: 'white' });

if (myShowFill) {
	fill(myHighLine, myLowLine, 'gray', 0.1);
}
else {
	fill(myHighLine, myLowLine, 'gray', 0);
}

// Scanner/alert friendly breakout signals
const myBreakoutUp = for_every(close, myDisplayHigh, (_c, _h) => _h !== null && _c > _h);
const myBreakoutDown = for_every(close, myDisplayLow, (_c, _l) => _l !== null && _c < _l);

register_signal(myBreakoutUp, 'ORB Breakout Up');
register_signal(myBreakoutDown, 'ORB Breakout Down');
register_signal(myOrbStartFlag, 'ORB Start');