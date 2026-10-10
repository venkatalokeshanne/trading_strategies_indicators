// NOTE: TrendSpider Custom JS does not support Pine's box/line/label
// drawing primitives, custom session strings, or timeframe.in_seconds().
// This is a best-effort re-implementation using series painted with
// 'ladder' style (flat, non-interpolated), which visually reproduces the
// ORB box, PMH/PML and PDH/PDL lines appearing at session start and
// freezing until the session ends. Exact Pine bar-by-bar values should
// match, but the drawing style (boxes/lines/labels) is approximated.
describe_indicator('15min ORB plus PMH PML PDH PDL', 'price');

const myShowOrb = input.boolean('Show ORB Box', true);
const myShowPm = input.boolean('Show PMH PML', true);
const myShowPd = input.boolean('Show PDH PDL', true);
// Shortened input name to satisfy platform's input name length limit
const myDaysBack = input.number('Days back (0=all)', 5, { min: 0, max: 200 });
const myOrbMinutes = input.number('ORB Window Minutes', 15, { min: 1, max: 120 });

assert(!isNaN(current.resolution), 'Only applicable to intraday charts');

const mySessionStartMin = current.session.start.hours * 60 + current.session.start.minutes;
const mySessionEndMin = current.session.end.hours * 60 + current.session.end.minutes;
const myOrbEndMin = mySessionStartMin + myOrbMinutes;

const myHasPremarket = !!current.ext_session_premarket;
const myPmStartMin = myHasPremarket ? (current.ext_session_premarket.start.hours * 60 + current.ext_session_premarket.start.minutes) : null;
const myPmEndMin = myHasPremarket ? (current.ext_session_premarket.end.hours * 60 + current.ext_session_premarket.end.minutes) : mySessionStartMin;

const myOrbHighOut = series_of(null);
const myOrbLowOut = series_of(null);
const myPmhOut = series_of(null);
const myPmlOut = series_of(null);
const myPdhOut = series_of(null);
const myPdlOut = series_of(null);

let myDayKey = null;
let myPmHigh = null;
let myPmLow = null;
let myOrbHigh = null;
let myOrbLow = null;
let myCurHigh = null;
let myCurLow = null;
let myPdHigh = null;
let myPdLow = null;

const myNowTs = current.now;
const myDaysBackLimitSeconds = myDaysBack === 0 ? null : myDaysBack * 26 * 60 * 60;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimestamp = time[myIndex];
	const myBarInfo = bar_at(myTimestamp);
	const myKey = myBarInfo.session;
	const myTod = time_of(myTimestamp);
	const myTodMin = myTod.hours * 60 + myTod.minutes;
	const myWithinLimit = myDaysBackLimitSeconds === null ? true : (myTimestamp >= myNowTs - myDaysBackLimitSeconds);
	const myIsRth = myTodMin >= mySessionStartMin && myTodMin < mySessionEndMin;
	const myIsOrb = myTodMin >= mySessionStartMin && myTodMin < myOrbEndMin;
	const myIsPm = myHasPremarket ? (myTodMin >= myPmStartMin && myTodMin < myPmEndMin) : false;
	const myNewDay = myKey !== myDayKey;

	if (myNewDay) {
		myPdHigh = myCurHigh;
		myPdLow = myCurLow;
		myCurHigh = null;
		myCurLow = null;
		myPmHigh = null;
		myPmLow = null;
		myOrbHigh = null;
		myOrbLow = null;
		myDayKey = myKey;
	}

	if (myIsPm && myWithinLimit) {
		myPmHigh = myPmHigh === null ? high[myIndex] : Math.max(myPmHigh, high[myIndex]);
		myPmLow = myPmLow === null ? low[myIndex] : Math.min(myPmLow, low[myIndex]);
	}

	if (myIsOrb && myWithinLimit) {
		myOrbHigh = myOrbHigh === null ? high[myIndex] : Math.max(myOrbHigh, high[myIndex]);
		myOrbLow = myOrbLow === null ? low[myIndex] : Math.min(myOrbLow, low[myIndex]);
	}

	if (myIsRth) {
		myCurHigh = myCurHigh === null ? high[myIndex] : Math.max(myCurHigh, high[myIndex]);
		myCurLow = myCurLow === null ? low[myIndex] : Math.min(myCurLow, low[myIndex]);
	}

	if (myIsRth && myWithinLimit) {
		if (myShowPm) {
			myPmhOut[myIndex] = myPmHigh;
			myPmlOut[myIndex] = myPmLow;
		}
		if (myShowPd) {
			myPdhOut[myIndex] = myPdHigh;
			myPdlOut[myIndex] = myPdLow;
		}
		if (myShowOrb && !myIsOrb && myOrbHigh !== null) {
			myOrbHighOut[myIndex] = myOrbHigh;
			myOrbLowOut[myIndex] = myOrbLow;
		}
	}
}

const myOrbHighPainted = paint(myOrbHighOut, { name: 'ORB High', color: '#7E57C2', style: 'ladder', thickness: 2 });
const myOrbLowPainted = paint(myOrbLowOut, { name: 'ORB Low', color: '#7E57C2', style: 'ladder', thickness: 2 });
fill(myOrbHighPainted, myOrbLowPainted, '#7E57C2', 0.15);

paint(myPmhOut, { name: 'PMH', color: '#FFFFFF', style: 'ladder', thickness: 1 });
paint(myPmlOut, { name: 'PML', color: '#FFFFFF', style: 'ladder', thickness: 1 });
paint(myPdhOut, { name: 'PDH', color: '#FFC107', style: 'ladder', thickness: 1 });
paint(myPdlOut, { name: 'PDL', color: '#FFC107', style: 'ladder', thickness: 1 });

// Breakout signals for scanners, alerts and backtests
const myBreakOrbUp = for_every(close, myOrbHighOut, (_c, _l) => _l !== null && _c > _l);
const myBreakOrbDown = for_every(close, myOrbLowOut, (_c, _l) => _l !== null && _c < _l);
const myBreakPmhUp = for_every(close, myPmhOut, (_c, _l) => _l !== null && _c > _l);
const myBreakPmlDown = for_every(close, myPmlOut, (_c, _l) => _l !== null && _c < _l);
const myBreakPdhUp = for_every(close, myPdhOut, (_c, _l) => _l !== null && _c > _l);
const myBreakPdlDown = for_every(close, myPdlOut, (_c, _l) => _l !== null && _c < _l);

register_signal(myBreakOrbUp, 'Breakout Above ORB High');
register_signal(myBreakOrbDown, 'Breakdown Below ORB Low');
register_signal(myBreakPmhUp, 'Breakout Above PMH');
register_signal(myBreakPmlDown, 'Breakdown Below PML');
register_signal(myBreakPdhUp, 'Breakout Above PDH');
register_signal(myBreakPdlDown, 'Breakdown Below PDL');