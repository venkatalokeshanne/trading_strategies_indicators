describe_indicator('Stock Breakout Momentum Strategy', 'price');

// ===================== INPUTS =====================
const myMainTab = input.tab('Main');
const myBreakoutLength = myMainTab.number('Breakout Lookback (bars)', 20, { min: 1 });
const myBarsInTrade = myMainTab.number('Time-Based Exit (bars)', 20, { min: 1 });
const myAtrLength = myMainTab.number('ATR Length', 14, { min: 1 });
const myAtrMultiplier = myMainTab.number('ATR Stop Multiplier', 2.0, { min: 0.1 });
// Shortened from "Percent of Equity to Allocate per Trade (%)" to fit input name length limit
const myAccountRiskPct = myMainTab.number('Equity Allocation %', 100.0, { min: 1.0, max: 500.0 });
const myAllowShort = myMainTab.boolean('Allow Short Entries', true);

const myProfitTab = input.tab('Profit Target');
const myUseProfitTarget = myProfitTab.boolean('Use Profit Target', true);
const myProfitTargetATRMult = myProfitTab.number('Profit Target ATR Mult', 3.0, { min: 0.1 });

const myFiltersTab = input.tab('Filters');
const myUseTrendFilter = myFiltersTab.boolean('Use Trend Filter', true);
const myTrendLength = myFiltersTab.number('Trend SMA Length', 50, { min: 1 });
const myUseVolumeFilter = myFiltersTab.boolean('Use Volume Filter', true);
const myVolLength = myFiltersTab.number('Volume SMA Length', 20, { min: 1 });
const myVolumeMultiplier = myFiltersTab.number('Volume Multiplier', 1.2, { min: 0.1 });

// ===================== CALCULATIONS (done once, outside loops) =====================
const myHighestHigh = highest(high, myBreakoutLength);
const myLowestLow = lowest(low, myBreakoutLength);
const myAtrValue = atr(high, low, close, myAtrLength);
const myTrendSMA = sma(close, myTrendLength);
const myVolSMA = sma(volume, myVolLength);
const myNumCandles = close.length;

// Note: there is no `strategy.equity` concept in TrendSpider custom indicators,
// so position sizing (sharesToTrade) from the original Pine script cannot be
// reproduced here. This script focuses on reproducing the signal logic
// (entries/exits, stops, targets) exactly, not the equity curve or sizing.

// Output series
const myLongTrailingStop = series_of(null);
const myShortTrailingStop = series_of(null);
const myLongProfitTarget = series_of(null);
const myShortProfitTarget = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

// Simulation state (mirrors Pine `var` persistent variables)
let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myLongSL = null;
let myShortSL = null;
let myLongTP = null;
let myShortTP = null;
let myEntryBarIndex = null;

for (let myIndex = 1; myIndex < myNumCandles; myIndex += 1) {
	const myPrevHighestHigh = myHighestHigh[myIndex - 1];
	const myPrevLowestLow = myLowestLow[myIndex - 1];
	const myAtrAtIndex = myAtrValue[myIndex];
	const myTrendAtIndex = myTrendSMA[myIndex];
	const myVolAtIndex = myVolSMA[myIndex];

	const myDataReady = myPrevHighestHigh != null && myPrevLowestLow != null && myAtrAtIndex != null &&
		(!myUseTrendFilter || myTrendAtIndex != null) &&
		(!myUseVolumeFilter || myVolAtIndex != null);

	const myTrendOKLong = !myUseTrendFilter || close[myIndex] > myTrendAtIndex;
	const myTrendOKShort = !myUseTrendFilter || close[myIndex] < myTrendAtIndex;
	const myVolOK = !myUseVolumeFilter || volume[myIndex] > (myVolAtIndex * myVolumeMultiplier);

	const myLongBreakout = myDataReady && close[myIndex] > myPrevHighestHigh && myTrendOKLong && myVolOK;
	const myShortBreakout = myAllowShort && myDataReady && close[myIndex] < myPrevLowestLow && myTrendOKShort && myVolOK;

	let myJustEntered = false;

	// ===================== ENTRY =====================
	if (myLongBreakout && myPositionSize === 0) {
		myJustEntered = true;
		myEntryBarIndex = myIndex;
		myLongSL = open[myIndex] - myAtrAtIndex * myAtrMultiplier;
		myLongTP = myUseProfitTarget ? open[myIndex] + myAtrAtIndex * myProfitTargetATRMult : null;
		myPositionSize = 1;
		myLongEntrySignal[myIndex] = true;
	}

	if (myShortBreakout && myPositionSize === 0) {
		myJustEntered = true;
		myEntryBarIndex = myIndex;
		myShortSL = open[myIndex] + myAtrAtIndex * myAtrMultiplier;
		myShortTP = myUseProfitTarget ? open[myIndex] - myAtrAtIndex * myProfitTargetATRMult : null;
		myPositionSize = -1;
		myShortEntrySignal[myIndex] = true;
	}

	// ===================== TRAILING STOP UPDATE =====================
	if (myPositionSize > 0) {
		const myBaseSL = myLongSL != null ? myLongSL : open[myIndex];
		myLongSL = Math.max(myBaseSL, close[myIndex] - myAtrAtIndex * myAtrMultiplier);
	}
	if (myPositionSize < 0) {
		const myBaseSL = myShortSL != null ? myShortSL : open[myIndex];
		myShortSL = Math.min(myBaseSL, close[myIndex] + myAtrAtIndex * myAtrMultiplier);
	}

	// ===================== EXIT LOGIC =====================
	const myTimeExitLong = myPositionSize > 0 && myEntryBarIndex != null && (myIndex - myEntryBarIndex) >= myBarsInTrade;
	const myTimeExitShort = myPositionSize < 0 && myEntryBarIndex != null && (myIndex - myEntryBarIndex) >= myBarsInTrade;

	if (myPositionSize > 0) {
		if (myTimeExitLong) {
			myPositionSize = 0;
			myLongExitSignal[myIndex] = true;
		}
		else {
			// stop / limit check using this candle's high/low (approximation
			// of intrabar stop/limit fills, since Pine evaluates these live)
			const myHitStop = myLongSL != null && low[myIndex] <= myLongSL;
			const myHitTarget = myUseProfitTarget && myLongTP != null && high[myIndex] >= myLongTP;
			if (myHitStop || myHitTarget) {
				myPositionSize = 0;
				myLongExitSignal[myIndex] = true;
			}
		}
	}

	if (myPositionSize < 0) {
		if (myTimeExitShort) {
			myPositionSize = 0;
			myShortExitSignal[myIndex] = true;
		}
		else {
			const myHitStop = myShortSL != null && high[myIndex] >= myShortSL;
			const myHitTarget = myUseProfitTarget && myShortTP != null && low[myIndex] <= myShortTP;
			if (myHitStop || myHitTarget) {
				myPositionSize = 0;
				myShortExitSignal[myIndex] = true;
			}
		}
	}

	// ===================== RESET BLOCK =====================
	if (myPositionSize === 0 && !myJustEntered) {
		myLongSL = null;
		myShortSL = null;
		myLongTP = null;
		myShortTP = null;
		myEntryBarIndex = null;
	}

	// ===================== PLOTS (per-candle assignment) =====================
	myLongTrailingStop[myIndex] = myPositionSize > 0 ? myLongSL : null;
	myShortTrailingStop[myIndex] = myPositionSize < 0 ? myShortSL : null;
	myLongProfitTarget[myIndex] = myPositionSize > 0 ? myLongTP : null;
	myShortProfitTarget[myIndex] = myPositionSize < 0 ? myShortTP : null;
}

// ===================== PLOTS =====================
paint(myHighestHigh, { name: 'HighestHigh', color: '#26A69A', thickness: 1 });
paint(myLowestLow, { name: 'LowestLow', color: '#EF5350', thickness: 1 });
paint(myLongTrailingStop, { name: 'LongTrailingStop', color: '#00BCD4', thickness: 2, style: 'ladder' });
paint(myShortTrailingStop, { name: 'ShortTrailingStop', color: '#FF9800', thickness: 2, style: 'ladder' });
paint(myTrendSMA, { name: 'TrendSMA', color: '#FFEB3B', thickness: 1 });
paint(myLongProfitTarget, { name: 'LongProfitTarget', color: '#2962FF', thickness: 2, style: 'ladder' });
paint(myShortProfitTarget, { name: 'ShortProfitTarget', color: '#2962FF', thickness: 2, style: 'ladder' });

// ===================== SIGNALS (for Scanner, Alerts, Strategy Tester) =====================
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');