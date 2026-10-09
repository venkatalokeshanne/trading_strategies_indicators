describe_indicator('Axis Reversal', 'price');

// ─── Inputs ──────────────────────────────────────────────────────────────
const myTab = input.tab('Axis Reversal');
const myRow1 = myTab.row();
const mySensitivity = myRow1.number('Sensitivity', 50, { min: 1, max: 500 });
const myAtrPeriod = myRow1.number('ATR Period', 10, { min: 1, max: 200 });
const myRow2 = myTab.row();
const myAtrMult = myRow2.number('ATR Mult', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myTakeProfitPercent = myRow2.number('Take Profit %', 1.5, { min: 0.01, max: 100, step: 0.01 });
const mySlopeRow = myTab.row();
const myStopLossPercent = mySlopeRow.number('Stop Loss %', 1.0, { min: 0.01, max: 100, step: 0.01 });

// Note: Pine strategy.entry/exit (actual order execution, TP/SL brackets) has
// no equivalent in Custom JS indicators. We expose Long/Short entry signals
// via register_signal() so they can be used in TrendSpider's Strategy Tester,
// where TP/SL can be configured using the same percentages as inputs above.

// ─── Core math ───────────────────────────────────────────────────────────
const myRsi = rsi(close, 14);
const myAtr = atr(high, low, close, myAtrPeriod);
const myHl2 = hl2;
const myStep = Math.max(1, Math.floor(mySensitivity / 10));
const myHiLevel = highest(high, mySensitivity);
const myLoLevel = lowest(low, mySensitivity);
const myCandleCount = close.length;

// recursive series (mirrors Pine's "var" persistent variables)
const myUp = series_of(null);
const myDn = series_of(null);
const myTrend = series_of(null);
const myHiActive = series_of(null);
const myLoActive = series_of(null);
const myTSw = series_of(null);
const myBSw = series_of(null);

// these two hold the final buy/sell reversal flags per candle
// (fixed: previously referenced undefined "myRevSellSeries"/"myRevBuySeries")
const myRevBuySeries = series_of(false);
const myRevSellSeries = series_of(false);

let myPrevUp = null;
let myPrevDn = null;
let myPrevTrend = 1;
let myPrevHiActive = 0;
let myPrevLoActive = 0;
let myPrevTSw = 0;
let myPrevBSw = 0;
let mySinceBelow30 = Infinity;
let mySinceAbove70 = Infinity;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// barssince trackers
	if (myRsi[myIndex] < 30) { mySinceBelow30 = 0; } else { mySinceBelow30 += 1; }
	if (myRsi[myIndex] > 70) { mySinceAbove70 = 0; } else { mySinceAbove70 += 1; }

	const myRsiDnZone = mySinceBelow30 < 10;
	const myRsiUpZone = mySinceAbove70 < 10;

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;

	let myCurUp;
	if (myPrevUp !== null && myPrevClose !== null && myPrevClose > myPrevUp) {
		myCurUp = Math.max(myHl2[myIndex] - myAtrMult * myAtr[myIndex], myPrevUp);
	}
	else {
		myCurUp = myHl2[myIndex] - myAtrMult * myAtr[myIndex];
	}

	let myCurDn;
	if (myPrevDn !== null && myPrevClose !== null && myPrevClose < myPrevDn) {
		myCurDn = Math.min(myHl2[myIndex] + myAtrMult * myAtr[myIndex], myPrevDn);
	}
	else {
		myCurDn = myHl2[myIndex] + myAtrMult * myAtr[myIndex];
	}

	let myCurTrend = myPrevTrend;
	if (myPrevTrend === -1 && myPrevDn !== null && close[myIndex] > myPrevDn) {
		myCurTrend = 1;
	}
	else if (myPrevTrend === 1 && myPrevUp !== null && close[myIndex] < myPrevUp) {
		myCurTrend = -1;
	}

	// hi_active / lo_active logic, referencing values "step" candles back
	let myCurHiActive = myPrevHiActive;
	const myHiLevelStepAgo = (myIndex - myStep >= 0) ? myHiLevel[myIndex - myStep] : null;
	if (myHiLevelStepAgo !== null && myHiLevel[myIndex] !== myHiLevelStepAgo && close[myIndex] > myHiLevelStepAgo) {
		myCurHiActive = 1;
	}
	if (myCurTrend === -1 && myPrevTrend === 1) {
		myCurHiActive = 0;
	}

	let myCurLoActive = myPrevLoActive;
	const myLoLevelStepAgo = (myIndex - myStep >= 0) ? myLoLevel[myIndex - myStep] : null;
	if (myLoLevelStepAgo !== null && myLoLevel[myIndex] !== myLoLevelStepAgo && close[myIndex] < myLoLevelStepAgo) {
		myCurLoActive = 1;
	}
	if (myCurTrend === 1 && myPrevTrend === -1) {
		myCurLoActive = 0;
	}

	// t_sw / b_sw switches
	let myCurTSw;
	if (myCurTrend === -1 && myPrevTrend === 1) {
		myCurTSw = 0;
	}
	else if (myCurHiActive !== 0 && myCurTrend === 1) {
		myCurTSw = 1;
	}
	else {
		myCurTSw = myPrevTSw;
	}

	// renamed from "myRevSell" (which shadowed outer const) to "myIsRevSell"
	const myIsRevSell = (myPrevTSw === 1 && myCurTSw === 0 && myRsiUpZone);

	let myCurBSw;
	if (myCurTrend === 1 && myPrevTrend === -1) {
		myCurBSw = 0;
	}
	else if (myCurLoActive !== 0 && myCurTrend === -1) {
		myCurBSw = 1;
	}
	else {
		myCurBSw = myPrevBSw;
	}

	// renamed from "myRevBuy" (which shadowed outer const) to "myIsRevBuy"
	const myIsRevBuy = (myPrevBSw === 1 && myCurBSw === 0 && myRsiDnZone);

	myUp[myIndex] = myCurUp;
	myDn[myIndex] = myCurDn;
	myTrend[myIndex] = myCurTrend;
	myHiActive[myIndex] = myCurHiActive;
	myLoActive[myIndex] = myCurLoActive;
	myTSw[myIndex] = myCurTSw;
	myBSw[myIndex] = myCurBSw;

	// write to the series (fixed: write booleans directly, no undefined refs)
	myRevSellSeries[myIndex] = myIsRevSell;
	myRevBuySeries[myIndex] = myIsRevBuy;

	myPrevUp = myCurUp;
	myPrevDn = myCurDn;
	myPrevTrend = myCurTrend;
	myPrevHiActive = myCurHiActive;
	myPrevLoActive = myCurLoActive;
	myPrevTSw = myCurTSw;
	myPrevBSw = myCurBSw;
}

// ─── Lines (plotted only while "active", mirrors Pine's "linebr" break lines) ───
const myHiLine = series_of(null);
const myLoLine = series_of(null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	myHiLine[myIndex] = myHiActive[myIndex] ? myHiLevel[myIndex] : null;
	myLoLine[myIndex] = myLoActive[myIndex] ? myLoLevel[myIndex] : null;
}

paint(myHiLine, { name: 'Axis High', color: '#ff0055', thickness: 2, style: 'line' });
paint(myLoLine, { name: 'Axis Low', color: '#00ffcc', thickness: 2, style: 'line' });

// ─── Markers (Buy below bars, Sell above bars) ───
const myBuyMarker = series_of(null);
const mySellMarker = series_of(null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	myBuyMarker[myIndex] = myRevBuySeries[myIndex] ? low[myIndex] : null;
	mySellMarker[myIndex] = myRevSellSeries[myIndex] ? high[myIndex] : null;
}

paint(myBuyMarker, { name: 'Buy Marker', color: '#00ffcc', style: 'labels_below' });
paint(mySellMarker, { name: 'Sell Marker', color: '#ff0055', style: 'labels_above' });

// ─── Signals for scanner, alerts, strategy tester ───
register_signal(myRevBuySeries, 'Axis Reversal Buy');
register_signal(myRevSellSeries, 'Axis Reversal Sell');