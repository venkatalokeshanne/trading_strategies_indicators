describe_indicator('Session Highlight and Monday Line', 'price');
// EXPERIMENTAL NOTE: TrendSpider's Custom JS API has no bgcolor()
// equivalent and no true timezone-aware time() function like Pine
// Script. This indicator approximates the original Pine logic:
// - Session highlighting is approximated using color_candles()
//   (candle body coloring) instead of a background fill.
// - Timezone handling is approximated with a manual UTC hour
//   offset input, since time_of() only returns values in the
//   exchange's own timezone, not an arbitrary selectable one.
// - The Monday vertical line is approximated with a short
//   high-to-low segment at the Monday bar (TrendSpider's line()
//   only extends to the right, not both directions like Pine's
//   extend.both).
// Values and exact bar alignment may differ slightly from the
// original Pine script because of these platform limitations.

const myTab = input.tab('Session');
const mySessionStartHour = myTab.number('Session Start Hour', 17, { min: 0, max: 23 });
const mySessionEndHour = myTab.number('Session End Hour', 22, { min: 0, max: 23 });
// Shortened input name to satisfy platform's input name length limit
const myTzOffsetHours = myTab.number('Timezone Offset (hrs)', 0, { min: -12, max: 12 });

const myLineTab = input.tab('Monday Line');
const myLineStyle = myLineTab.select('Line Style', 'dashed', ['solid', 'dashed', 'dotted']);

// Compute adjusted hour per candle (approximating timezone shift)
const myAdjustedHours = time.map(_t => {
	const myInfo = time_of(_t);
	let myHour = myInfo.hours + myTzOffsetHours;
	myHour = ((myHour % 24) + 24) % 24;
	return myHour;
});

// In-session flag, supports sessions crossing midnight
const myInSession = myAdjustedHours.map(_h => {
	if (mySessionStartHour <= mySessionEndHour) {
		return _h >= mySessionStartHour && _h < mySessionEndHour;
	}
	else {
		return _h >= mySessionStartHour || _h < mySessionEndHour;
	}
});

// Approximate session highlight via candle coloring
const myCandleColors = myInSession.map(_in => _in ? 'rgba(41,98,255,0.15)' : null);
color_candles(myCandleColors);

// Day of week per candle (ISO: 1 = Monday ... 7 = Sunday)
const myDayOfWeek = time.map(_t => time_of(_t).dayOfWeek);

// Detect first Monday bar of the week
const myIsMondayStart = series_of(false);
for (let myIndex = 1; myIndex < time.length; myIndex += 1) {
	myIsMondayStart[myIndex] = (myDayOfWeek[myIndex] === 1) && (myDayOfWeek[myIndex - 1] !== 1);
}

// Build a vertical-ish segment (high to low) at each Monday start bar
const myMondayLineHigh = series_of(null);
const myMondayLineLow = series_of(null);
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	if (myIsMondayStart[myIndex]) {
		myMondayLineHigh[myIndex] = high[myIndex];
		myMondayLineLow[myIndex] = low[myIndex];
	}
}

const myLineStyleMap = {
	solid: 'line',
	dashed: 'dotted',
	dotted: 'dotted'
};

fill(
	paint(myMondayLineHigh, { name: 'MondayLineHigh', color: 'red', style: myLineStyleMap[myLineStyle] }),
	paint(myMondayLineLow, { name: 'MondayLineLow', color: 'red', style: myLineStyleMap[myLineStyle] }),
	'red',
	0.0
);

// Signals for use in Scanners, Alerts, Strategy Tester
register_signal(myInSession, 'In Session');
register_signal(myIsMondayStart, 'Monday Start');