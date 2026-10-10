// Experiment note: this is a best-effort translation of a Pine Script
// strategy into a TrendSpider indicator. Multi-trade position tracking,
// independent per-trade take-profits and order fills are approximated
// using a simple bar-by-bar simulation loop (not a true backtest engine),
// so exact fill timing/slippage may differ slightly from Pine results.
describe_indicator('S/R Breakout Strategy Long Only', 'price');

const myEntryTab = input.tab('Entry S/R');
const myLeftBars = myEntryTab.number('Entry Left Bars', 15, { min: 1, max: 200 });
const myRightBars = myEntryTab.number('Entry Right Bars', 15, { min: 1, max: 200 });

const myMngTab = input.tab('Trade Management');
const myAllowLong = myMngTab.boolean('Allow Long', true);
const myMaxRangePerc = myMngTab.number('Max Channel Width Percent', 2.0, { min: 0.1, max: 100 });
const myTpPercent = myMngTab.number('Take Profit Percent', 1.0, { min: 0.1, max: 100 });
const myMaxOpenTrades = myMngTab.number('Max Open Trades', 20, { min: 1, max: 500 });
const myCooldownBars = myMngTab.number('Cooldown Bars', 10, { min: 0, max: 1000 });

const mySmaTab = input.tab('SMA Filter');
const myUseSmaFilter = mySmaTab.boolean('Use SMA Filter', true);
const mySmaLength = mySmaTab.number('SMA Length', 200, { min: 1, max: 2000 });
// Empty string timeframe in Pine means "current chart timeframe". We expose
// it as a text input; leave empty for the same behavior.
const mySmaTf = mySmaTab.text('SMA Timeframe', '');
const myMinDistanceFromSmaPerc = mySmaTab.number('Min Distance From SMA Percent', 1.0, { min: 0.1, max: 100 });

// Pivot points for S/R, using high/low as per Pine's ta.pivothigh/pivotlow defaults.
const myPivotHighRaw = pivot_high(high, myLeftBars, myRightBars);
const myPivotLowRaw = pivot_low(low, myLeftBars, myRightBars);

// Fetch SMA source data. If timeframe is blank, use the current chart data.
const mySmaHistoryPromise = myUseSmaFilter && mySmaTf !== ''
	? request.history(current.ticker, mySmaTf)
	: Promise.resolve(null);

const [myHistoryResult] = await Promise.all([mySmaHistoryPromise]);

let mySmaLanded;
if (!myUseSmaFilter) {
	mySmaLanded = series_of(null);
}
else if (myHistoryResult) {
	assert(!myHistoryResult.error, 'Error fetching SMA timeframe data: ' + myHistoryResult.error);
	const myRawSma = sma(myHistoryResult.close, mySmaLength);
	// Shift by 1 to emulate Pine's [1] (previous closed bar value), anti-repaint.
	const myShiftedSma = shift(myRawSma, 1);
	const myLanded = land_points_onto_series(myHistoryResult.time, myShiftedSma, time, 'ge');
	mySmaLanded = interpolate_sparse_series(myLanded, 'constant');
}
else {
	const myRawSma = sma(close, mySmaLength);
	mySmaLanded = shift(myRawSma, 1);
}

const myResistanceOut = series_of(null);
const mySupportOut = series_of(null);
const myLongEntryOut = series_of(null);
const myTpExitOut = series_of(null);
const myLongSignal = series_of(false);
const myTpExitSignal = series_of(false);

let myResistanceLevel = null;
let mySupportLevel = null;
let myLastEntryBarIndex = null;
let myTradeCounter = 0;
const myOpenTrades = [];

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotHighRaw[myIndex] !== null && myPivotHighRaw[myIndex] !== undefined) {
		myResistanceLevel = myPivotHighRaw[myIndex];
	}
	if (myPivotLowRaw[myIndex] !== null && myPivotLowRaw[myIndex] !== undefined) {
		mySupportLevel = myPivotLowRaw[myIndex];
	}

	myResistanceOut[myIndex] = myResistanceLevel;
	mySupportOut[myIndex] = mySupportLevel;

	// A. Channel width validity
	let myChannelRange = null;
	if (myResistanceLevel !== null && mySupportLevel !== null && mySupportLevel !== 0) {
		myChannelRange = ((myResistanceLevel - mySupportLevel) / mySupportLevel) * 100;
	}
	const myIsRangeValid = myChannelRange !== null && myChannelRange <= myMaxRangePerc;

	// B. Breakout: close crosses over resistance
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myPrevResistance = myIndex > 0 ? myResistanceOut[myIndex - 1] : null;
	const myBreakoutLong = myResistanceLevel !== null
		&& myPrevResistance !== null
		&& close[myIndex] > myResistanceLevel
		&& myPrevClose !== null
		&& myPrevClose <= myPrevResistance;

	// C. SMA condition
	const mySmaValueAtIndex = mySmaLanded[myIndex];
	const mySmaCondLong = !myUseSmaFilter || (mySmaValueAtIndex !== null && mySmaValueAtIndex !== undefined && close[myIndex] > mySmaValueAtIndex);

	// D. Minimum distance from SMA
	let myDistanceFromSmaPerc = null;
	if (mySmaValueAtIndex !== null && mySmaValueAtIndex !== undefined && mySmaValueAtIndex !== 0) {
		myDistanceFromSmaPerc = Math.abs(close[myIndex] - mySmaValueAtIndex) / mySmaValueAtIndex * 100;
	}
	const myFarEnoughFromSma = !myUseSmaFilter || (myDistanceFromSmaPerc !== null && myDistanceFromSmaPerc > myMinDistanceFromSmaPerc);

	// E. Max open trades
	const myCanOpenMoreTrades = myOpenTrades.length < myMaxOpenTrades;

	// Cooldown check
	const myBarsSinceLastEntry = myLastEntryBarIndex === null ? 1000000 : (myIndex - myLastEntryBarIndex);
	const myCooldownPassed = myCooldownBars <= 0 || myBarsSinceLastEntry >= myCooldownBars;

	// F. Final entry condition
	const myLongCondition = myAllowLong && myBreakoutLong && myIsRangeValid && mySmaCondLong && myFarEnoughFromSma && myCanOpenMoreTrades && myCooldownPassed;

	myLongSignal[myIndex] = myLongCondition;

	if (myLongCondition) {
		myTradeCounter += 1;
		myOpenTrades.push({ entryPrice: close[myIndex], entryBar: myIndex, id: myTradeCounter });
		myLastEntryBarIndex = myIndex;
		myLongEntryOut[myIndex] = low[myIndex];
	}

	// Independent TP exits: check each open trade against this bar's high
	let myAnyExit = false;
	for (let myTradeIndex = myOpenTrades.length - 1; myTradeIndex >= 0; myTradeIndex -= 1) {
		const myTrade = myOpenTrades[myTradeIndex];
		const myTpPrice = myTrade.entryPrice * (1 + myTpPercent / 100);
		if (high[myIndex] >= myTpPrice) {
			myAnyExit = true;
			myOpenTrades.splice(myTradeIndex, 1);
		}
	}
	myTpExitSignal[myIndex] = myAnyExit;
	if (myAnyExit) {
		myTpExitOut[myIndex] = high[myIndex];
	}
}

register_signal(myLongSignal, 'Long Entry');
register_signal(myTpExitSignal, 'Take Profit Exit');

paint(myUseSmaFilter ? mySmaLanded : constants.empty_series, { name: 'SMA Filter', color: 'orange', thickness: 2 });
paint(myResistanceOut, { name: 'Entry Resistance', color: 'red', thickness: 2, style: 'ladder' });
paint(mySupportOut, { name: 'Entry Support', color: 'blue', thickness: 2, style: 'ladder' });

paint(myLongEntryOut, { name: 'Long Entry Marker', color: 'green', style: 'labels_below' });
paint(myTpExitOut, { name: 'Take Profit Marker', color: 'teal', style: 'labels_above' });