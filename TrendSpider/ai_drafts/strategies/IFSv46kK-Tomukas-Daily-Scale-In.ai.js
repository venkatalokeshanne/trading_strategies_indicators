describe_indicator('Tomukas Sweep Reclaim Signals', 'price');

// This indicator reproduces the SIGNAL LOGIC of the Pine Script exactly
// (sweep detection + reclaim conditions). The position sizing, scale-in
// adds, equity-based quantities and the fixed % take profit are strategy
// (money management) concepts that do not exist in the Custom JS API,
// which only supports indicators (no simulated broker/equity). Those
// parts could not be reproduced here - see note below.

const swingTab = input.tab('Swing / Sweep');
const swingRow = swingTab.row();
const myLeftBars = swingRow.number('Swing Left', 8, { min: 1, max: 100 });
const myRightBars = swingRow.number('Swing Right', 8, { min: 1, max: 100 });
const myAtrLen = swingTab.number('ATR Length', 14, { min: 1, max: 200 });
const sweepRow = swingTab.row();
const myMinSweepATR = sweepRow.number('Min Sweep ATR', 0.05, { min: 0, max: 10, step: 0.01 });
const myMaxSweepATR = sweepRow.number('Max Sweep ATR', 0.80, { min: 0, max: 10, step: 0.01 });

const reclaimTab = input.tab('Reclaim');
const myReclaimBars = reclaimTab.number('Reclaim Window Bars', 3, { min: 0, max: 100 });
const myCloseBufferATR = reclaimTab.number('Reclaim Close Buffer ATR', 0.02, { min: 0, max: 5, step: 0.01 });
const myMinCloseLocation = reclaimTab.number('Min Close Location', 0.60, { min: 0, max: 1, step: 0.05 });
const myMinBodyATR = reclaimTab.number('Min Body ATR', 0.05, { min: 0, max: 5, step: 0.01 });

const biasTab = input.tab('Bias');
const myUseEMA = biasTab.boolean('Use EMA200 Bias', true);
const myEmaLen = biasTab.number('EMA Length', 200, { min: 1, max: 1000 });

// mintick proxy (true syminfo.mintick is not exposed in Custom JS API)
const myMinTick = 1 / Math.pow(10, current.decimals || 2);

const myAtr = atr(high, low, close, myAtrLen);
const myEma = ema(close, myEmaLen);

// Pivot points, placed at the pivot candle index itself. Pine's
// ta.pivothigh/pivotlow only becomes known `rightBars` candles later
// (on the confirmation bar). We shift the pivot series forward by
// `rightBars` to replicate that exact confirmation timing and avoid
// look-ahead bias.
const myPivotHighRaw = pivot_high(high, myLeftBars, myRightBars);
const myPivotLowRaw = pivot_low(low, myLeftBars, myRightBars);
const myPivotHigh = shift(myPivotHighRaw, myRightBars);
const myPivotLow = shift(myPivotLowRaw, myRightBars);

const myCandleCount = close.length;
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

let mySwingHigh = null;
let mySwingLow = null;
let mySwingHighBar = null;
let mySwingLowBar = null;
let myHighSwept = false;
let myLowSwept = false;
let myHighSweepBar = null;
let myLowSweepBar = null;
let myHighSweepLevel = null;
let myLowSweepLevel = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const mySafeATR = Math.max(myAtr[myIndex] || 0, myMinTick);
	const myBullBias = !myUseEMA || close[myIndex] > myEma[myIndex];
	const myBearBias = !myUseEMA || close[myIndex] < myEma[myIndex];
	const myBodyATR = Math.abs(close[myIndex] - open[myIndex]) / mySafeATR;
	const myBarRange = Math.max(high[myIndex] - low[myIndex], myMinTick);
	const myBullCloseLocation = (close[myIndex] - low[myIndex]) / myBarRange;
	const myBearCloseLocation = (high[myIndex] - close[myIndex]) / myBarRange;

	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		mySwingHigh = myPivotHigh[myIndex];
		mySwingHighBar = myIndex - myRightBars;
		myHighSwept = false;
	}
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		mySwingLow = myPivotLow[myIndex];
		mySwingLowBar = myIndex - myRightBars;
		myLowSwept = false;
	}

	const myHighSweepDepth = mySwingHigh !== null ? (high[myIndex] - mySwingHigh) / mySafeATR : null;
	const myLowSweepDepth = mySwingLow !== null ? (mySwingLow - low[myIndex]) / mySafeATR : null;

	const myNewHighSweep = mySwingHigh !== null && !myHighSwept && myIndex > mySwingHighBar &&
		high[myIndex] > mySwingHigh && myHighSweepDepth >= myMinSweepATR && myHighSweepDepth <= myMaxSweepATR;
	const myNewLowSweep = mySwingLow !== null && !myLowSwept && myIndex > mySwingLowBar &&
		low[myIndex] < mySwingLow && myLowSweepDepth >= myMinSweepATR && myLowSweepDepth <= myMaxSweepATR;

	if (myNewHighSweep) {
		myHighSwept = true;
		myHighSweepBar = myIndex;
		myHighSweepLevel = mySwingHigh;
	}
	if (myNewLowSweep) {
		myLowSwept = true;
		myLowSweepBar = myIndex;
		myLowSweepLevel = mySwingLow;
	}

	let mySellReclaim = myHighSwept && myHighSweepBar !== null && (myIndex - myHighSweepBar) <= myReclaimBars &&
		close[myIndex] < (myHighSweepLevel - mySafeATR * myCloseBufferATR) &&
		myBearCloseLocation >= myMinCloseLocation && myBodyATR >= myMinBodyATR && myBearBias;
	let myBuyReclaim = myLowSwept && myLowSweepBar !== null && (myIndex - myLowSweepBar) <= myReclaimBars &&
		close[myIndex] > (myLowSweepLevel + mySafeATR * myCloseBufferATR) &&
		myBullCloseLocation >= myMinCloseLocation && myBodyATR >= myMinBodyATR && myBullBias;

	if (mySellReclaim) {
		myHighSwept = false;
	}
	if (myBuyReclaim) {
		myLowSwept = false;
	}
	if (mySellReclaim && myBuyReclaim) {
		mySellReclaim = false;
		myBuyReclaim = false;
	}

	myBuySignal[myIndex] = myBuyReclaim;
	mySellSignal[myIndex] = mySellReclaim;
}

const myBuyMarks = for_every(close, low, (_c, _l) => null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	myBuyMarks[myIndex] = myBuySignal[myIndex] ? low[myIndex] : null;
}

const mySellMarks = for_every(close, high, (_c, _h) => null);
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	mySellMarks[myIndex] = mySellSignal[myIndex] ? high[myIndex] : null;
}

// Note: paint() and register_signal() output names must be unique across
// the whole indicator (they share the same namespace). The painted labels
// keep the "Reclaim" names, while the register_signal() outputs use
// distinct "Signal" names to avoid the "already exists" collision error.
paint(myBuyMarks, { style: 'labels_below', color: '#26A69A', name: 'Buy Reclaim' });
paint(mySellMarks, { style: 'labels_above', color: '#EF5350', name: 'Sell Reclaim' });

register_signal(myBuySignal, 'Buy Reclaim Signal');
register_signal(mySellSignal, 'Sell Reclaim Signal');