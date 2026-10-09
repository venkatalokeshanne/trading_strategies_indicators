describe_indicator('ORB 15m Range Breakout', 'price');

assert(!isNaN(current.resolution), 'This indicator only works on intraday time frames');

const myMoment = library('moment-timezone');

// ─── INPUTS ───
const mySessionTab = input.tab('Session Settings');
const mySessionWindow = mySessionTab.text('NY Opening Window (HHMM-HHMM)', '0930-0945');
const myCloseTimeStr = mySessionTab.text('NY Session Close Time (HHMM)', '1600');

const myStyleTab = input.tab('Display Style Settings');
const myLineStyleRow = myStyleTab.row();
const myLineStyle = myLineStyleRow.select('Line Style', 'Solid', ['Solid', 'Dashed']);
const myLineWidth = myLineStyleRow.number('Line Width', 2, { min: 1, max: 5 });
const myHiColor = myStyleTab.color('15m High Line Color', 'green');
const myLoColor = myStyleTab.color('15m Low Line Color', 'red');
const myShowShapes = myStyleTab.boolean('Show Breakout Triangles', true);

// ─── PARSE SESSION WINDOW / CLOSE TIME ───
const mySessionParts = mySessionWindow.split('-');
const mySessionStartHour = parseInt(mySessionParts[0].substring(0, 2), 10);
const mySessionStartMin = parseInt(mySessionParts[0].substring(2, 4), 10);
const mySessionEndHour = parseInt(mySessionParts[1].substring(0, 2), 10);
const mySessionEndMin = parseInt(mySessionParts[1].substring(2, 4), 10);
const myCloseHour = parseInt(myCloseTimeStr.substring(0, 2), 10);
const myCloseMin = parseInt(myCloseTimeStr.substring(2, 4), 10);

const mySessionStartTotal = mySessionStartHour * 60 + mySessionStartMin;
const mySessionEndTotal = mySessionEndHour * 60 + mySessionEndMin;
const myCloseTotal = myCloseHour * 60 + myCloseMin;

// ─── CONVERT TIMESTAMPS TO NY LOCAL MINUTES-OF-DAY ───
const myNyMinutesOfDay = time.map(_t => {
	const myM = myMoment.unix(_t).tz('America/New_York');
	return myM.hours() * 60 + myM.minutes();
});

const myInSession = myNyMinutesOfDay.map(_m => _m >= mySessionStartTotal && _m < mySessionEndTotal);
const myIsPastClose = myNyMinutesOfDay.map(_m => _m >= myCloseTotal);

// ─── MAIN TRACKING LOOP (sequential state, cannot be vectorized) ───
const myStableHighSeries = series_of(null);
const myStableLowSeries = series_of(null);
const myBreakUpSeries = series_of(false);
const myBreakDownSeries = series_of(false);

let myCurHigh = null;
let myCurLow = null;
let myCurStableHigh = null;
let myCurStableLow = null;
let myHighBroken = false;
let myLowBroken = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevInSession = myIndex > 0 ? myInSession[myIndex - 1] : false;
	const mySessionStartFlag = myInSession[myIndex] && !myPrevInSession;
	const mySessionEndFlag = !myInSession[myIndex] && myPrevInSession;

	if (mySessionStartFlag) {
		myCurHigh = high[myIndex];
		myCurLow = low[myIndex];
		myHighBroken = false;
		myLowBroken = false;
	}
	else if (myInSession[myIndex]) {
		myCurHigh = Math.max(myCurHigh, high[myIndex]);
		myCurLow = Math.min(myCurLow, low[myIndex]);
	}

	if (mySessionEndFlag) {
		myCurStableHigh = myCurHigh;
		myCurStableLow = myCurLow;
	}

	const myShowStable = !myInSession[myIndex] && myCurStableHigh != null && !myIsPastClose[myIndex];
	myStableHighSeries[myIndex] = myShowStable ? myCurStableHigh : null;
	myStableLowSeries[myIndex] = myShowStable ? myCurStableLow : null;

	const myBreakUp = !myInSession[myIndex] && !myIsPastClose[myIndex] && myCurStableHigh != null && !myHighBroken && close[myIndex] > myCurStableHigh;
	const myBreakDown = !myInSession[myIndex] && !myIsPastClose[myIndex] && myCurStableLow != null && !myLowBroken && close[myIndex] < myCurStableLow;

	if (myBreakUp) {
		myHighBroken = true;
	}
	if (myBreakDown) {
		myLowBroken = true;
	}

	myBreakUpSeries[myIndex] = myBreakUp;
	myBreakDownSeries[myIndex] = myBreakDown;
}

// ─── PAINTING ───
const myLineStyleResolved = myLineStyle === 'Solid' ? 'ladder' : 'dotted';

paint(myStableHighSeries, { name: 'Range High', color: myHiColor, thickness: myLineWidth, style: myLineStyleResolved });
paint(myStableLowSeries, { name: 'Range Low', color: myLoColor, thickness: myLineWidth, style: myLineStyleResolved });

const myBreakUpShapes = myBreakUpSeries.map((_v, _i) => (myShowShapes && _v) ? low[_i] : null);
const myBreakDownShapes = myBreakDownSeries.map((_v, _i) => (myShowShapes && _v) ? high[_i] : null);

paint(myBreakUpShapes, { name: 'Bullish Break', style: 'labels_below', color: 'green' });
paint(myBreakDownShapes, { name: 'Bearish Break', style: 'labels_above', color: 'red' });

// ─── SIGNALS FOR SCANNER / STRATEGY / ALERTS ───
register_signal(myBreakUpSeries, 'Bullish Breakout');
register_signal(myBreakDownSeries, 'Bearish Breakout');