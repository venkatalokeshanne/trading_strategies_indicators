describe_indicator('Liquidity Sweep Range 5-9 PRO', 'price');
// NOTE: This is a partial, approximate port. The TradingView script
// provided is incomplete (it is cut off mid-logic, after the
// "if isNewDay" block, before range building, sweep detection,
// confirmation and signal logic are even written). I cannot
// reproduce logic that was never given to me. What follows is my
// best-effort reconstruction of what the script seems to intend:
// build a High/Low range over a NY session window (default 05:00-09:00),
// then detect a liquidity sweep (wick piercing the range high or low)
// after the range window closes, and flag a directional bias.
// Please treat this as an experimental approximation, not an exact
// port, since the exact confirmation/entry rules were not provided.

const myStartHour = input.number('Range Start Hour (NY)', 5, { min: 0, max: 23 });
const myEndHour = input.number('Range End Hour (NY)', 9, { min: 0, max: 23 });
assert(!isNaN(current.resolution), "This indicator is designed for intraday charts");

// NY session hours for each candle. We cannot use `new Date()` in this
// engine, so we derive hour-of-day using time_of(), which returns
// hour/day info in exchange timezone (approximation of NY time for
// US-listed symbols).
const myTimeInfo = time.map(_t => time_of(_t));
const myDayKey = myTimeInfo.map(_info => _info.year * 10000 + _info.month * 100 + _info.dayOfMonth);

const myRangeHigh = series_of(null);
const myRangeLow = series_of(null);
const mySweepDir = series_of(0);

let myCurRangeHigh = null;
let myCurRangeLow = null;
let myCurDay = null;
let myRangeReady = false;
let myCurSweepDir = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myHour = myTimeInfo[myIndex].hours;
	const myIsNewDay = myDayKey[myIndex] !== myCurDay;

	if (myIsNewDay) {
		myCurDay = myDayKey[myIndex];
		myCurRangeHigh = null;
		myCurRangeLow = null;
		myRangeReady = false;
		myCurSweepDir = 0;
	}

	const myInRangeSession = myStartHour <= myEndHour
		? (myHour >= myStartHour && myHour < myEndHour)
		: (myHour >= myStartHour || myHour < myEndHour);

	if (myInRangeSession) {
		myCurRangeHigh = myCurRangeHigh === null ? high[myIndex] : Math.max(myCurRangeHigh, high[myIndex]);
		myCurRangeLow = myCurRangeLow === null ? low[myIndex] : Math.min(myCurRangeLow, low[myIndex]);
		myRangeReady = false;
	}
	else if (myCurRangeHigh !== null) {
		myRangeReady = true;

		if (high[myIndex] > myCurRangeHigh) {
			myCurSweepDir = -1;
		}
		else if (low[myIndex] < myCurRangeLow) {
			myCurSweepDir = 1;
		}
	}

	myRangeHigh[myIndex] = myCurRangeHigh;
	myRangeLow[myIndex] = myCurRangeLow;
	mySweepDir[myIndex] = myRangeReady ? myCurSweepDir : 0;
}

const myRangeHighLine = paint(myRangeHigh, { name: 'RangeHigh', color: '#4DA3FF', style: 'ladder', thickness: 1 });
const myRangeLowLine = paint(myRangeLow, { name: 'RangeLow', color: '#FF9F4D', style: 'ladder', thickness: 1 });
fill(myRangeHighLine, myRangeLowLine, '#4DA3FF', 0.08);

const myBuySignal = for_every(mySweepDir, _d => _d === 1);
const mySellSignal = for_every(mySweepDir, _d => _d === -1);
register_signal(myBuySignal, 'Liquidity Sweep Buy Bias');
register_signal(mySellSignal, 'Liquidity Sweep Sell Bias');