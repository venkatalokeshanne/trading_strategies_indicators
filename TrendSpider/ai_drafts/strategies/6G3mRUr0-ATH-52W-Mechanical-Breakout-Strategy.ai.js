describe_indicator('ATH / 52W Mechanical Breakout Strategy', 'price');

// ==== INPUTS ====
const tab = input.tab('Breakout Settings');
const i_useATH = tab.boolean('Use All-Time High', true);
const i_use52W = tab.boolean('Use 52-Week High', true);
const i_athLookback = tab.number('ATH Lookback Bars', 5000, { min: 10, max: 5000 });

const exitTab = input.tab('Exit Settings');
const exitRow1 = exitTab.row();
const i_atrLength = exitRow1.number('ATR Length', 14, { min: 1, max: 200 });
const i_atrMult = exitRow1.number('ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });
const i_useEMAExit = exitTab.boolean('Use EMA Exit Instead of ATR', false);
const i_emaLength = exitTab.number('EMA Length', 20, { min: 1, max: 500 });

// ==== LEVEL CALCULATIONS ====

// All-Time High (rolling large lookback, as a proxy for "full history")
const myAth = highest(high, i_athLookback);

// True 52-Week High from weekly data.
// NOTE: request.history gives us weekly candles; we compute Highest(High,52) on them,
// then land those values onto our chart's timeline. We use 'le' matching
// (last known value at or before each candle time) to emulate request.security's
// default non-repainting behavior (value only updates once the weekly bar closes).
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, 'Error fetching weekly data: ' + myWeeklyData.error);
const myWeeklyHigh52 = highest(myWeeklyData.high, 52);
const myWeeklyHighLanded = land_points_onto_series(myWeeklyData.time, myWeeklyHigh52, time, 'le');
const myWeeklyHigh = interpolate_sparse_series(myWeeklyHighLanded, 'constant');

// Pine's [1] means "value of the series on the previous bar". We approximate
// this using shift(1) on our already-computed series.
const myAthPrev = shift(myAth, 1);
const myWeeklyHighPrev = shift(myWeeklyHigh, 1);

// ATR and EMA (precomputed outside any loop, per the engine's rules)
const myAtr = atr(high, low, close, i_atrLength);
const myEma = ema(close, i_emaLength);

// ==== STRATEGY SIMULATION ====
// We simulate the Pine strategy's position state bar-by-bar, since the
// Custom JS API has no built-in strategy/backtesting state machine.
const myCandleCount = close.length;

const myPositionSize = series_of(0);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myAtrStopSeries = series_of(null);
const myHighestSinceEntryArr = series_of(null);

let myHighestSinceEntry = null;
let myInPosition = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myBreakATH = i_useATH && myAthPrev[myIndex] != null && high[myIndex] > myAthPrev[myIndex];
	const myBreak52W = i_use52W && myWeeklyHighPrev[myIndex] != null && high[myIndex] > myWeeklyHighPrev[myIndex];
	const myLongCondition = myBreakATH || myBreak52W;

	// Entry: only when flat
	if (myLongCondition && !myInPosition) {
		myInPosition = true;
		myEntrySignal[myIndex] = true;
		myHighestSinceEntry = high[myIndex];
	}
	else if (myInPosition) {
		myHighestSinceEntry = Math.max(myHighestSinceEntry, high[myIndex]);
	}
	else {
		myHighestSinceEntry = null;
	}

	let myAtrStop = null;
	if (myInPosition && myHighestSinceEntry != null && myAtr[myIndex] != null) {
		myAtrStop = myHighestSinceEntry - (myAtr[myIndex] * i_atrMult);
	}

	// Exit logic
	let myExitedThisBar = false;
	if (myInPosition) {
		if (!i_useEMAExit) {
			// ATR trailing stop exit: triggers if low breaches the stop level
			if (myAtrStop != null && low[myIndex] <= myAtrStop) {
				myExitedThisBar = true;
			}
		}
		else {
			// EMA exit
			if (myEma[myIndex] != null && close[myIndex] < myEma[myIndex]) {
				myExitedThisBar = true;
			}
		}
	}

	if (myExitedThisBar) {
		myExitSignal[myIndex] = true;
		myInPosition = false;
		myHighestSinceEntry = null;
		myAtrStop = null;
	}

	myPositionSize[myIndex] = myInPosition ? 1 : 0;
	myAtrStopSeries[myIndex] = (myInPosition && !i_useEMAExit) ? myAtrStop : null;
	myHighestSinceEntryArr[myIndex] = myHighestSinceEntry;
}

// ==== PLOTS ====
paint(i_useATH ? myAth : constants.empty_series, { name: 'ATH Level', color: 'maroon', thickness: 2 });
paint(i_use52W ? myWeeklyHigh : constants.empty_series, { name: '52W High', color: 'red', thickness: 2 });
paint(i_useEMAExit ? myEma : constants.empty_series, { name: 'EMA Exit', color: 'blue' });
paint(myAtrStopSeries, { name: 'ATR Trailing Stop', color: 'orange', style: 'line' });

// ==== SIGNALS FOR SCANNERS / ALERTS / STRATEGY TESTER ====
register_signal(myEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');
register_signal(for_every(myPositionSize, m => m > 0), 'In Long Position');