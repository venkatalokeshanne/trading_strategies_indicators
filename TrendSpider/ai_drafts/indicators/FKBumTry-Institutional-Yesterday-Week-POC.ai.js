describe_indicator('Institutional Yesterday and Week Constant POC');

// NOTE: Pine's fastPOC() finds the "point of control" as the close price of
// the candle with the highest volume so far within a Day/Week, computed on
// Daily/Weekly request.security(). Custom JS API has no bar_index-level
// request.security with per-session reset like Pine, so this approximates
// the "POC" by scanning the CURRENT CHART's own candles (must be intraday)
// grouped by day/week, picking the close of the highest-volume candle in
// each completed session, then locking that onto the following session.

const showDaily = input.boolean('Show Yesterday POC?', true);
const colorDPOC = input.color('Yesterday POC Color', 'orange');
const showWkly = input.boolean('Show Previous Week POC?', true);
const colorWPOC = input.color('Previous Week POC Color', 'blue');
const showLabels = input.boolean('Show Text Labels?', true);

assert(!isNaN(current.resolution), 'This indicator requires an intraday chart to compute intrabar POC');

const myDayKeys = time.map(_t => bar_at(_t).session);
const myWeekKeys = time.map(_t => bar_at(_t, 'W').session);

// compute per-day and per-week POC (close of highest volume candle in session)
const myDayPOCByKey = {};
const myDayMaxVolByKey = {};
const myWeekPOCByKey = {};
const myWeekMaxVolByKey = {};

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myDayKey = myDayKeys[myIndex];
	const myWeekKey = myWeekKeys[myIndex];
	const myVol = volume[myIndex];
	const myClose = close[myIndex];

	if (myDayMaxVolByKey[myDayKey] === undefined || myVol > myDayMaxVolByKey[myDayKey]) {
		myDayMaxVolByKey[myDayKey] = myVol;
		myDayPOCByKey[myDayKey] = myClose;
	}

	if (myWeekMaxVolByKey[myWeekKey] === undefined || myVol > myWeekMaxVolByKey[myWeekKey]) {
		myWeekMaxVolByKey[myWeekKey] = myVol;
		myWeekPOCByKey[myWeekKey] = myClose;
	}
}

// walk through candles, locking the previous completed session's POC
// onto the following session's candles (constant line, non-shifting)
const myLockedYPOC = series_of(null);
const myLockedWPOC = series_of(null);

let myLastDayKey = null;
let myLastWeekKey = null;
let myCurrentYPOC = null;
let myCurrentWPOC = null;
let myPrevDayKey = null;
let myPrevWeekKey = null;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myDayKey = myDayKeys[myIndex];
	const myWeekKey = myWeekKeys[myIndex];

	if (myDayKey !== myLastDayKey) {
		if (myPrevDayKey !== null && myDayPOCByKey[myPrevDayKey] !== undefined) {
			myCurrentYPOC = myDayPOCByKey[myPrevDayKey];
		}
		myPrevDayKey = myLastDayKey !== null ? myLastDayKey : myPrevDayKey;
		myLastDayKey = myDayKey;
	}

	if (myWeekKey !== myLastWeekKey) {
		if (myPrevWeekKey !== null && myWeekPOCByKey[myPrevWeekKey] !== undefined) {
			myCurrentWPOC = myWeekPOCByKey[myPrevWeekKey];
		}
		myPrevWeekKey = myLastWeekKey !== null ? myLastWeekKey : myPrevWeekKey;
		myLastWeekKey = myWeekKey;
	}

	myLockedYPOC[myIndex] = myCurrentYPOC;
	myLockedWPOC[myIndex] = myCurrentWPOC;
}

const myYPOCLine = showDaily ? myLockedYPOC : series_of(null);
const myWPOCLine = showWkly ? myLockedWPOC : series_of(null);

const myYPOCPainted = paint(myYPOCLine, { name: 'YesterdayPOC', color: colorDPOC, style: 'ladder', thickness: 2 });
const myWPOCPainted = paint(myWPOCLine, { name: 'PreviousWeekPOC', color: colorWPOC, style: 'ladder', thickness: 2 });

// labels on the most recent point of each line, only if enabled and valid
if (showLabels && myLockedYPOC[myLockedYPOC.length - 1] !== null) {
	paint_label_at_line(myYPOCPainted, myLockedYPOC.length - 1, 'Yesterday vPOC', { color: colorDPOC });
}
if (showLabels && myLockedWPOC[myLockedWPOC.length - 1] !== null) {
	paint_label_at_line(myWPOCPainted, myLockedWPOC.length - 1, 'Prev Week vPOC', { color: colorWPOC });
}

// signals for scanning/alerts/strategy: price crossing the locked POCs
const myCrossYPOC = for_every(close, myLockedYPOC, (_c, _y, _p, _i) => {
	if (_y === null || _i === 0) return false;
	const myPrevC = close[_i - 1];
	const myPrevY = myLockedYPOC[_i - 1];
	if (myPrevY === null) return false;
	return (myPrevC - myPrevY) * (_c - _y) < 0;
});

const myCrossWPOC = for_every(close, myLockedWPOC, (_c, _w, _p, _i) => {
	if (_w === null || _i === 0) return false;
	const myPrevC = close[_i - 1];
	const myPrevW = myLockedWPOC[_i - 1];
	if (myPrevW === null) return false;
	return (myPrevC - myPrevW) * (_c - _w) < 0;
});

register_signal(myCrossYPOC, 'Price Crosses Yesterday POC');
register_signal(myCrossWPOC, 'Price Crosses Previous Week POC');