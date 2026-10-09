describe_indicator('Single Factor Index Enhancer', 'price');

// ─────────────────────────────────────────────────────────
// Inputs, grouped like the original Pine script
// ─────────────────────────────────────────────────────────
const macroTab = input.tab('Macro Trend');
const myMacroTF = macroTab.select('Macro Timeframe', 'D', constants.time_frames);
const maGroup = macroTab.group('MA Base');
const myMaShortLen = maGroup.number('Short MA Length', 60, { min: 1, max: 500 });
const myMaLongLen = maGroup.number('Long MA Length', 100, { min: 1, max: 500 });
// shortened from "Fake Breakout Confirm Bars" to satisfy the input name length limit
const myConfBars = maGroup.number('Confirm Bars', 15, { min: 1, max: 200 });

const zTab = input.tab('Attack Engine');
const myZLen = zTab.number('ZScore Length', 24, { min: 1, max: 500 });
const myZEntry = zTab.number('Entry Threshold', -2.1, { min: -10, max: 10, step: 0.1 });
const myZExit = zTab.number('Exit Threshold', 1.1, { min: -10, max: 10, step: 0.1 });

const riskTab = input.tab('Risk Settings');
// shortened from "Max Drawdown Stop Loss Percent" to satisfy the input name length limit
const myStopLossPct = riskTab.number('Stop Loss Percent', 3.0, { min: 0.1, max: 50, step: 0.1 });

// ─────────────────────────────────────────────────────────
// Macro trend base: fetch macro timeframe data and compute SMAs there,
// then land them onto the current chart (constant interpolation,
// matching Pine's lookahead_on request.security behavior as closely
// as a non-repainting approach allows).
// ─────────────────────────────────────────────────────────
const myMacroData = await request.history(current.ticker, myMacroTF);
assert(!myMacroData.error, `Error fetching macro data: "${myMacroData.error}"`);

const myMacroMaShort = sma(myMacroData.close, myMaShortLen);
const myMacroMaLong = sma(myMacroData.close, myMaLongLen);

const myMaShortLanded = interpolate_sparse_series(
	land_points_onto_series(myMacroData.time, myMacroMaShort, time, 'le'),
	'constant'
);
const myMaLongLanded = interpolate_sparse_series(
	land_points_onto_series(myMacroData.time, myMacroMaLong, time, 'le'),
	'constant'
);

// ─────────────────────────────────────────────────────────
// Z-Score engine, computed on the current chart's close
// ─────────────────────────────────────────────────────────
const myPriceMean = sma(close, myZLen);
const myPriceStd = stdev(close, myZLen);

const myZVal = for_every(close, myPriceMean, myPriceStd, (_close, _mean, _std) => {
	const myStdClamped = Math.max(_std, 0.0001);
	return (_close - _mean) / myStdClamped;
});

// ─────────────────────────────────────────────────────────
// Sequential simulation of: bull confirmation counter, regime,
// position state, average entry price and stop-loss logic.
// This must be a plain stateful loop since it depends on several
// pieces of state carried bar-to-bar (mirrors Pine's `var` state).
// ─────────────────────────────────────────────────────────
const myBullRegime = series_of(false);
const myIsLong = series_of(false);
const myPositionSize = series_of(0);
const myStopPrice = series_of(null);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);

let myBullConfCnt = 0;
let myIsLongState = false;
let myPositionAvgPrice = 0;
let myPositionSizeState = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myMacroBullRaw = myMaShortLanded[myIndex] != null && myMaLongLanded[myIndex] != null
		? myMaShortLanded[myIndex] > myMaLongLanded[myIndex]
		: false;

	myBullConfCnt = myMacroBullRaw ? myBullConfCnt + 1 : 0;
	const myBullRegimeValue = myBullConfCnt >= myConfBars;
	myBullRegime[myIndex] = myBullRegimeValue;

	const myStopPriceValue = myPositionSizeState > 0
		? myPositionAvgPrice * (1 - myStopLossPct / 100)
		: null;

	const myIsStopLoss = myPositionSizeState > 0 && myStopPriceValue != null && close[myIndex] < myStopPriceValue;

	// Entry condition
	if (myBullRegimeValue && myZVal[myIndex] < myZEntry) {
		myIsLongState = true;
	}

	// Exit conditions (take profit, regime flip, hard stop loss)
	if (myZVal[myIndex] > myZExit || !myBullRegimeValue || myIsStopLoss) {
		myIsLongState = false;
	}

	let myEnteredNow = false;
	let myExitedNow = false;

	// All-in entry
	if (myIsLongState && myPositionSizeState === 0) {
		myPositionSizeState = 1;
		myPositionAvgPrice = close[myIndex];
		myEnteredNow = true;
	}

	// Close all
	if (!myIsLongState && myPositionSizeState > 0) {
		myPositionSizeState = 0;
		myPositionAvgPrice = 0;
		myExitedNow = true;
	}

	myIsLong[myIndex] = myIsLongState;
	myPositionSize[myIndex] = myPositionSizeState;
	myStopPrice[myIndex] = myPositionSizeState > 0
		? myPositionAvgPrice * (1 - myStopLossPct / 100)
		: null;
	myEntrySignal[myIndex] = myEnteredNow;
	myExitSignal[myIndex] = myExitedNow;
}

// ─────────────────────────────────────────────────────────
// Visualization
// ─────────────────────────────────────────────────────────
paint(myStopPrice, { name: 'Stop Loss Line', color: 'red', style: 'ladder', thickness: 2 });
paint(myMaShortLanded, { name: 'Macro Short MA', color: 'rgba(33,150,243,0.7)', thickness: 2 });
paint(myMaLongLanded, { name: 'Macro Long MA', color: 'rgba(255,152,0,0.7)', thickness: 2 });

const myCandleColors = for_every(myBullRegime, myPositionSize, (_bull, _pos) => {
	if (_pos > 0) return 'rgba(76,175,80,0.5)';
	return _bull ? 'rgba(76,175,80,0.15)' : 'rgba(244,67,54,0.15)';
});
color_candles(myCandleColors);

// ─────────────────────────────────────────────────────────
// Signals for scanners, alerts and strategy testing
// ─────────────────────────────────────────────────────────
register_signal(myBullRegime, 'Bull Regime');
register_signal(myEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');
register_signal(myIsLong, 'In Long Position');