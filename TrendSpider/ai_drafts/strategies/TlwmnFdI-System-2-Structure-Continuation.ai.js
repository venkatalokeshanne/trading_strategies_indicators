describe_indicator('System 2 - Structure Continuation', 'price');

// ===== INPUTS =====
const myRiskPercent = input.number('Risk Pct', 2.0, { min: 0.1, max: 100, step: 0.1 });
const myRR = input.number('RR', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myDispMult = input.number('Disp ATR Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myPullbackBars = input.number('Max Pullback', 10, { min: 3, max: 200 });
const myCooldownBars = input.number('Cooldown Bars', 10, { min: 0, max: 500 });

// ATR(14), computed once outside the loop
const myAtr = atr(high, low, close, 14);
const myLength = close.length;

// Output series
const myBullDispSeries = series_of(null);
const myBearDispSeries = series_of(null);
const myBuySeries = series_of(null);
const mySellSeries = series_of(null);
const myBullDispSignal = series_of(false);
const myBearDispSignal = series_of(false);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

// State variables (mirroring the Pine `var` state)
let myDispBar = null;
let myDispLow = null;
let myDispHigh = null;
let myBullishActive = false;
let myBearishActive = false;
let myLastTradeBar = null;

// Simulated position state (0 = flat, 1 = long, -1 = short),
// needed to replicate strategy.position_size == 0 (flatOK) and
// the stop/limit exit mechanism from strategy.exit().
let myPositionSize = 0;
let myStopPrice = 0;
let myTargetPrice = 0;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myOpen = open[myIndex];
	const myClose = close[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myAtrValue = myAtr[myIndex] || 0;

	// Check if an open simulated position gets stopped out or hits target
	// this bar. We assume the stop is checked before the limit when both
	// could be touched within the same bar (a worst-case approximation,
	// since Pine's actual intrabar fill order can't be reproduced exactly).
	if (myPositionSize === 1) {
		if (myLow <= myStopPrice || myHigh >= myTargetPrice) {
			myPositionSize = 0;
		}
	}
	else if (myPositionSize === -1) {
		if (myHigh >= myStopPrice || myLow <= myTargetPrice) {
			myPositionSize = 0;
		}
	}

	const myBullDisplacement = (myClose - myOpen) > myAtrValue * myDispMult;
	const myBearDisplacement = (myOpen - myClose) > myAtrValue * myDispMult;

	if (myBullDisplacement) {
		myDispBar = myIndex;
		myDispLow = myLow;
		myBullishActive = true;
		myBearishActive = false;
	}
	if (myBearDisplacement) {
		myDispBar = myIndex;
		myDispHigh = myHigh;
		myBearishActive = true;
		myBullishActive = false;
	}

	const myBarsSinceDisp = myDispBar === null ? null : myIndex - myDispBar;
	const myValidPullback = myDispBar !== null && myBarsSinceDisp > 0 && myBarsSinceDisp <= myPullbackBars;
	const myBullStructure = myBullishActive && myValidPullback && myLow > myDispLow;
	const myBearStructure = myBearishActive && myValidPullback && myHigh < myDispHigh;
	const myBullEntry = myBullStructure && myClose > myOpen;
	const myBearEntry = myBearStructure && myClose < myOpen;
	const myCooldownOK = myLastTradeBar === null || (myIndex - myLastTradeBar > myCooldownBars);
	const myFlatOK = myPositionSize === 0;
	const myLongCondition = myBullEntry && myCooldownOK && myFlatOK;
	const myShortCondition = myBearEntry && myCooldownOK && myFlatOK;

	if (myLongCondition) {
		const myEntryPrice = myClose;
		const myStop = myDispLow;
		const myRiskDist = myEntryPrice - myStop;
		if (myRiskDist > 0) {
			myStopPrice = myStop;
			myTargetPrice = myEntryPrice + (myRiskDist * myRR);
			myPositionSize = 1;
			myLastTradeBar = myIndex;
			myBullishActive = false;
		}
	}
	if (myShortCondition) {
		const myEntryPrice = myClose;
		const myStop = myDispHigh;
		const myRiskDist = myStop - myEntryPrice;
		if (myRiskDist > 0) {
			myStopPrice = myStop;
			myTargetPrice = myEntryPrice - (myRiskDist * myRR);
			myPositionSize = -1;
			myLastTradeBar = myIndex;
			myBearishActive = false;
		}
	}

	myBullDispSeries[myIndex] = myBullDisplacement ? constants.icons.triangle_up : null;
	myBearDispSeries[myIndex] = myBearDisplacement ? constants.icons.triangle_down : null;
	myBuySeries[myIndex] = myLongCondition ? constants.icons.arrow_up : null;
	mySellSeries[myIndex] = myShortCondition ? constants.icons.arrow_down : null;
	myBullDispSignal[myIndex] = myBullDisplacement;
	myBearDispSignal[myIndex] = myBearDisplacement;
	myLongSignal[myIndex] = myLongCondition;
	myShortSignal[myIndex] = myShortCondition;
}

// Visuals
paint(myBullDispSeries, { style: 'labels_below', color: 'green', name: 'BullDisplacement' });
paint(myBearDispSeries, { style: 'labels_above', color: 'red', name: 'BearDisplacement' });
paint(myBuySeries, { style: 'labels_below', color: 'green', name: 'BuySignal' });
paint(mySellSeries, { style: 'labels_above', color: 'red', name: 'SellSignal' });

// Signals for scanners, alerts and strategy tester.
// Renamed to be distinct, alphanumeric-only names (no spaces), since
// identical/non-alphanumeric names across paint() and register_signal()
// calls were causing the "already exists" collision error.
register_signal(myBullDispSignal, 'BullDisplacementSignal');
register_signal(myBearDispSignal, 'BearDisplacementSignal');
register_signal(myLongSignal, 'LongEntrySignal');
register_signal(myShortSignal, 'ShortEntrySignal');