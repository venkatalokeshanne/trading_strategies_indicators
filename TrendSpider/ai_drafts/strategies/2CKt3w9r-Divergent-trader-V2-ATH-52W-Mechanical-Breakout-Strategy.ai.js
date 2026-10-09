describe_indicator('ATH 52W Mechanical Breakout Strategy', 'price');

// NOTE: this is an approximation of the Pine Script strategy logic.
// TrendSpider custom indicators don't have a built-in strategy engine
// (no strategy.entry/exit/position_size), so position state, entries
// and exits are simulated manually, bar by bar, inside a loop.
// Stop-hit detection assumes the ATR trailing stop is hit if the bar's
// low touches or goes below the stop level (intrabar fill approximation).
// Entries/exits are applied on the same bar the condition triggers,
// instead of Pine's next-bar order fill behavior.

const myUseATH = input.boolean('Use All Time High', true);
const myUse52W = input.boolean('Use 52 Week High', true);
const myAthLookback = input.number('ATH Lookback Bars', 5000, { min: 10, max: 5000 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myUseEMAExit = input.boolean('Use EMA Exit Instead of ATR', false);
const myEMALength = input.number('EMA Length', 20, { min: 1, max: 500 });

// All time high, rolling over a large lookback window as a proxy for "all time"
const myAth = highest(high, myAthLookback);
const myAthPrev = shift(myAth, 1);

// True weekly 52-week high, fetched from weekly resolution data
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

const myWeeklyHigh52 = highest(myWeeklyData.high, 52);
const myWeeklyHighLanded = land_points_onto_series(myWeeklyData.time, myWeeklyHigh52, time, 'le');
const myWeeklyHigh = interpolate_sparse_series(myWeeklyHighLanded, 'constant');
const myWeeklyHighPrev = shift(myWeeklyHigh, 1);

const myAtr = atr(high, low, close, myAtrLength);
const myEma = ema(close, myEMALength);

const myBreakATH = for_every(high, myAthPrev, (_h, _a) => myUseATH && _a !== null && _h > _a);
const myBreak52W = for_every(high, myWeeklyHighPrev, (_h, _w) => myUse52W && _w !== null && _h > _w);
const myLongCondition = for_every(myBreakATH, myBreak52W, (_b1, _b2) => _b1 || _b2);

const myEntrySignalSeries = series_of(false);
const myExitSignalSeries = series_of(false);
const myAtrStopSeries = series_of(null);
const myEmaExitLineSeries = series_of(null);

let myPositionState = 0;
let myHighestSinceEntry = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPositionState > 0) {
		myHighestSinceEntry = myHighestSinceEntry === null ? high[myIndex] : Math.max(myHighestSinceEntry, high[myIndex]);
	}
	else {
		myHighestSinceEntry = null;
	}

	const myAtrStopValue = myHighestSinceEntry !== null ? myHighestSinceEntry - (myAtr[myIndex] * myAtrMult) : null;
	myAtrStopSeries[myIndex] = (myPositionState > 0 && !myUseEMAExit) ? myAtrStopValue : null;
	myEmaExitLineSeries[myIndex] = myUseEMAExit ? myEma[myIndex] : null;

	let myExit = false;

	if (myPositionState > 0) {
		if (!myUseEMAExit && myAtrStopValue !== null && low[myIndex] <= myAtrStopValue) {
			myExit = true;
		}
		if (myUseEMAExit && close[myIndex] < myEma[myIndex]) {
			myExit = true;
		}
	}

	if (myExit) {
		myPositionState = 0;
		myHighestSinceEntry = null;
	}

	let myEntry = false;

	if (myPositionState === 0 && myLongCondition[myIndex]) {
		myEntry = true;
		myPositionState = 1;
	}

	myEntrySignalSeries[myIndex] = myEntry;
	myExitSignalSeries[myIndex] = myExit;
}

paint(myUseATH ? myAth : constants.empty_series, { name: 'ATH Level', color: '#8B0000', thickness: 2 });
paint(myUse52W ? myWeeklyHigh : constants.empty_series, { name: '52W High', color: 'red', thickness: 2 });
paint(myEmaExitLineSeries, { name: 'EMA Exit', color: 'blue' });
paint(myAtrStopSeries, { name: 'ATR Trailing Stop', color: 'orange', style: 'dotted' });

register_signal(myEntrySignalSeries, 'Long Entry');
register_signal(myExitSignalSeries, 'Long Exit');