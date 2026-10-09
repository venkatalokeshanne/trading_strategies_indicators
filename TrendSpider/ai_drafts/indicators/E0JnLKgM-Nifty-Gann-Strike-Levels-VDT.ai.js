describe_indicator('Nifty Gann and Strike Levels', 'price');

// Maximum levels supported above/below the anchor price. The original
// Pine script lets the user pick an arbitrary level count, which would
// make the number of paint() calls dynamic. TrendSpider requires a
// constant number of paint() calls on every run, so we cap the number
// of levels at a fixed maximum and simply leave the unused slots blank.
const MAX_LEVELS = 10;

// --- GANN LEVELS ---
const gannTab = input.tab('Gann Levels');
const myShowGann = gannTab.boolean('Show Gann Levels', true);
const myGannLevels = gannTab.number('Levels Above / Below', 5, { min: 1, max: MAX_LEVELS });

// --- 100 INTERVAL LEVELS ---
const intervalTab = input.tab('100 Interval Levels');
const myShowInterval = intervalTab.boolean('Show 100-Interval Levels', true);
const myIntervalLevels = intervalTab.number('Levels Above / Below', 5, { min: 1, max: MAX_LEVELS });

// --- PREVIOUS DAY LEVELS ---
const prevTab = input.tab('Previous Day Levels');
const myShowPrev = prevTab.boolean('Show Prev Day High/Low', true);

// Fetch daily data to compute previous completed day's High/Low.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

// Determine if the last daily bar belongs to the same calendar day as the
// last candle on the current chart. If so, that daily bar is "today" (in
// progress) and the previous day's High/Low is one bar before it.
let myPrevHigh = null;
let myPrevLow = null;

if (myDailyData.time.length > 0) {
	const myLastChartDay = bar_at(time[time.length - 1]).session;
	const myLastDailyDay = bar_at(myDailyData.time[myDailyData.time.length - 1]).session;
	const myIsSameDay = myLastChartDay === myLastDailyDay;
	const myPrevIndex = myIsSameDay ? myDailyData.time.length - 2 : myDailyData.time.length - 1;

	if (myPrevIndex >= 0) {
		myPrevHigh = myDailyData.high[myPrevIndex];
		myPrevLow = myDailyData.low[myPrevIndex];
	}
}

// Anchor price used for Gann and Interval level calculations (last close).
const myCloseLast = close[close.length - 1];

// --- Gann levels (based on Square Root method, step of 0.125) ---
const myAnchorGannSqrt = Math.sqrt(myCloseLast);
const myBaseStep = Math.round(myAnchorGannSqrt / 0.125);

// NOTE: each paint() call must have a unique, static (hardcoded) name.
// Since every slot in this fixed-size loop corresponds to a fixed,
// enumerable level ("Gann Level 1" .. "Gann Level 21"), it's safe (and
// required) to bake the loop index into the literal name below.
for (let myIndex = -MAX_LEVELS; myIndex <= MAX_LEVELS; myIndex += 1) {
	const myWithinRange = Math.abs(myIndex) <= myGannLevels;
	const myLevelValue = myShowGann && myWithinRange
		? Math.pow((myBaseStep + myIndex) * 0.125, 2)
		: null;

	paint(horizontal_line(myLevelValue), {
		name: `Gann Level ${myIndex + MAX_LEVELS + 1}`,
		color: '#313131',
		thickness: 2,
		style: 'line'
	});
}

// --- 100 Interval (Strike) levels ---
const myBaseInterval = Math.round(myCloseLast / 100) * 100;

for (let myIndex = -MAX_LEVELS; myIndex <= MAX_LEVELS; myIndex += 1) {
	const myWithinRange = Math.abs(myIndex) <= myIntervalLevels;
	const myLevelValue = myShowInterval && myWithinRange
		? myBaseInterval + (myIndex * 100)
		: null;

	paint(horizontal_line(myLevelValue), {
		name: `Interval Level ${myIndex + MAX_LEVELS + 1}`,
		color: '#e0a94e',
		thickness: 2,
		style: 'dotted'
	});
}

// --- Previous Day High/Low ---
const myPrevHighValue = (myShowPrev && myPrevHigh !== null) ? myPrevHigh : null;
const myPrevLowValue = (myShowPrev && myPrevLow !== null) ? myPrevLow : null;

const myPrevHighLine = paint(horizontal_line(myPrevHighValue), {
	name: 'Previous Day High',
	color: '#ff5252',
	thickness: 2,
	style: 'dotted'
});

const myPrevLowLine = paint(horizontal_line(myPrevLowValue), {
	name: 'Previous Day Low',
	color: '#4caf50',
	thickness: 2,
	style: 'dotted'
});

// --- Scanner / Strategy signals ---
// Close crossing above/below the previous day's High and Low.
const myCrossAbovePrevHigh = for_every(close, (_c, _prev, _i) => {
	if (myPrevHighValue === null || _i === 0) return false;
	return close[_i - 1] <= myPrevHighValue && close[_i] > myPrevHighValue;
});

const myCrossBelowPrevLow = for_every(close, (_c, _prev, _i) => {
	if (myPrevLowValue === null || _i === 0) return false;
	return close[_i - 1] >= myPrevLowValue && close[_i] < myPrevLowValue;
});

// Close crossing the nearest 100-Interval level (ATM strike) and the
// nearest Gann base level, useful for Gann/Strike-based entries.
const myNearestIntervalLevel = myBaseInterval;
const myNearestGannLevel = Math.pow(myBaseStep * 0.125, 2);

const myCrossIntervalLevel = for_every(close, (_c, _prev, _i) => {
	if (_i === 0) return false;
	return (close[_i - 1] - myNearestIntervalLevel) * (close[_i] - myNearestIntervalLevel) < 0;
});

const myCrossGannLevel = for_every(close, (_c, _prev, _i) => {
	if (_i === 0) return false;
	return (close[_i - 1] - myNearestGannLevel) * (close[_i] - myNearestGannLevel) < 0;
});

register_signal(myCrossAbovePrevHigh, 'Cross Above Previous Day High');
register_signal(myCrossBelowPrevLow, 'Cross Below Previous Day Low');
register_signal(myCrossIntervalLevel, 'Cross Nearest Interval Level');
register_signal(myCrossGannLevel, 'Cross Nearest Gann Level');