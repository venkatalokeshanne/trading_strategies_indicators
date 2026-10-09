// This is a conversion of a Pine Script strategy (TradingView) into a
// TrendSpider indicator. Since Custom JS does not support broker/strategy
// primitives (strategy.entry, strategy.position_size, strategy.close_all,
// pyramiding, equity tracking, etc.) this script reproduces the exact same
// bar-by-bar decision logic using a manual state machine (a for loop,
// which is fine here since it does not call any indicator function inside
// the loop body - rsi is computed once, outside of it).
describe_indicator('Advanced DCA Bot', 'price');

// --- INPUTS ---
const myTab1 = input.tab('Entry');
const myRsiLength = myTab1.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOversold = myTab1.number('RSI Oversold Level', 30, { min: 1, max: 99 });

const myTab2 = input.tab('DCA');
const myBaseQty = myTab2.number('Start order qty', 100, { min: 1, max: 1000000 });
// Shortened input name to satisfy the platform's input name length limit.
const myDcaDropPct = myTab2.number('DCA Drop Trigger %', 5.0, { min: 0.1, max: 100 });
const myDcaMultiplier = myTab2.number('DCA Multiplier', 1.5, { min: 1.0, max: 10 });
const myMaxDcas = myTab2.number('Maximum DCA Steps', 5, { min: 1, max: 50 });

const myTab3 = input.tab('Take Profit');
// Shortened input name to satisfy the platform's input name length limit.
const myTpPct = myTab3.number('Take Profit % (Avg Price)', 3.0, { min: 0.1, max: 1000 });

// --- CALCULATIONS ---
const myRsi = rsi(close, myRsiLength);
const myDropFraction = myDcaDropPct / 100;
const myTpFraction = myTpPct / 100;

// Output series
const myAvgPriceSeries = series_of(null);
const myTpLevelSeries = series_of(null);
const myNextDcaLevelSeries = series_of(null);
const myInitialEntrySignal = series_of(false);
const myDcaEntrySignal = series_of(false);
const myTakeProfitSignal = series_of(false);
const myDcaLabelSeries = series_of(null);

// State variables (mirrors the Pine "var" state)
let myLastEntryPrice = null;
let myDcaCount = 0;
let myPositionSize = 0; // total qty currently held
let myTotalCost = 0;    // sum of (qty * price) for all entries in current cycle

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];
	const myRsiValue = myRsi[myIndex];
	const myRsiPrev = myIndex > 0 ? myRsi[myIndex - 1] : null;

	// crossunder(rsi, oversold): previous bar at/above level, current bar below
	const myCrossedUnder = myRsiPrev !== null && myRsiValue !== null &&
		myRsiPrev >= myRsiOversold && myRsiValue < myRsiOversold;

	// 1. INITIAL ENTRY
	if (myCrossedUnder && myPositionSize === 0) {
		myPositionSize = myBaseQty;
		myTotalCost = myBaseQty * myClose;
		myLastEntryPrice = myClose;
		myDcaCount = 0;
		myInitialEntrySignal[myIndex] = true;
	}

	// 2. DCA LOGIC
	if (myPositionSize > 0 && myDcaCount < myMaxDcas) {
		const myDropThreshold = myLastEntryPrice * (1 - myDropFraction);
		if (myClose <= myDropThreshold) {
			myDcaCount += 1;
			const myNextQty = myBaseQty * Math.pow(myDcaMultiplier, myDcaCount);
			myPositionSize += myNextQty;
			myTotalCost += myNextQty * myClose;
			myLastEntryPrice = myClose;
			myDcaEntrySignal[myIndex] = true;
			myDcaLabelSeries[myIndex] = myDcaCount;
		}
	}

	// 3. TAKE PROFIT LOGIC
	if (myPositionSize > 0) {
		const myAvgPrice = myTotalCost / myPositionSize;
		const myTpPrice = myAvgPrice * (1 + myTpFraction);
		if (myClose >= myTpPrice) {
			myTakeProfitSignal[myIndex] = true;
			// reset for next cycle
			myPositionSize = 0;
			myTotalCost = 0;
			myDcaCount = 0;
			myLastEntryPrice = null;
		}
	}

	// --- VISUALIZATION (computed after possible reset above, matches Pine's
	// behavior where plot() reads the final state of this bar) ---
	if (myPositionSize > 0) {
		const myAvgPriceNow = myTotalCost / myPositionSize;
		myAvgPriceSeries[myIndex] = myAvgPriceNow;
		myTpLevelSeries[myIndex] = myAvgPriceNow * (1 + myTpFraction);
		myNextDcaLevelSeries[myIndex] = myLastEntryPrice * (1 - myDropFraction);
	}
}

// --- PAINTING ---
paint(myAvgPriceSeries, { name: 'Average Price', color: '#FFFFFF', thickness: 2, style: 'ladder' });
paint(myTpLevelSeries, { name: 'Take Profit Level', color: '#2ca599', thickness: 2, style: 'ladder' });
paint(myNextDcaLevelSeries, { name: 'Next DCA Level', color: '#ee5451', thickness: 1, style: 'ladder' });
paint(myDcaLabelSeries, { name: 'DCA Step', style: 'labels_above', color: '#ff9800' });

// --- SIGNALS (for scanners, alerts, strategy tester) ---
register_signal(myInitialEntrySignal, 'Initial Entry');
register_signal(myDcaEntrySignal, 'DCA Entry');
register_signal(myTakeProfitSignal, 'Take Profit Hit');