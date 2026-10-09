describe_indicator('NQ Range Breakout (Touch Entry)', 'price');

// ─────────────────────────────────────────────────────────────────
// NOTE: TrendSpider's time_of() always uses the EXCHANGE time zone
// of the current symbol. There is no way to pick an arbitrary user
// time zone (like "Asia/Taipei") as Pine's hour(time, tz) allows.
// This indicator therefore computes session hours/minutes using the
// chart's native exchange time zone instead of a selectable one.
// ─────────────────────────────────────────────────────────────────

const myStartHour = input.number('Range Start Hour', 11, { min: 0, max: 23 });
const myStartMinute = input.number('Range Start Minute', 43, { min: 0, max: 59 });
const myEndHour = input.number('Range End Hour', 13, { min: 0, max: 23 });
const myEndMinute = input.number('Range End Minute', 33, { min: 0, max: 59 });

const myBufferPercent = input.number('Entry Buffer (%)', 38.2, { min: 0 });
const myTakeProfitRatio = input.number('Take Profit Ratio', 0.618, { min: 0, max: 10, step: 0.01 });
const mySLAtLevel = input.number('Stop Loss Level (0..1)', 0.1, { min: 0, max: 1, step: 0.01 });
const myMaxRangePercent = input.number('Max Range (%)', 1.0, { min: 0.1, step: 0.1 });
const myMinRangePercent = input.number('Min Range (%)', 0.1, { min: 0, step: 0.05 });

const myStartTotal = myStartHour * 60 + myStartMinute;
const myEndTotal = myEndHour * 60 + myEndMinute;
const myMaxRangeRatio = myMaxRangePercent / 100;
const myMinRangeRatio = myMinRangePercent / 100;

const myCandleCount = close.length;

const myRangeHigh = series_of(null);
const myRangeLow = series_of(null);
const myLongTrigger = series_of(null);
const myShortTrigger = series_of(null);
const myLongStopLoss = series_of(null);
const myLongTakeProfit = series_of(null);
const myShortStopLoss = series_of(null);
const myShortTakeProfit = series_of(null);

const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myOversizeFlag = series_of(false);
const myUndersizeFlag = series_of(false);
const myInRangeFlag = series_of(false);
const myInTradeWindowFlag = series_of(false);

let myCurrRangeHigh = null;
let myCurrRangeLow = null;
let myAlreadyTradedToday = false;
let myPrevDayKey = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = myTimeInfo.year * 1000 + myTimeInfo.dayOfYear;

	if (myPrevDayKey !== null && myDayKey !== myPrevDayKey) {
		myCurrRangeHigh = null;
		myCurrRangeLow = null;
		myAlreadyTradedToday = false;
	}
	myPrevDayKey = myDayKey;

	const myCurrTimeTotal = myTimeInfo.hours * 60 + myTimeInfo.minutes;
	const myInRange = myCurrTimeTotal >= myStartTotal && myCurrTimeTotal < myEndTotal;
	const myInTradeWindow = myCurrTimeTotal >= myEndTotal;

	if (myInRange) {
		myCurrRangeHigh = myCurrRangeHigh === null ? high[myIndex] : Math.max(myCurrRangeHigh, high[myIndex]);
		myCurrRangeLow = myCurrRangeLow === null ? low[myIndex] : Math.min(myCurrRangeLow, low[myIndex]);
	}

	myRangeHigh[myIndex] = myCurrRangeHigh;
	myRangeLow[myIndex] = myCurrRangeLow;
	myInRangeFlag[myIndex] = myInRange;
	myInTradeWindowFlag[myIndex] = myInTradeWindow;

	let myIsOversize = false;
	let myIsUndersize = false;

	if (myCurrRangeHigh !== null) {
		const myRangePercent = (myCurrRangeHigh - myCurrRangeLow) / myCurrRangeHigh;
		myIsOversize = myRangePercent > myMaxRangeRatio;
		myIsUndersize = myRangePercent < myMinRangeRatio;
	}
	myOversizeFlag[myIndex] = myIsOversize;
	myUndersizeFlag[myIndex] = myIsUndersize;

	const myCanTrade = myInTradeWindow && myCurrRangeHigh !== null && !myAlreadyTradedToday && !myIsOversize && !myIsUndersize;

	let myLongEntryFired = false;
	let myShortEntryFired = false;

	if (myCanTrade) {
		const myRangeSize = myCurrRangeHigh - myCurrRangeLow;
		const myLongTrg = myCurrRangeHigh + (myRangeSize * (myBufferPercent / 100));
		const myShortTrg = myCurrRangeLow - (myRangeSize * (myBufferPercent / 100));
		const myLongSL = myCurrRangeLow + (myRangeSize * mySLAtLevel);
		const myShortSL = myCurrRangeHigh - (myRangeSize * mySLAtLevel);
		const myLongTP = myCurrRangeHigh + (myRangeSize * myTakeProfitRatio);
		const myShortTP = myCurrRangeLow - (myRangeSize * myTakeProfitRatio);

		myLongTrigger[myIndex] = myLongTrg;
		myShortTrigger[myIndex] = myShortTrg;
		myLongStopLoss[myIndex] = myLongSL;
		myLongTakeProfit[myIndex] = myLongTP;
		myShortStopLoss[myIndex] = myShortSL;
		myShortTakeProfit[myIndex] = myShortTP;

		// Approximation of Pine's intrabar stop-order fill: we check
		// whether the current bar's high/low touched the trigger
		// price. Long trigger is checked first (same priority as the
		// order placement order in the Pine script).
		if (high[myIndex] >= myLongTrg) {
			myLongEntryFired = true;
			myAlreadyTradedToday = true;
		}
		else if (low[myIndex] <= myShortTrg) {
			myShortEntryFired = true;
			myAlreadyTradedToday = true;
		}
	}

	myLongEntrySignal[myIndex] = myLongEntryFired;
	myShortEntrySignal[myIndex] = myShortEntryFired;
}

paint(myRangeHigh, { name: 'RangeHigh', color: '#ef5350', thickness: 1, style: 'line' });
paint(myRangeLow, { name: 'RangeLow', color: '#26a69a', thickness: 1, style: 'line' });

register_signal(myLongEntrySignal, 'Long Entry Triggered');
register_signal(myShortEntrySignal, 'Short Entry Triggered');
register_signal(myOversizeFlag, 'Range Oversize');
register_signal(myUndersizeFlag, 'Range Undersize');
register_signal(myInRangeFlag, 'In Range Window');
register_signal(myInTradeWindowFlag, 'In Trade Window');