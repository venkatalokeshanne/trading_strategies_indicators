describe_indicator('XAUUSD Quant SMC D1 4H 15M 5M', 'price');

// NOTE: this is a best-effort translation of a Pine Script STRATEGY into
// a TrendSpider INDICATOR. TrendSpider custom indicators have no concept
// of strategy.equity, strategy.closedtrades or broker-side PnL tracking,
// so all the daily/weekly/monthly PnL risk limits from the original
// script could not be reproduced. They were replaced with a simplified
// "max 1 signal per day" limiter. Session hours use the exchange time
// zone (via time_of()) as a proxy for "GMT+1" used in the original script.

const myTfD = input.text('Trend Daily Timeframe', 'D');
const myTf4h = input.text('Trend 4H Timeframe', '240');
const myTf15m = input.text('BOS Structure Timeframe', '15');

const mySessionRow = input.row();
const mySessStart = mySessionRow.number('Session Start Hour', 7, { min: 0, max: 23 });
const mySessEnd = mySessionRow.number('Session End Hour', 13, { min: 0, max: 23 });

// ── fetch multi-timeframe data ──
const [myDailyData, my4hData, my15mData] = await Promise.all([
	request.history(current.ticker, myTfD),
	request.history(current.ticker, myTf4h),
	request.history(current.ticker, myTf15m)
]);

assert(!myDailyData.error, `Error fetching Daily data: ${myDailyData.error}`);
assert(!my4hData.error, `Error fetching 4H data: ${my4hData.error}`);
assert(!my15mData.error, `Error fetching 15M data: ${my15mData.error}`);

// ── trend on D1 and 4H (close vs EMA50) ──
const myEma50D = ema(myDailyData.close, 50);
const myTrendDRaw = for_every(myDailyData.close, myEma50D, (_c, _e) => (_c > _e ? 1 : -1));

const myEma50H4 = ema(my4hData.close, 50);
const myTrend4hRaw = for_every(my4hData.close, myEma50H4, (_c, _e) => (_c > _e ? 1 : -1));

const myTrendDLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myTrendDRaw, time, 'le'),
	'constant'
);
const myTrend4hLanded = interpolate_sparse_series(
	land_points_onto_series(my4hData.time, myTrend4hRaw, time, 'le'),
	'constant'
);

// ── 15M highest/lowest(10) and close, landed onto current chart ──
const myHigh15Raw = highest(my15mData.high, 10);
const myLow15Raw = lowest(my15mData.low, 10);

const myHigh15Landed = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, myHigh15Raw, time, 'le'),
	'constant'
);
const myLow15Landed = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, myLow15Raw, time, 'le'),
	'constant'
);
const myClose15Landed = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, my15mData.close, time, 'le'),
	'constant'
);

const myHigh15Shift1 = shift(myHigh15Landed, 1);
const myLow15Shift1 = shift(myLow15Landed, 1);

// ── stateful BOS / Fibonacci / signal logic (sequential, cannot be vectorized) ──
const myCandleCount = close.length;

const myFib618 = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

let myBosOccurred = false;
let myFibHigh = null;
let myFibLow = null;
let myPrevDayOfWeek = null;
let myTradesToday = 0;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayOfWeek = myTimeInfo.dayOfWeek;

	if (myPrevDayOfWeek !== null && myDayOfWeek !== myPrevDayOfWeek) {
		myBosOccurred = false;
		myTradesToday = 0;
	}
	myPrevDayOfWeek = myDayOfWeek;

	const myIsBullish = myTrendDLanded[myIndex] === 1 && myTrend4hLanded[myIndex] === 1;
	const myIsBearish = myTrendDLanded[myIndex] === -1 && myTrend4hLanded[myIndex] === -1;
	const myTrendAligned = myIsBullish || myIsBearish;

	const myCrossoverUp = myClose15Landed[myIndex] > myHigh15Shift1[myIndex] &&
		myClose15Landed[myIndex - 1] <= myHigh15Shift1[myIndex - 1];
	const myCrossunderDown = myClose15Landed[myIndex] < myLow15Shift1[myIndex] &&
		myClose15Landed[myIndex - 1] >= myLow15Shift1[myIndex - 1];

	if (myIsBullish && myCrossoverUp) {
		myBosOccurred = true;
		myFibHigh = myHigh15Landed[myIndex];
		myFibLow = myLow15Landed[myIndex];
	}
	else if (myIsBearish && myCrossunderDown) {
		myBosOccurred = true;
		myFibHigh = myHigh15Landed[myIndex];
		myFibLow = myLow15Landed[myIndex];
	}

	let myFibValue = null;
	if (myFibHigh !== null && myFibLow !== null) {
		myFibValue = myIsBullish ?
			myFibHigh - (myFibHigh - myFibLow) * 0.618 :
			myFibLow + (myFibHigh - myFibLow) * 0.618;
	}
	myFib618[myIndex] = myFibValue;

	const myInSession = myTimeInfo.hours >= mySessStart && myTimeInfo.hours < mySessEnd;
	const myCanTrade = myTradesToday < 1;

	const myPrevFibValue = myFib618[myIndex - 1];
	const myCrossunderLow = myFibValue !== null && myPrevFibValue !== null &&
		low[myIndex] < myFibValue && low[myIndex - 1] >= myPrevFibValue;
	const myCrossoverHigh = myFibValue !== null && myPrevFibValue !== null &&
		high[myIndex] > myFibValue && high[myIndex - 1] <= myPrevFibValue;

	const myLongCondition = myTrendAligned && myIsBullish && myBosOccurred &&
		myCrossunderLow && myInSession && myCanTrade;
	const myShortCondition = myTrendAligned && myIsBearish && myBosOccurred &&
		myCrossoverHigh && myInSession && myCanTrade;

	if (myLongCondition) {
		myBosOccurred = false;
		myTradesToday = 1;
	}
	if (myShortCondition) {
		myBosOccurred = false;
		myTradesToday = 1;
	}

	myLongSignal[myIndex] = myLongCondition;
	myShortSignal[myIndex] = myShortCondition;
}

// ── painting ──
paint(myFib618, { name: 'Fib618Entry', color: '#f0c419', style: 'line' });

const myLongMarks = for_every(myLongSignal, low, (_s, _l) => (_s ? _l : null));
const myShortMarks = for_every(myShortSignal, high, (_s, _h) => (_s ? _h : null));

paint(myLongMarks, { name: 'BuySignal', color: '#2ecc71', style: 'labels_below' });
paint(myShortMarks, { name: 'SellSignal', color: '#e74c3c', style: 'labels_above' });

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');