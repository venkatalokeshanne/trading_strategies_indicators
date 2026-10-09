describe_indicator('MNQ Midpoint Retest Strategy Signals', 'price');
// ======================================================================
// This is a best-effort translation of a Pine strategy script into
// TrendSpider Custom JS. TrendSpider's Custom JS API has no built-in
// strategy engine (no strategy.entry/exit/pyramiding/qty_percent/closed
// trade P&L tracking). All of that state (position, stops, partial
// exits, loss-streak lockout) is re-implemented manually below using a
// sequential loop over candles, which is the only way to express this
// kind of path-dependent logic in this API. Exact fill/partial-exit
// P&L math (70%/30% split) is approximated for the purpose of the
// "loss streak" lockout logic only; the actual TrendSpider output is
// signals (entry conditions, range lines, breakout markers) rather
// than a full equity simulation.
// ======================================================================

// shortened input titles to satisfy the platform's input name length limit
const myRangeStartMinute = input.number('Range Start (min)', 480, { min: 0, max: 1439 });
const myRangeEndMinute = input.number('Range End (min)', 495, { min: 0, max: 1439 });
const myTradeStartMinute = input.number('Trade Start (min)', 585, { min: 0, max: 1439 });
const myTradeEndMinute = input.number('Trade End (min)', 660, { min: 0, max: 1439 });
const myLossStreakLimit = input.number('Loss Streak Limit', 2, { min: 1, max: 10 });

const myLength = close.length;
const myRHigh = series_of(null);
const myRLow = series_of(null);
const myMid = series_of(null);
const myAboveRange = series_of(null);
const myBelowRange = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const mySessionEndSignal = series_of(false);

let myCurRHigh = null;
let myCurRLow = null;
let myCurMid = null;
let myBreakoutState = 0;
let myRangeLocked = false;
let myEntry = null;
let myLossStreak = 0;
let myLockedForDay = false;
let myMovedToBE = false;
let myPositionSize = 0; // 1 long, -1 short, 0 flat
let myLongStop = null;
let myShortStop = null;
let myLongTP1 = null;
let myLongTP2 = null;
let myShortTP1 = null;
let myShortTP2 = null;
let myLastDayOfYear = null;
let myLastYear = null;
let myPrevTradeSession = false;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myMinuteOfDay = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myRangeSession = myMinuteOfDay >= myRangeStartMinute && myMinuteOfDay < myRangeEndMinute;
	const myTradeSession = myMinuteOfDay >= myTradeStartMinute && myMinuteOfDay < myTradeEndMinute;
	const myEndSession = !myTradeSession && myPrevTradeSession;
	const myNewDay = (myTimeInfo.year !== myLastYear) || (myTimeInfo.dayOfYear !== myLastDayOfYear);
	myLastYear = myTimeInfo.year;
	myLastDayOfYear = myTimeInfo.dayOfYear;

	if (myNewDay) {
		myCurRHigh = null;
		myCurRLow = null;
		myCurMid = null;
		myBreakoutState = 0;
		myRangeLocked = false;
		myEntry = null;
		myLossStreak = 0;
		myLockedForDay = false;
		myMovedToBE = false;
		myPositionSize = 0;
	}

	// range build
	if (myRangeSession && !myRangeLocked) {
		myCurRHigh = myCurRHigh === null ? high[myIndex] : Math.max(myCurRHigh, high[myIndex]);
		myCurRLow = myCurRLow === null ? low[myIndex] : Math.min(myCurRLow, low[myIndex]);
	}
	if (!myRangeSession && !myRangeLocked && myCurRHigh !== null && myCurRLow !== null) {
		myCurMid = (myCurRHigh + myCurRLow) / 2;
		myRangeLocked = true;
	}

	// force close at session end
	if (myEndSession && myPositionSize !== 0) {
		myPositionSize = 0;
		myEntry = null;
		myMovedToBE = false;
	}

	// breakout
	const myAbove = myRangeLocked && myCurRHigh !== null && close[myIndex] > myCurRHigh;
	const myBelow = myRangeLocked && myCurRLow !== null && close[myIndex] < myCurRLow;
	if (myAbove) {
		myBreakoutState = 1;
	}
	if (myBelow) {
		myBreakoutState = -1;
	}

	// manage open position (stop/TP checks) - approximate full close on stop or TP2
	if (myPositionSize > 0 && myEntry !== null) {
		if (high[myIndex] >= myLongTP1) {
			myMovedToBE = true;
		}
		const myBeStop = myMovedToBE ? myEntry : myLongStop;
		if (low[myIndex] <= myBeStop || high[myIndex] >= myLongTP2) {
			const myProfit = (high[myIndex] >= myLongTP2 ? myLongTP2 : myBeStop) - myEntry;
			if (myProfit < 0) {
				myLossStreak += 1;
			}
			else {
				myLossStreak = 0;
			}
			myPositionSize = 0;
			myEntry = null;
			myMovedToBE = false;
		}
	}
	else if (myPositionSize < 0 && myEntry !== null) {
		if (low[myIndex] <= myShortTP1) {
			myMovedToBE = true;
		}
		const myBeStop = myMovedToBE ? myEntry : myShortStop;
		if (high[myIndex] >= myBeStop || low[myIndex] <= myShortTP2) {
			const myProfit = myEntry - (low[myIndex] <= myShortTP2 ? myShortTP2 : myBeStop);
			if (myProfit < 0) {
				myLossStreak += 1;
			}
			else {
				myLossStreak = 0;
			}
			myPositionSize = 0;
			myEntry = null;
			myMovedToBE = false;
		}
	}

	if (myLossStreak >= myLossStreakLimit) {
		myLockedForDay = true;
	}

	const myCanTrade = myTradeSession && myRangeLocked && !myLockedForDay;
	const myTouchLong = myCanTrade && myBreakoutState === 1 && myCurMid !== null && low[myIndex] <= myCurMid;
	const myTouchShort = myCanTrade && myBreakoutState === -1 && myCurMid !== null && high[myIndex] >= myCurMid;
	const myFlat = myPositionSize === 0;

	if (myTouchLong && myFlat) {
		myPositionSize = 1;
		myEntry = close[myIndex];
		myMovedToBE = false;
		myLongStop = myCurRLow;
		const myRisk = myEntry - myLongStop;
		myLongTP1 = myEntry + 2 * myRisk;
		myLongTP2 = myEntry + 4 * myRisk;
		myLongEntrySignal[myIndex] = true;
	}
	else if (myTouchShort && myFlat) {
		myPositionSize = -1;
		myEntry = close[myIndex];
		myMovedToBE = false;
		myShortStop = myCurRHigh;
		const myRisk = myShortStop - myEntry;
		myShortTP1 = myEntry - 2 * myRisk;
		myShortTP2 = myEntry - 4 * myRisk;
		myShortEntrySignal[myIndex] = true;
	}

	mySessionEndSignal[myIndex] = myEndSession;
	myRHigh[myIndex] = myRangeLocked ? myCurRHigh : null;
	myRLow[myIndex] = myRangeLocked ? myCurRLow : null;
	myMid[myIndex] = myRangeLocked ? myCurMid : null;
	myAboveRange[myIndex] = myAbove ? low[myIndex] : null;
	myBelowRange[myIndex] = myBelow ? high[myIndex] : null;
	myPrevTradeSession = myTradeSession;
}

paint(myRHigh, { name: 'Range High', color: '#26A69A', style: 'line' });
paint(myRLow, { name: 'Range Low', color: '#EF5350', style: 'line' });
paint(myMid, { name: 'Mid', color: '#4DA3FF', style: 'line' });
paint(myAboveRange, { name: 'Breakout Above', style: 'labels_below', color: '#26A69A' });
paint(myBelowRange, { name: 'Breakout Below', style: 'labels_above', color: '#EF5350' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(mySessionEndSignal, 'Session End Close');