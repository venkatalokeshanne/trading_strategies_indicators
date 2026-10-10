// EXPERIMENTAL CONVERSION: this recreates the Pine Script's monthly
// high/low CLOSE tracking logic using daily OHLC data landed onto the
// current chart. TrendSpider's Custom JS API has no equivalent for
// Pine's line.new/box.new/label.new drawing objects (rays, boxes,
// floating labels anchored to specific historical bars), so this is
// approximated using constant-held step lines (functionally equal to
// a ray) and a filled area between the close line and the price
// extreme line (functionally close to the box). Results will track
// the same VALUES and the same bars where the extremes update, but
// will not look pixel-identical to Pine's drawing objects.
describe_indicator('Monthly High Low Close Rays And Boxes', 'price');

const myShowBoxes = input.boolean('Show Close to Extreme Boxes', true);
const myShowLabels = input.boolean('Show Price Labels', true);
const myHighBoxColor = input.color('High Box Fill Color', 'rgba(0,255,0,0.15)');
const myLowBoxColor = input.color('Low Box Fill Color', 'rgba(255,0,0,0.15)');

const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: ${myDailyData.error}`);

const myDayCount = myDailyData.time.length;

const myMonthHighSeries = [];
const myMonthLowSeries = [];
const myMonthHighPxSeries = [];
const myMonthLowPxSeries = [];
const myNewMonthFlagSeries = [];

let myMonthHighValue = null;
let myMonthLowValue = null;
let myMonthHighPxValue = null;
let myMonthLowPxValue = null;
let myPrevMonth = null;
let myPrevYear = null;

for (let myDayIndex = 0; myDayIndex < myDayCount; myDayIndex += 1) {
	const myTimeInfo = time_of(myDailyData.time[myDayIndex]);
	const myIsNewMonth = myDayIndex === 0 || myTimeInfo.month !== myPrevMonth || myTimeInfo.year !== myPrevYear;

	if (myIsNewMonth) {
		// Seed with the previous day's close (dailyClose[1] in Pine),
		// falling back to the current close on the very first bar.
		const mySeed = myDayIndex > 0 ? myDailyData.close[myDayIndex - 1] : myDailyData.close[myDayIndex];
		myMonthHighValue = mySeed;
		myMonthLowValue = mySeed;
		myMonthHighPxValue = myDailyData.high[myDayIndex];
		myMonthLowPxValue = myDailyData.low[myDayIndex];
	}
	else {
		const myCompletedClose = myDailyData.close[myDayIndex - 1];

		if (myCompletedClose > myMonthHighValue) {
			myMonthHighValue = myCompletedClose;
		}
		if (myCompletedClose < myMonthLowValue) {
			myMonthLowValue = myCompletedClose;
		}
		if (myDailyData.high[myDayIndex] > myMonthHighPxValue) {
			myMonthHighPxValue = myDailyData.high[myDayIndex];
		}
		if (myDailyData.low[myDayIndex] < myMonthLowPxValue) {
			myMonthLowPxValue = myDailyData.low[myDayIndex];
		}
	}

	myMonthHighSeries.push(myMonthHighValue);
	myMonthLowSeries.push(myMonthLowValue);
	myMonthHighPxSeries.push(myMonthHighPxValue);
	myMonthLowPxSeries.push(myMonthLowPxValue);
	myNewMonthFlagSeries.push(myIsNewMonth);

	myPrevMonth = myTimeInfo.month;
	myPrevYear = myTimeInfo.year;
}

// Land the daily derived values onto the current chart's timestamps.
// 'le' means "the last known daily value at or before this candle".
const myMonthHighLanded = land_points_onto_series(myDailyData.time, myMonthHighSeries, time, 'le');
const myMonthLowLanded = land_points_onto_series(myDailyData.time, myMonthLowSeries, time, 'le');
const myMonthHighPxLanded = land_points_onto_series(myDailyData.time, myMonthHighPxSeries, time, 'le');
const myMonthLowPxLanded = land_points_onto_series(myDailyData.time, myMonthLowPxSeries, time, 'le');
const myNewMonthLanded = land_points_onto_series(myDailyData.time, myNewMonthFlagSeries, time, 'eq');

// 'constant' interpolation keeps the backtest/alert-safe, non-repainting
// behavior (never looks ahead to future daily closes).
const myMonthHighLine = interpolate_sparse_series(myMonthHighLanded, 'constant');
const myMonthLowLine = interpolate_sparse_series(myMonthLowLanded, 'constant');
const myMonthHighPxLine = interpolate_sparse_series(myMonthHighPxLanded, 'constant');
const myMonthLowPxLine = interpolate_sparse_series(myMonthLowPxLanded, 'constant');

const myHighRayPainted = paint(myMonthHighLine, { name: 'Month High Close', color: 'lime', thickness: 2, style: 'line' });
const myLowRayPainted = paint(myMonthLowLine, { name: 'Month Low Close', color: 'red', thickness: 2, style: 'line' });

// Approximate the Pine "box" (close to extreme price shaded area) with a fill.
const myHighBoxTopLine = myShowBoxes ? myMonthHighPxLine : constants.empty_series;
const myLowBoxBottomLine = myShowBoxes ? myMonthLowPxLine : constants.empty_series;

fill(
	myHighRayPainted,
	paint(myHighBoxTopLine, { name: 'Month High Price Extreme', color: 'lime', thickness: 1, style: 'dotted' }),
	myHighBoxColor,
	0.15
);

fill(
	myLowRayPainted,
	paint(myLowBoxBottomLine, { name: 'Month Low Price Extreme', color: 'red', thickness: 1, style: 'dotted' }),
	myLowBoxColor,
	0.15
);

// Labels on the latest point of each ray, mimicking the Pine labels
// that follow price to the current bar.
const myLastIndex = close.length - 1;

if (myShowLabels && myMonthHighLine[myLastIndex] !== null) {
	paint_label_at_line(myHighRayPainted, myLastIndex, 'Month High Close', { color: 'lime' });
}
if (myShowLabels && myMonthLowLine[myLastIndex] !== null) {
	paint_label_at_line(myLowRayPainted, myLastIndex, 'Month Low Close', { color: 'red' });
}

// Signals for scanners, alerts and backtesting.
const myNewMonthSignal = for_every(myNewMonthLanded, _myFlag => !!_myFlag);
const myHighCloseBrokenSignal = for_every(close, myMonthHighLine, (_myClose, _myHigh) => _myHigh !== null && _myClose > _myHigh);
const myLowCloseBrokenSignal = for_every(close, myMonthLowLine, (_myClose, _myLow) => _myLow !== null && _myClose < _myLow);

register_signal(myNewMonthSignal, 'New Month Started');
register_signal(myHighCloseBrokenSignal, 'Close Above Month High Close');
register_signal(myLowCloseBrokenSignal, 'Close Below Month Low Close');