describe_indicator('Hull RSI Trend Rider Pro', 'price');

// --- Inputs ---
const myHullLength = input.number('Hull Base Length', 55, { min: 1 });
const myHullMult = input.number('Hull Multiplier', 10.0, { min: 0.1, step: 0.1 });
const myRsiLen = input.number('RSI Length', 14, { min: 1 });
const myRsiUpper = input.number('RSI Upper (Short Trigger)', 50, { min: 1, max: 99 });
const myRsiLower = input.number('RSI Lower (Long Trigger)', 50, { min: 1, max: 99 });
const myLookback = input.number('SL Lookback', 13, { min: 1 });
const myRrRatio = input.number('Risk Reward Ratio', 5.0, { min: 0.1, step: 0.1 });

// --- Calculations ---
// Pine does int(hullLength * hullMult); we replicate the truncation towards zero.
const myActualLength = Math.trunc(myHullLength * myHullMult);

const myHma = hullma(close, myActualLength);
const myRsiVal = rsi(close, myRsiLen);
const myLowestLow = lowest(low, myLookback);
const myHighestHigh = highest(high, myLookback);

// trendDir: hma > hma[1] ? 1 : -1. For the first candle, hma[1] is undefined;
// Pine's na comparisons make trendDir default to -1 there, we replicate that.
const myPrevHma = shift(myHma, 1);

// --- Simulated strategy state machine ---
// We simulate strategy.position_size, SL/TP levels and the "tradeTakenThisCycle"
// flag in a single sequential pass, since the Custom JS API has no built-in
// strategy engine equivalent. Entries are "next bar is not needed" here because
// Pine Script's strategy.entry() on this bar executes using this bar's close,
// matching how this script computes slPrice/tpPrice from the triggering bar.
const myTrendDir = series_of(null);
const myPositionSize = series_of(0);
const mySlPrice = series_of(null);
const myTpPrice = series_of(null);
const myLongEntry = series_of(false);
const myShortEntry = series_of(false);
const myTrendFlipExit = series_of(false);
const mySafetySlExit = series_of(false);
const myTakeProfitExit = series_of(false);

let myTradeTakenThisCycle = false;
let myPrevTrendDir = -1;
let myCurrPosition = 0;
let myCurrSl = null;
let myCurrTp = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myHmaNow = myHma[myIndex];
	const myHmaPrev = myPrevHma[myIndex];

	let myDir = -1;
	if (myHmaNow != null && myHmaPrev != null) {
		myDir = myHmaNow > myHmaPrev ? 1 : -1;
	}
	myTrendDir[myIndex] = myDir;

	const myHullChanged = myIndex > 0 && myDir !== myPrevTrendDir;
	if (myHullChanged) {
		myTradeTakenThisCycle = false;
	}

	const myRsiNow = myRsiVal[myIndex];
	const myRsiPrev = myIndex > 0 ? myRsiVal[myIndex - 1] : null;

	let myCrossUnderLower = false;
	let myCrossOverUpper = false;
	if (myRsiNow != null && myRsiPrev != null) {
		myCrossUnderLower = myRsiPrev >= myRsiLower && myRsiNow < myRsiLower;
		myCrossOverUpper = myRsiPrev <= myRsiUpper && myRsiNow > myRsiUpper;
	}

	const myLongCondition = (myDir === 1) && myCrossUnderLower && !myTradeTakenThisCycle;
	const myShortCondition = (myDir === -1) && myCrossOverUpper && !myTradeTakenThisCycle;

	let myLongEntryNow = false;
	let myShortEntryNow = false;
	let myTrendFlipExitNow = false;
	let mySafetySlExitNow = false;
	let myTakeProfitExitNow = false;

	// entries, only when flat
	if (myLongCondition && myCurrPosition === 0) {
		myCurrSl = myLowestLow[myIndex];
		const myRisk = close[myIndex] - myCurrSl;
		myCurrTp = close[myIndex] + (myRisk * myRrRatio);
		myCurrPosition = 1;
		myTradeTakenThisCycle = true;
		myLongEntryNow = true;
	}
	else if (myShortCondition && myCurrPosition === 0) {
		myCurrSl = myHighestHigh[myIndex];
		const myRisk = myCurrSl - close[myIndex];
		myCurrTp = close[myIndex] - (myRisk * myRrRatio);
		myCurrPosition = -1;
		myTradeTakenThisCycle = true;
		myShortEntryNow = true;
	}

	// trend flip exit
	if (myCurrPosition > 0 && myDir === -1) {
		myCurrPosition = 0;
		myCurrSl = null;
		myCurrTp = null;
		myTrendFlipExitNow = true;
	}
	else if (myCurrPosition < 0 && myDir === 1) {
		myCurrPosition = 0;
		myCurrSl = null;
		myCurrTp = null;
		myTrendFlipExitNow = true;
	}

	// SL / TP exit (engine managed, checked against this bar's high/low)
	if (myCurrPosition !== 0 && myCurrSl != null && myCurrTp != null) {
		if (myCurrPosition > 0) {
			if (low[myIndex] <= myCurrSl) {
				mySafetySlExitNow = true;
				myCurrPosition = 0;
				myCurrSl = null;
				myCurrTp = null;
			}
			else if (high[myIndex] >= myCurrTp) {
				myTakeProfitExitNow = true;
				myCurrPosition = 0;
				myCurrSl = null;
				myCurrTp = null;
			}
		}
		else {
			if (high[myIndex] >= myCurrSl) {
				mySafetySlExitNow = true;
				myCurrPosition = 0;
				myCurrSl = null;
				myCurrTp = null;
			}
			else if (low[myIndex] <= myCurrTp) {
				myTakeProfitExitNow = true;
				myCurrPosition = 0;
				myCurrSl = null;
				myCurrTp = null;
			}
		}
	}

	myPositionSize[myIndex] = myCurrPosition;
	mySlPrice[myIndex] = myCurrPosition !== 0 ? myCurrSl : null;
	myTpPrice[myIndex] = myCurrPosition !== 0 ? myCurrTp : null;
	myLongEntry[myIndex] = myLongEntryNow;
	myShortEntry[myIndex] = myShortEntryNow;
	myTrendFlipExit[myIndex] = myTrendFlipExitNow;
	mySafetySlExit[myIndex] = mySafetySlExitNow;
	myTakeProfitExit[myIndex] = myTakeProfitExitNow;

	myPrevTrendDir = myDir;
}

const myHmaColor = for_every(myTrendDir, _dir => _dir === 1 ? '#26A69A' : '#EF5350');

paint(myHma, { name: 'Hull Suite', color: myHmaColor, thickness: 3 });
paint(mySlPrice, { name: 'Stop Loss', color: 'red', style: 'ladder' });
paint(myTpPrice, { name: 'Take Profit', color: 'lime', style: 'ladder' });

// --- Signals for scanners / alerts / strategy tester ---
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myTrendFlipExit, 'Trend Flip Exit');
register_signal(mySafetySlExit, 'Safety SL Exit');
register_signal(myTakeProfitExit, 'Take Profit Exit');