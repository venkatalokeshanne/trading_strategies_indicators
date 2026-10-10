describe_indicator('Turtle Trading Strategy with ATR Stop and Pyramiding', 'price');

// ──────────────────────────────────────────────────────────────
// This is a port of a TradingView Pine strategy. It reproduces
// the breakout/trend/ATR math bar by bar in a sequential loop,
// since the pyramiding state (lastEntryPrice, pyramidCount,
// atrStop, position_size) depends on prior bar outcomes exactly
// like Pine's "var" variables do.
// ──────────────────────────────────────────────────────────────

const myInputsTab = input.tab('Settings');

const myEntryGroup = myInputsTab.group('Breakout');
const myEntryLength = myEntryGroup.number('Entry Breakout Length', 20, { min: 1, max: 500 });
const myExitLength = myEntryGroup.number('Exit Breakout Length', 10, { min: 1, max: 500 });

const myTrendGroup = myInputsTab.group('Trend Filter');
const myTrendMaLength = myTrendGroup.number('Trend MA Length', 200, { min: 1, max: 1000 });
const myUseTrendFilter = myTrendGroup.boolean('Use Trend Filter', true);

const myAtrGroup = myInputsTab.group('ATR Stop');
const myAtrLength = myAtrGroup.number('ATR Length', 20, { min: 1, max: 500 });
const myAtrStopMultiple = myAtrGroup.number('ATR Stop Multiple', 2.0, { min: 0.1, max: 20, step: 0.1 });

const myPyramidGroup = myInputsTab.group('Pyramiding');
// Shortened title (platform rejected the longer original due to a length limit)
const myRiskPctPerEntry = myPyramidGroup.number('Size Percent Per Entry', 25, { min: 1, max: 100 });
const myMaxPyramidEntries = myPyramidGroup.number('Maximum Pyramid Entries', 4, { min: 1, max: 10 });

const myDisplayGroup = myInputsTab.group('Display');
const myShowTrendMa = myDisplayGroup.boolean('Show Trend MA', true);
const myShowEntryLine = myDisplayGroup.boolean('Show Entry Line', true);
const myShowExitLine = myDisplayGroup.boolean('Show Exit Line', true);
const myShowAtrStop = myDisplayGroup.boolean('Show ATR Stop', true);

// ──────────────────────────────────────────────────────────────
// Core series
// ──────────────────────────────────────────────────────────────
const myTrendMa = sma(close, myTrendMaLength);
const myEntryHigh = highest(shift(high, 1), myEntryLength);
const myExitLow = lowest(shift(low, 1), myExitLength);
const myAtrValue = atr(high, low, close, myAtrLength);
const myCount = close.length;

// Output series
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myAtrStopSeries = series_of(null);
const myPositionSize = series_of(0);

// Sequential (Pine "var") state
let myLastEntryPrice = null;
let myPyramidCount = 0;
let myAtrStop = null;
let myPositionSizeState = 0;
let myRawSellPrevState = false;

for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myTrendMaValue = myTrendMa[myIndex];
	const myEntryHighValue = myEntryHigh[myIndex];
	const myExitLowValue = myExitLow[myIndex];
	const myAtrAtIndex = myAtrValue[myIndex];

	const myTrendFilter = myTrendMaValue != null && myClose > myTrendMaValue;
	const myRawBuySignal = myEntryHighValue != null && myClose > myEntryHighValue && (!myUseTrendFilter || myTrendFilter);

	const myCanAddPosition = myPositionSizeState === 0 || (
		myPositionSizeState > 0 &&
		myPyramidCount < myMaxPyramidEntries &&
		myAtrAtIndex != null &&
		myLastEntryPrice != null &&
		myClose >= myLastEntryPrice + (0.5 * myAtrAtIndex)
	);

	const myBuySignalValue = myRawBuySignal && myCanAddPosition;

	if (myBuySignalValue) {
		myPyramidCount += 1;
		myLastEntryPrice = myClose;

		if (myPositionSizeState === 0) {
			myAtrStop = myAtrAtIndex != null ? myClose - myAtrAtIndex * myAtrStopMultiple : null;
		}

		myPositionSizeState += 1;
	}

	if (myPositionSizeState === 0) {
		myPyramidCount = 0;
		myLastEntryPrice = null;
		myAtrStop = null;
	}

	if (myPositionSizeState > 0 && myAtrAtIndex != null) {
		const myNewStop = myClose - myAtrAtIndex * myAtrStopMultiple;
		myAtrStop = myAtrStop == null ? myNewStop : Math.max(myAtrStop, myNewStop);
	}

	const myExitSignalChannel = myPositionSizeState > 0 && myExitLowValue != null && myClose < myExitLowValue;
	const myExitSignalAtr = myPositionSizeState > 0 && myAtrStop != null && myClose < myAtrStop;
	const myRawSellSignal = myExitSignalChannel || myExitSignalAtr;
	const mySellSignalValue = myRawSellSignal && !myRawSellPrevState;

	if (mySellSignalValue) {
		myPositionSizeState = 0;
	}

	myBuySignal[myIndex] = myBuySignalValue;
	mySellSignal[myIndex] = mySellSignalValue;
	myAtrStopSeries[myIndex] = (myPositionSizeState > 0 && myAtrStop != null) ? myAtrStop : null;
	myPositionSize[myIndex] = myPositionSizeState;
	myRawSellPrevState = myRawSellSignal;
}

// ──────────────────────────────────────────────────────────────
// Painting
// ──────────────────────────────────────────────────────────────
paint(myShowTrendMa ? myTrendMa : constants.empty_series, { name: 'Trend MA', color: '#2962FF', thickness: 2 });
paint(myShowEntryLine ? myEntryHigh : constants.empty_series, { name: 'Entry Breakout', color: '#26A69A', thickness: 2 });
paint(myShowExitLine ? myExitLow : constants.empty_series, { name: 'Exit Breakdown', color: '#EF5350', thickness: 2 });
paint(myShowAtrStop ? myAtrStopSeries : constants.empty_series, { name: 'ATR Stop', color: '#FB8C00', thickness: 2 });

const myBuyLabelSeries = for_every(myBuySignal, _b => _b ? 1 : null);
const mySellLabelSeries = for_every(mySellSignal, _s => _s ? 1 : null);

paint(myBuyLabelSeries, { name: 'Buy Signal Label', style: 'labels_below', color: '#00C853' });
paint(mySellLabelSeries, { name: 'Sell Signal Label', style: 'labels_above', color: '#D50000' });

const myCandleColors = for_every(myBuySignal, mySellSignal, (_b, _s) => _b ? 'green' : (_s ? 'red' : null));
color_candles(myCandleColors);

// Signal names changed to avoid clashing with the paint() line names
// above (the engine requires every paint/register_signal output name
// to be unique across the whole indicator).
register_signal(myBuySignal, 'Buy Signal Triggered');
register_signal(mySellSignal, 'Sell Signal Triggered');
register_signal(for_every(myPositionSize, _p => _p > 0), 'In Long Position');