// ==========================================================================
// EXPERIMENTAL CONVERSION NOTICE
// This is a best-effort translation of a Pine Script v6 strategy into
// TrendSpider Custom JS. TrendSpider has no native strategy.entry/exit,
// stop/limit order engine, or box drawing primitives, so the order
// simulation below (stop entries, SL/TP exits) is manually reconstructed
// with a bar-by-bar loop. Results should closely resemble the Pine
// strategy for simple cases, but exact intrabar fill order (when both
// stop/limit levels are touched within the same bar) is an assumption,
// not a guarantee of byte-for-byte parity with Pine's execution engine.
// ==========================================================================
describe_indicator('Decoded Volatility Expansion Visual Pro', 'price');

const myInputsTab = input.tab('Settings');
const myLookback = myInputsTab.number('Consolidation Lookback', 20, { min: 1, max: 500 });
const myAtrLen = myInputsTab.number('Volatility Length', 14, { min: 1, max: 500 });
const myAtrMult = myInputsTab.number('Outlier Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myRrRatio = myInputsTab.number('Risk Reward Ratio', 2.0, { min: 0.1, max: 20, step: 0.1 });

// ==========================================================================
// Dynamic levels (computed outside any loop, using built-in functions)
// ==========================================================================
const myHighShifted = shift(high, 1);
const myLowShifted = shift(low, 1);

const myZoneHigh = highest(myHighShifted, myLookback);
const myZoneLow = lowest(myLowShifted, myLookback);
const myZoneMid = div(add(myZoneHigh, myZoneLow), 2);
const myAtr = atr(high, low, close, myAtrLen);
const myOffset = mult(myAtr, myAtrMult);

const myBuyStopLevel = add(myZoneHigh, myOffset);
const mySellStopLevel = sub(myZoneLow, myOffset);

// ==========================================================================
// Manual order simulation (netting, single position, stop entries,
// SL/limit exits). State: 0 = flat, 1 = long, -1 = short.
// ==========================================================================
const myPositionState = series_of(0);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);
const myLongSLSeries = series_of(null);
const myLongTPSeries = series_of(null);
const myShortSLSeries = series_of(null);
const myShortTPSeries = series_of(null);

let myPrevState = 0;
let myCurrentLongSL = null;
let myCurrentLongTP = null;
let myCurrentShortSL = null;
let myCurrentShortTP = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myBuyLevel = myBuyStopLevel[myIndex];
	const mySellLevel = mySellStopLevel[myIndex];
	const myMid = myZoneMid[myIndex];

	let myState = myPrevState;
	let myLongEntered = false;
	let myShortEntered = false;
	let myLongExited = false;
	let myShortExited = false;

	if (myPrevState === 0) {
		// stop orders placed this bar; both evaluated, long processed first
		const myHitLong = myBuyLevel != null && high[myIndex] >= myBuyLevel;
		const myHitShort = mySellLevel != null && low[myIndex] <= mySellLevel;

		if (myHitLong) {
			myState = 1;
			myLongEntered = true;
			myCurrentLongSL = myMid;
			myCurrentLongTP = myBuyLevel + Math.abs(myBuyLevel - myMid) * myRrRatio;
		}
		else if (myHitShort) {
			myState = -1;
			myShortEntered = true;
			myCurrentShortSL = myMid;
			myCurrentShortTP = mySellLevel - Math.abs(mySellLevel - myMid) * myRrRatio;
		}
	}
	else if (myPrevState === 1) {
		// Long position: check SL first (conservative assumption), then TP
		const myHitSL = myCurrentLongSL != null && low[myIndex] <= myCurrentLongSL;
		const myHitTP = myCurrentLongTP != null && high[myIndex] >= myCurrentLongTP;

		if (myHitSL) {
			myState = 0;
			myLongExited = true;
		}
		else if (myHitTP) {
			myState = 0;
			myLongExited = true;
		}
	}
	else if (myPrevState === -1) {
		// Short position: check SL first (conservative assumption), then TP
		const myHitSL = myCurrentShortSL != null && high[myIndex] >= myCurrentShortSL;
		const myHitTP = myCurrentShortTP != null && low[myIndex] <= myCurrentShortTP;

		if (myHitSL) {
			myState = 0;
			myShortExited = true;
		}
		else if (myHitTP) {
			myState = 0;
			myShortExited = true;
		}
	}

	myPositionState[myIndex] = myState;
	myLongEntrySignal[myIndex] = myLongEntered;
	myShortEntrySignal[myIndex] = myShortEntered;
	myLongExitSignal[myIndex] = myLongExited;
	myShortExitSignal[myIndex] = myShortExited;
	myLongSLSeries[myIndex] = myState === 1 ? myCurrentLongSL : null;
	myLongTPSeries[myIndex] = myState === 1 ? myCurrentLongTP : null;
	myShortSLSeries[myIndex] = myState === -1 ? myCurrentShortSL : null;
	myShortTPSeries[myIndex] = myState === -1 ? myCurrentShortTP : null;

	myPrevState = myState;
}

// ==========================================================================
// Visuals
// ==========================================================================
paint(myZoneMid, { name: 'Midline Equilibrium', color: '#FFFFFF', thickness: 2 });
paint(myBuyStopLevel, { name: 'Buy Stop Trigger', color: '#00BCD4', thickness: 2 });
paint(mySellStopLevel, { name: 'Sell Stop Trigger', color: '#FF9800', thickness: 2 });

const myLongEntryMarks = for_every(myLongEntrySignal, low, (_myEntered, _myLow) => _myEntered ? _myLow : null);
const myShortEntryMarks = for_every(myShortEntrySignal, high, (_myEntered, _myHigh) => _myEntered ? _myHigh : null);

const myLongLabelLine = paint(myLongEntryMarks, { name: 'Expansion Buy', color: '#4CAF50', style: 'labels_below' });
const myShortLabelLine = paint(myShortEntryMarks, { name: 'Expansion Sell', color: '#F44336', style: 'labels_above' });

// ==========================================================================
// Scanning / strategy signals
// ==========================================================================
register_signal(myLongEntrySignal, 'Long Entry (Expansion Up)');
register_signal(myShortEntrySignal, 'Short Entry (Expansion Down)');
register_signal(myLongExitSignal, 'Long Exit (Fakeout or Target Hit)');
register_signal(myShortExitSignal, 'Short Exit (Fakeout or Target Hit)');