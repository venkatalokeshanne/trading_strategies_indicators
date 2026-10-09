describe_indicator('EMA and Fib Confluence with Targets and Trailing', 'price');

// --- INPUTS ---
const emaTab = input.tab('EMA Trend Settings');
const fastEmaLen = emaTab.number('Fast EMA Length', 9, { min: 1, max: 500 });
const slowEmaLen = emaTab.number('Slow EMA Length', 21, { min: 1, max: 500 });

const fibTab = input.tab('Fibonacci Levels');
const fibLookback = fibTab.number('Fibonacci Lookback Period', 50, { min: 1, max: 1000 });
const fibLevelEntry = fibTab.number('Fib Entry Target Ratio', 0.618, { min: 0, max: 1 });

const tpTab = input.tab('Take Profit Settings');
const tp1PctInput = tpTab.number('Target 1 (%)', 1.0, { min: 0, max: 100 });
const tp2PctInput = tpTab.number('Target 2 (%)', 2.0, { min: 0, max: 100 });
const tp3PctInput = tpTab.number('Target 3 (%)', 3.5, { min: 0, max: 100 });

const scalingTab = input.tab('Position Scaling');
const tp1Qty = scalingTab.number('Target 1 Close Qty Percent', 33.0, { min: 0, max: 100 });
const tp2Qty = scalingTab.number('Target 2 Close Qty Percent', 33.0, { min: 0, max: 100 });
const tp3Qty = scalingTab.number('Target 3 Close Qty Percent', 34.0, { min: 0, max: 100 });

const trailTab = input.tab('Trailing Stop Settings');
const trailPctInput = trailTab.number('Trailing Distance Percent', 1.5, { min: 0, max: 100 });

const tp1Pct = tp1PctInput / 100;
const tp2Pct = tp2PctInput / 100;
const tp3Pct = tp3PctInput / 100;
const trailPct = trailPctInput / 100;

// --- CALCULATIONS (computed outside loops, as required) ---
const myFastEma = ema(close, fastEmaLen);
const mySlowEma = ema(close, slowEmaLen);

const myHighestHigh = highest(high, fibLookback);
const myLowestLow = lowest(low, fibLookback);
const myPriceRange = sub(myHighestHigh, myLowestLow);

const myFibLongLevel = sub(myHighestHigh, mult(myPriceRange, fibLevelEntry));
const myFibShortLevel = add(myLowestLow, mult(myPriceRange, fibLevelEntry));

paint(myFastEma, { name: 'Fast EMA', color: '#2ecc71', thickness: 2 });
paint(mySlowEma, { name: 'Slow EMA', color: '#e74c3c', thickness: 2 });

// --- STATE MACHINE (sequential, cannot be vectorized, uses a plain loop over precomputed series only) ---
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myCloseLongSignal = series_of(false);
const myCloseShortSignal = series_of(false);

const myCount = close.length;
let myEntryPrice = null;
let myT1Price = null;
let myT2Price = null;
let myT3Price = null;
let myTrailingStop = null;
let myActivePositionType = 0; // 1 = Long, -1 = Short, 0 = None

for (let myIndex = 0; myIndex < myCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myFast = myFastEma[myIndex];
	const mySlow = mySlowEma[myIndex];
	const myPrevFast = myIndex > 0 ? myFastEma[myIndex - 1] : null;
	const myPrevSlow = myIndex > 0 ? mySlowEma[myIndex - 1] : null;
	const myLongLevel = myFibLongLevel[myIndex];
	const myShortLevel = myFibShortLevel[myIndex];
	const myPrevLongLevel = myIndex > 0 ? myFibLongLevel[myIndex - 1] : null;
	const myPrevShortLevel = myIndex > 0 ? myFibShortLevel[myIndex - 1] : null;

	// ta.crossover / ta.crossunder replicated manually
	const myCrossoverLong = myPrevClose != null && myLongLevel != null && myPrevLongLevel != null &&
		myPrevClose <= myPrevLongLevel && myClose > myLongLevel;
	const myCrossunderShort = myPrevClose != null && myShortLevel != null && myPrevShortLevel != null &&
		myPrevClose >= myPrevShortLevel && myClose < myShortLevel;
	const myCrossunderEma = myPrevFast != null && myPrevSlow != null &&
		myPrevFast >= myPrevSlow && myFast < mySlow;
	const myCrossoverEma = myPrevFast != null && myPrevSlow != null &&
		myPrevFast <= myPrevSlow && myFast > mySlow;

	const myBuyConfluence = (myFast > mySlow) && myCrossoverLong;
	const mySellConfluence = (myFast < mySlow) && myCrossunderShort;

	let myBuyFired = false;
	let mySellFired = false;
	let myCloseLongFired = false;
	let myCloseShortFired = false;

	if (myBuyConfluence && myActivePositionType == 0) {
		myEntryPrice = myClose;
		myT1Price = myClose * (1 + tp1Pct);
		myT2Price = myClose * (1 + tp2Pct);
		myT3Price = myClose * (1 + tp3Pct);
		myTrailingStop = myClose * (1 - trailPct);
		myActivePositionType = 1;
		myBuyFired = true;
	}

	if (mySellConfluence && myActivePositionType == 0) {
		myEntryPrice = myClose;
		myT1Price = myClose * (1 - tp1Pct);
		myT2Price = myClose * (1 - tp2Pct);
		myT3Price = myClose * (1 - tp3Pct);
		myTrailingStop = myClose * (1 + trailPct);
		myActivePositionType = -1;
		mySellFired = true;
	}

	if (myActivePositionType == 1) {
		if (myClose * (1 - trailPct) > myTrailingStop) {
			myTrailingStop = myClose * (1 - trailPct);
		}
		if (myClose <= myTrailingStop || myCrossunderEma) {
			myCloseLongFired = true;
			myActivePositionType = 0;
		}
	}

	if (myActivePositionType == -1) {
		if (myClose * (1 + trailPct) < myTrailingStop) {
			myTrailingStop = myClose * (1 + trailPct);
		}
		if (myClose >= myTrailingStop || myCrossoverEma) {
			myCloseShortFired = true;
			myActivePositionType = 0;
		}
	}

	myBuySignal[myIndex] = myBuyFired;
	mySellSignal[myIndex] = mySellFired;
	myCloseLongSignal[myIndex] = myCloseLongFired;
	myCloseShortSignal[myIndex] = myCloseShortFired;
}

// --- SIGNALS (always registered, unconditionally) ---
register_signal(myBuySignal, 'Long Entry');
register_signal(mySellSignal, 'Short Entry');
register_signal(myCloseLongSignal, 'Long Exit Trailing Stop or Reverse Cross');
register_signal(myCloseShortSignal, 'Short Exit Trailing Stop or Reverse Cross');

// --- VISUAL MARKERS FOR ENTRIES/EXITS ---
const myBuyMarker = for_every(myBuySignal, close, (_buy, _close) => _buy ? _close : null);
const mySellMarker = for_every(mySellSignal, close, (_sell, _close) => _sell ? _close : null);
const myCloseLongMarker = for_every(myCloseLongSignal, close, (_cl, _close) => _cl ? _close : null);
const myCloseShortMarker = for_every(myCloseShortSignal, close, (_cs, _close) => _cs ? _close : null);

paint(myBuyMarker, { name: 'Long Entry Marker', style: 'labels_below', color: '#2ecc71', thickness: 3 });
paint(mySellMarker, { name: 'Short Entry Marker', style: 'labels_above', color: '#e74c3c', thickness: 3 });
paint(myCloseLongMarker, { name: 'Long Exit Marker', style: 'labels_above', color: '#3498db', thickness: 3 });
paint(myCloseShortMarker, { name: 'Short Exit Marker', style: 'labels_below', color: '#f39c12', thickness: 3 });