describe_indicator('Simple ORB (Opening Range Breakout)', 'price');

// NOTE: TrendSpider does not have a native "session string" input like
// Pine's input.session(). We approximate it with a text input in the
// "HHMM-HHMM" format (default "0930-0945"), parsed once at the top.
// Session time is interpreted in the exchange's local time zone (the
// same time zone used internally by time_of()), which for US equities
// is America/New_York — matching the Pine script's hardcoded timezone.

const myOrbSessionText = input.text('ORB Session (HHMM-HHMM)', '0930-0945');
const myShowPreviousDays = input.boolean('Show Previous Days', true);
const myLineWidth = input.number('Line Width', 2, { min: 1, max: 5 });

const mySessionParts = myOrbSessionText.split('-');
assert(mySessionParts.length === 2, 'ORB Session must be in HHMM-HHMM format');

const myStartMinutesOfDay = parseInt(mySessionParts[0].slice(0, 2), 10) * 60 + parseInt(mySessionParts[0].slice(2, 4), 10);
const myEndMinutesOfDay = parseInt(mySessionParts[1].slice(0, 2), 10) * 60 + parseInt(mySessionParts[1].slice(2, 4), 10);

const myOrbHighSeries = series_of(null);
const myOrbLowSeries = series_of(null);

let myCurrentHigh = null;
let myCurrentLow = null;
let myLastDayKey = null;
let myLastCandleDayKey = null;

// Determine the day key of the very last candle, so we know which day
// is "current" (relevant to the "Show Previous Days" toggle).
if (time.length > 0) {
	const myLastTimeInfo = time_of(time[time.length - 1]);
	myLastCandleDayKey = myLastTimeInfo.year * 1000 + myLastTimeInfo.dayOfYear;
}

for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	const myTimeInfo = time_of(time[myCandleIndex]);
	const myDayKey = myTimeInfo.year * 1000 + myTimeInfo.dayOfYear;
	const myMinutesNow = myTimeInfo.hours * 60 + myTimeInfo.minutes;

	if (myDayKey !== myLastDayKey) {
		// New trading day started, reset the ORB range builder
		myCurrentHigh = null;
		myCurrentLow = null;
		myLastDayKey = myDayKey;
	}

	const myInOrb = myMinutesNow >= myStartMinutesOfDay && myMinutesNow < myEndMinutesOfDay;

	if (myInOrb) {
		myCurrentHigh = myCurrentHigh === null ? high[myCandleIndex] : Math.max(myCurrentHigh, high[myCandleIndex]);
		myCurrentLow = myCurrentLow === null ? low[myCandleIndex] : Math.min(myCurrentLow, low[myCandleIndex]);
	}

	// Once the ORB range has started for the day, the lines stay frozen
	// at their final value for the rest of that day (mimics extend.right)
	const myIsCurrentDay = myDayKey === myLastCandleDayKey;
	const myShouldShow = myIsCurrentDay || myShowPreviousDays;

	myOrbHighSeries[myCandleIndex] = myShouldShow ? myCurrentHigh : null;
	myOrbLowSeries[myCandleIndex] = myShouldShow ? myCurrentLow : null;
}

const myOrbHighLine = paint(myOrbHighSeries, { name: 'ORB High', color: 'green', thickness: myLineWidth, style: 'ladder' });
const myOrbLowLine = paint(myOrbLowSeries, { name: 'ORB Low', color: 'red', thickness: myLineWidth, style: 'ladder' });

// Breakout signals: close crossing above ORB High / below ORB Low,
// usable in Scanners, Alerts and the Strategy Tester.
const myPrevClose = shift(close, 1);
const myPrevOrbHigh = shift(myOrbHighSeries, 1);
const myPrevOrbLow = shift(myOrbLowSeries, 1);

const myBreakoutAboveHigh = for_every(close, myPrevClose, myOrbHighSeries, myPrevOrbHigh, (_c, _pc, _h, _ph) => {
	return _h !== null && _ph !== null && _pc <= _ph && _c > _h;
});

const myBreakoutBelowLow = for_every(close, myPrevClose, myOrbLowSeries, myPrevOrbLow, (_c, _pc, _l, _pl) => {
	return _l !== null && _pl !== null && _pc >= _pl && _c < _l;
});

register_signal(myBreakoutAboveHigh, 'ORB High Breakout');
register_signal(myBreakoutBelowLow, 'ORB Low Breakout');