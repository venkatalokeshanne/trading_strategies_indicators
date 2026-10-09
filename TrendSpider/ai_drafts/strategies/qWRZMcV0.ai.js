// EXPERIMENTAL CONVERSION NOTICE:
// This is a best-effort translation of a TradingView strategy() script into
// a TrendSpider Custom JS indicator. The Custom JS API has no concept of
// strategy.equity, strategy.closedtrades, position sizing or real PnL
// tracking, so all the risk-management logic (daily/weekly/monthly PnL
// limits, equity-based position sizing) could not be reproduced. Only the
// signal logic (trend alignment, BOS detection, Fibonacci 0.618 level,
// session filter, one-trade-per-day throttle) is reproduced. Treat this as
// an experiment, not a certified 1:1 port - verify behavior before using it.
describe_indicator('XAU Quant SMC Signals', 'price');

const myTfTab = input.tab('Multi Timeframe');
const myTfDaily = myTfTab.text('Daily Trend TF', 'D');
const myTf4h = myTfTab.text('4H Trend TF', '240');
const myTf15m = myTfTab.text('BOS Structure TF', '15');

const mySessionTab = input.tab('Trading Session (GMT+1)');
const mySessStart = mySessionTab.number('Start Hour', 7, { min: 0, max: 23 });
const mySessEnd = mySessionTab.number('End Hour', 13, { min: 0, max: 23 });

// Fetch the higher timeframe data needed for trend and BOS detection.
const [myDailyData, my4hData, my15mData] = await Promise.all([
	request.history(current.ticker, myTfDaily),
	request.history(current.ticker, myTf4h),
	request.history(current.ticker, myTf15m)
]);

assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);
assert(!my4hData.error, 'Error fetching 4H data: ' + my4hData.error);
assert(!my15mData.error, 'Error fetching 15M data: ' + my15mData.error);

// Trend per timeframe: close vs EMA50
const myDailyEma = ema(myDailyData.close, 50);
const myDailyTrend = for_every(myDailyData.close, myDailyEma, (_c, _e) => _c > _e ? 1 : -1);

const my4hEma = ema(my4hData.close, 50);
const my4hTrend = for_every(my4hData.close, my4hEma, (_c, _e) => _c > _e ? 1 : -1);

// BOS inputs on the 15M timeframe (rolling 10-bar highest/lowest, close)
const my15mHighest = highest(my15mData.high, 10);
const my15mLowest = lowest(my15mData.low, 10);

// Land all higher timeframe series onto the current chart's candles.
const myTrendDLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyTrend, time, 'ge'),
	'constant'
);
const myTrend4hLanded = interpolate_sparse_series(
	land_points_onto_series(my4hData.time, my4hTrend, time, 'ge'),
	'constant'
);
const my15mHighestLanded = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, my15mHighest, time, 'ge'),
	'constant'
);
const my15mLowestLanded = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, my15mLowest, time, 'ge'),
	'constant'
);
const my15mCloseLanded = interpolate_sparse_series(
	land_points_onto_series(my15mData.time, my15mData.close, time, 'ge'),
	'constant'
);

const myCount = close.length;
const myFib618 = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

let myBosOccurred = false;
let myFibHigh = null;
let myFibLow = null;
let myTradesToday = 0;
let myPrevDayOfWeek = null;

for (let myIndex = 1; myIndex < myCount; myIndex += 1) {
	const myTrendD = myTrendDLanded[myIndex];
	const myTrend4h = myTrend4hLanded[myIndex];
	const myTrendAligned = (myTrendD == 1 && myTrend4h == 1) || (myTrendD == -1 && myTrend4h == -1);
	const myIsBullish = myTrendD == 1 && myTrend4h == 1;

	const myDayOfWeek = time_of(time[myIndex]).dayOfWeek;
	if (myPrevDayOfWeek !== null && myDayOfWeek != myPrevDayOfWeek) {
		myBosOccurred = false;
		myTradesToday = 0;
	}
	myPrevDayOfWeek = myDayOfWeek;

	const myHigh15Now = my15mHighestLanded[myIndex];
	const myHigh15Prev = my15mHighestLanded[myIndex - 1];
	const myLow15Now = my15mLowestLanded[myIndex];
	const myLow15Prev = my15mLowestLanded[myIndex - 1];
	const myClose15Now = my15mCloseLanded[myIndex];
	const myClose15Prev = my15mCloseLanded[myIndex - 1];

	const myCrossoverHigh = myClose15Prev <= myHigh15Prev && myClose15Now > myHigh15Prev;
	const myCrossunderLow = myClose15Prev >= myLow15Prev && myClose15Now < myLow15Prev;

	if (myIsBullish && myCrossoverHigh) {
		myBosOccurred = true;
		myFibHigh = myHigh15Now;
		myFibLow = myLow15Now;
	}
	else if (!myIsBullish && myCrossunderLow) {
		myBosOccurred = true;
		myFibHigh = myHigh15Now;
		myFibLow = myLow15Now;
	}

	const myFibValue = (myBosOccurred && myFibHigh != null && myFibLow != null)
		? (myIsBullish ? myFibHigh - (myFibHigh - myFibLow) * 0.618 : myFibLow + (myFibHigh - myFibLow) * 0.618)
		: null;

	myFib618[myIndex] = myFibValue;

	const myHour = time_of(time[myIndex]).hours;
	const myInSession = myHour >= mySessStart && myHour < mySessEnd;

	// NOTE: PnL based risk limits from the original script are not
	// reproducible here; only the "one trade per day" throttle is kept.
	const myCanTrade = myTradesToday < 1;

	const myPrevLow = low[myIndex - 1];
	const myPrevHigh = high[myIndex - 1];
	const myPrevFib = myFib618[myIndex - 1];

	const myCrossunderFib = myFibValue != null && myPrevFib != null && myPrevLow >= myPrevFib && low[myIndex] < myFibValue;
	const myCrossoverFib = myFibValue != null && myPrevFib != null && myPrevHigh <= myPrevFib && high[myIndex] > myFibValue;

	const myLongCondition = myTrendAligned && myIsBullish && myBosOccurred && myCrossunderFib && myInSession && myCanTrade;
	const myShortCondition = myTrendAligned && !myIsBullish && myBosOccurred && myCrossoverFib && myInSession && myCanTrade;

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

const myFib618Line = paint(myFib618, { name: 'Fib618Entry', color: '#ffd54f', thickness: 2, style: 'line' });

const myLongMarks = for_every(myLongSignal, _s => _s ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortSignal, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'BuySignal', color: '#26a69a', style: 'labels_below' });
paint(myShortMarks, { name: 'SellSignal', color: '#ef5350', style: 'labels_above' });

register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');