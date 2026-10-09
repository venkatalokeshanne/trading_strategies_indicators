describe_indicator('Institutional OB Entry Exit SL Strategy', 'price');

// Inputs, grouped in tabs for readability
const myStructureTab = input.tab('Structure');
const myStructureLen = myStructureTab.number('Structure Lookback', 20, { min: 5, max: 200 });
const myEmaRow = myStructureTab.row();
const myFastEmaLen = myEmaRow.number('Fast EMA', 50, { min: 1, max: 500 });
const mySlowEmaLen = myEmaRow.number('Slow EMA', 200, { min: 1, max: 500 });

const myOscTab = input.tab('Oscillators');
const myRsiLen = myOscTab.number('RSI Length', 14, { min: 1, max: 200 });
const myStochRow = myOscTab.row();
const myStochLen = myStochRow.number('Stochastic Length', 14, { min: 1, max: 200 });
const mySmoothK = myStochRow.number('Stoch K Smoothing', 3, { min: 1, max: 50 });
const mySmoothD = myStochRow.number('Stoch D Smoothing', 3, { min: 1, max: 50 });

const myRiskTab = input.tab('Risk');
const myAtrLen = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrBuffer = myRiskTab.number('Stop Loss ATR Buffer', 0.25, { min: 0, max: 10, step: 0.05 });
const myRiskReward = myRiskTab.number('Risk Reward', 2.0, { min: 0.1, max: 20, step: 0.25 });

// Core indicators
const myEmaFast = ema(close, myFastEmaLen);
const myEmaSlow = ema(close, mySlowEmaLen);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, myAtrLen);
const myStochRaw = stochastic(close, high, low, myStochLen);
const myK = sma(myStochRaw, mySmoothK);
const myD = sma(myK, mySmoothD);

// Market structure: highest/lowest of PREVIOUS candle's high/low over lookback
const myShiftedHigh = shift(high, 1);
const myShiftedLow = shift(low, 1);
const myPrevHigh = highest(myShiftedHigh, myStructureLen);
const myPrevLow = lowest(myShiftedLow, myStructureLen);

const myLength = close.length;

// Output series
const myBullObHighOut = series_of(null);
const myBullObLowOut = series_of(null);
const myBearObHighOut = series_of(null);
const myBearObLowOut = series_of(null);
const myValidBuyOut = series_of(false);
const myValidSellOut = series_of(false);
const myBuyStopOut = series_of(null);
const myBuyTargetOut = series_of(null);
const mySellStopOut = series_of(null);
const mySellTargetOut = series_of(null);
const myBuyShapeOut = series_of(null);
const mySellShapeOut = series_of(null);

// Stateful tracking (equivalent of ta.valuewhen/ta.barssince), computed in a
// single forward pass since these are inherently sequential operations
let myLastBearHigh = null;
let myLastBearLow = null;
let myLastBullHigh = null;
let myLastBullLow = null;
let myBullObHigh = null;
let myBullObLow = null;
let myBearObHigh = null;
let myBearObLow = null;
let myBarsSinceBull = null;
let myBarsSinceBear = null;
let myPrevBuySignal = false;
let myPrevSellSignal = false;

// Approximate syminfo.mintick using current decimals
const myMinTick = Math.pow(10, -(current.decimals || 2));

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myClose = close[myIndex];
	const myOpen = open[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];

	const myBullBOS = myPrevHigh[myIndex] != null && myClose > myPrevHigh[myIndex];
	const myBearBOS = myPrevLow[myIndex] != null && myClose < myPrevLow[myIndex];

	// Track last bearish / bullish candle extremes
	if (myClose < myOpen) {
		myLastBearHigh = myHigh;
		myLastBearLow = myLow;
	}
	if (myClose > myOpen) {
		myLastBullHigh = myHigh;
		myLastBullLow = myLow;
	}

	// Update order block levels on BOS events
	if (myBullBOS) {
		myBullObHigh = myLastBearHigh;
		myBullObLow = myLastBearLow;
	}
	if (myBearBOS) {
		myBearObHigh = myLastBullHigh;
		myBearObLow = myLastBullLow;
	}

	// Bars since BOS
	myBarsSinceBull = myBullBOS ? 0 : (myBarsSinceBull == null ? null : myBarsSinceBull + 1);
	myBarsSinceBear = myBearBOS ? 0 : (myBarsSinceBear == null ? null : myBarsSinceBear + 1);

	const myBullActive = myBarsSinceBull != null && (myBarsSinceBear == null || myBarsSinceBull < myBarsSinceBear);
	const myBearActive = myBarsSinceBear != null && (myBarsSinceBull == null || myBarsSinceBear < myBarsSinceBull);

	const myEmaBull = myEmaFast[myIndex] > myEmaSlow[myIndex] && myClose > myEmaFast[myIndex];
	const myEmaBear = myEmaFast[myIndex] < myEmaSlow[myIndex] && myClose < myEmaFast[myIndex];

	const myRsiBull = myRsiVal[myIndex] > 50;
	const myRsiBear = myRsiVal[myIndex] < 50;

	const myStochBull = myK[myIndex] > myD[myIndex] && myK[myIndex] < 80;
	const myStochBear = myK[myIndex] < myD[myIndex] && myK[myIndex] > 20;

	const myInBullOB = myBullActive && myBullObHigh != null && myLow <= myBullObHigh && myHigh >= myBullObLow;
	const myInBearOB = myBearActive && myBearObHigh != null && myHigh >= myBearObLow && myLow <= myBearObHigh;

	const myBullMid = (myBullObHigh + myBullObLow) / 2;
	const myBearMid = (myBearObHigh + myBearObLow) / 2;

	const myBuySignal = myInBullOB && myClose > myBullMid && myEmaBull && myRsiBull && myStochBull;
	const mySellSignal = myInBearOB && myClose < myBearMid && myEmaBear && myRsiBear && myStochBear;

	const myBuyEntry = myBuySignal && !myPrevBuySignal;
	const mySellEntry = mySellSignal && !myPrevSellSignal;

	const myBuyStop = myBullObLow - myAtrVal[myIndex] * myAtrBuffer;
	const myBuyRisk = myClose - myBuyStop;
	const myBuyTarget = myClose + myBuyRisk * myRiskReward;

	const mySellStop = myBearObHigh + myAtrVal[myIndex] * myAtrBuffer;
	const mySellRisk = mySellStop - myClose;
	const mySellTarget = myClose - mySellRisk * myRiskReward;

	const myValidBuy = myBuyEntry && myBuyRisk > myMinTick;
	const myValidSell = mySellEntry && mySellRisk > myMinTick;

	myBullObHighOut[myIndex] = myBullActive ? myBullObHigh : null;
	myBullObLowOut[myIndex] = myBullActive ? myBullObLow : null;
	myBearObHighOut[myIndex] = myBearActive ? myBearObHigh : null;
	myBearObLowOut[myIndex] = myBearActive ? myBearObLow : null;

	myValidBuyOut[myIndex] = myValidBuy;
	myValidSellOut[myIndex] = myValidSell;

	myBuyStopOut[myIndex] = myValidBuy ? myBuyStop : null;
	myBuyTargetOut[myIndex] = myValidBuy ? myBuyTarget : null;
	mySellStopOut[myIndex] = myValidSell ? mySellStop : null;
	mySellTargetOut[myIndex] = myValidSell ? mySellTarget : null;

	myBuyShapeOut[myIndex] = myValidBuy ? constants.icons.triangle_up : null;
	mySellShapeOut[myIndex] = myValidSell ? constants.icons.triangle_down : null;

	myPrevBuySignal = myBuySignal;
	myPrevSellSignal = mySellSignal;
}

// Plots
paint(myEmaFast, { name: 'Fast EMA', color: '#FF9800', thickness: 1 });
paint(myEmaSlow, { name: 'Slow EMA', color: '#2962FF', thickness: 1 });
paint(myBullObHighOut, { name: 'Bullish OB High', color: '#26A69A', style: 'line' });
paint(myBullObLowOut, { name: 'Bullish OB Low', color: '#26A69A', style: 'line' });
paint(myBearObHighOut, { name: 'Bearish OB High', color: '#EF5350', style: 'line' });
paint(myBearObLowOut, { name: 'Bearish OB Low', color: '#EF5350', style: 'line' });
paint(myBuyShapeOut, { name: 'Buy Entry Marker', style: 'labels_below', color: '#26A69A' });
paint(mySellShapeOut, { name: 'Sell Entry Marker', style: 'labels_above', color: '#EF5350' });
paint(myBuyStopOut, { name: 'Buy Stop Loss', color: '#EF5350', style: 'dotted', thickness: 2 });
paint(myBuyTargetOut, { name: 'Buy Target', color: '#26A69A', style: 'dotted', thickness: 2 });
paint(mySellStopOut, { name: 'Sell Stop Loss', color: '#EF5350', style: 'dotted', thickness: 2 });
paint(mySellTargetOut, { name: 'Sell Target', color: '#26A69A', style: 'dotted', thickness: 2 });

// Signals for scanners, alerts and strategy tester
// Renamed to avoid colliding with the painted "Buy Entry Marker"/"Sell Entry Marker"
// line names, which was the cause of the "signal already exists" error.
register_signal(myValidBuyOut, 'Buy Entry Signal');
register_signal(myValidSellOut, 'Sell Entry Signal');