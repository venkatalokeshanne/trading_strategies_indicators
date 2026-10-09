describe_indicator('Trend Pullback RSI and ATR Daily Stocks', 'price');

// ============================================================================
// INPUTS
// ============================================================================
const regimeTab = input.tab('Regime');
const myEmaFastLen = regimeTab.number('EMA Fast Length', 50, { min: 10, max: 500 });
const myEmaSlowLen = regimeTab.number('EMA Slow Length', 200, { min: 50, max: 500 });

const rsiTab = input.tab('RSI and ATR');
const rsiRow1 = rsiTab.row();
const myRsiLen = rsiRow1.number('RSI Length', 14, { min: 2, max: 100 });
const myRsiPullback = rsiRow1.number('RSI Pullback Cross Level', 50, { min: 30, max: 70 });
const rsiRow2 = rsiTab.row();
const myRsiZoneLow = rsiRow2.number('RSI Pullback Zone Low', 40, { min: 20, max: 50 });
const myAtrLen = rsiRow2.number('ATR Length', 14, { min: 5, max: 100 });

const multTab = input.tab('Multipliers and Range');
const multRow = multTab.row();
const myAtrStopMult = multRow.number('ATR Stop Multiplier', 2.0, { min: 0.5, max: 20, step: 0.1 });
const myAtrTpMult = multRow.number('ATR TP Multiplier', 4.0, { min: 0.5, max: 20, step: 0.1 });
const myRiskPerTrade = multTab.number('Risk Percent Per Trade', 1.0, { min: 0.1, max: 5.0, step: 0.1 });

// Date range (as Unix timestamps in seconds). Approximation of Pine's input.time.
const dateRow = multTab.row();
const myStartDate = dateRow.number('Start Date (Unix seconds)', 1514764800, { min: 0, max: 9999999999 });
const myEndDate = dateRow.number('End Date (Unix seconds)', 4070908800, { min: 0, max: 9999999999 });

// ============================================================================
// INDICATORS
// ============================================================================
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

const myCandleCount = close.length;

// Output series
const myStopLine = series_of(null);
const myTpLine = series_of(null);
const myBuySignalMarks = series_of(null);
const myRegimeBrokenMarks = series_of(null);

const myLongEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myRegimeBrokenSignal = series_of(false);

// Simulated single-position state machine (pyramiding = 0, long only)
let myPositionSize = 0;
let myEntryPrice = null;
let myStopPrice = null;
let myTpPrice = null;
let myLastPullbackBarIndex = -9999;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myCloseValue = close[myIndex];
	const myHighValue = high[myIndex];
	const myLowValue = low[myIndex];
	const myRsiValue = myRsi[myIndex];
	const myPrevRsiValue = myIndex > 0 ? myRsi[myIndex - 1] : null;
	const myAtrValue = myAtr[myIndex];
	const myEmaFastValue = myEmaFast[myIndex];
	const myEmaSlowValue = myEmaSlow[myIndex];
	const myPrevEmaFastValue = myIndex > 0 ? myEmaFast[myIndex - 1] : null;
	const myPrevEmaSlowValue = myIndex > 0 ? myEmaSlow[myIndex - 1] : null;
	const myTimeValue = time[myIndex];

	// ta.barssince(rsi <= rsiPullback and rsi >= rsiZoneLow) <= 5
	if (myRsiValue !== null && myRsiValue !== undefined &&
		myRsiValue <= myRsiPullback && myRsiValue >= myRsiZoneLow) {
		myLastPullbackBarIndex = myIndex;
	}

	const myPullbackHappened = (myIndex - myLastPullbackBarIndex) <= 5 && myLastPullbackBarIndex >= 0;

	// ta.crossover(rsi, rsiPullback)
	const myRsiCrossUp = myPrevRsiValue !== null && myRsiValue !== null &&
		myPrevRsiValue <= myRsiPullback && myRsiValue > myRsiPullback;

	const myBullRegime = myEmaFastValue > myEmaSlowValue && myCloseValue > myEmaFastValue;
	const myAtrPctOfPrice = (myAtrValue / myCloseValue) * 100;
	const myVolOk = myAtrPctOfPrice > 1.0;
	const myInDateRange = myTimeValue >= myStartDate && myTimeValue <= myEndDate;

	const myLongCondition = myBullRegime && myPullbackHappened && myRsiCrossUp && myVolOk && myInDateRange;

	// Exits checked before entries, mimicking strategy.exit / strategy.close order
	let myExitHappenedThisBar = false;
	let myRegimeBrokenThisBar = false;

	if (myPositionSize > 0) {
		// Regime broken close (crossunder emaFast, emaSlow)
		const myCrossUnder = myPrevEmaFastValue !== null && myPrevEmaFastValue >= myPrevEmaSlowValue &&
			myEmaFastValue < myEmaSlowValue;

		if (myCrossUnder) {
			myPositionSize = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTpPrice = null;
			myRegimeBrokenThisBar = true;
		}
		else {
			// Stop / Limit exit, checked using current bar's high/low
			if (myLowValue <= myStopPrice) {
				myPositionSize = 0;
				myEntryPrice = null;
				myStopPrice = null;
				myTpPrice = null;
				myExitHappenedThisBar = true;
			}
			else if (myHighValue >= myTpPrice) {
				myPositionSize = 0;
				myEntryPrice = null;
				myStopPrice = null;
				myTpPrice = null;
				myExitHappenedThisBar = true;
			}
		}
	}

	let myEntryHappenedThisBar = false;
	if (myLongCondition && myPositionSize === 0) {
		myEntryPrice = myCloseValue;
		myStopPrice = myCloseValue - myAtrStopMult * myAtrValue;
		myTpPrice = myCloseValue + myAtrTpMult * myAtrValue;
		myPositionSize = 1;
		myEntryHappenedThisBar = true;
	}

	myStopLine[myIndex] = myPositionSize > 0 ? myStopPrice : null;
	myTpLine[myIndex] = myPositionSize > 0 ? myTpPrice : null;
	myBuySignalMarks[myIndex] = myEntryHappenedThisBar ? myLowValue : null;
	myRegimeBrokenMarks[myIndex] = myRegimeBrokenThisBar ? myHighValue : null;

	myLongEntrySignal[myIndex] = myEntryHappenedThisBar;
	myExitSignal[myIndex] = myExitHappenedThisBar;
	myRegimeBrokenSignal[myIndex] = myRegimeBrokenThisBar;
}

// ============================================================================
// VISUALIZATION
// ============================================================================
paint(myEmaFast, { name: 'EMA Fast', color: '#2962FF', thickness: 2 });
paint(myEmaSlow, { name: 'EMA Slow', color: '#FF9800', thickness: 2 });
paint(myStopLine, { name: 'Stop', color: '#EF5350', style: 'line' });
paint(myTpLine, { name: 'Take Profit', color: '#26A69A', style: 'line' });
paint(myBuySignalMarks, { name: 'Buy Signal', style: 'labels_below', color: '#26A69A' });
// Renamed this painted line so its name no longer collides with the
// register_signal() name below (names must be unique across the indicator).
paint(myRegimeBrokenMarks, { name: 'Regime Broken Mark', style: 'labels_above', color: '#EF5350' });

// ============================================================================
// SCANNER AND STRATEGY SIGNALS
// ============================================================================
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Stop or Target Exit');
// Renamed to avoid name collision with the paint() label above.
register_signal(myRegimeBrokenSignal, 'Regime Broken Signal');