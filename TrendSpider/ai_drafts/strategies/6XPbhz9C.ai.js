// ╔══════════════════════════════════════════════════════════════╗
// ║ Mean Reversion Suite — Institutional Index Edition (ported)   ║
// ║ Original Pine Script by @LliterH, MPL-2.0                      ║
// ║ Ported to TrendSpider Custom JS API.                           ║
// ╚══════════════════════════════════════════════════════════════╝

describe_indicator('Mean Reversion Setup LliterH', 'price');

// -- Core logic --
const myCoreTab = input.tab('Core Strategy Logic');
const myLookbackHigh = myCoreTab.number('Highest High Periods', 10, { min: 1, max: 200 });
const myLookbackAvg = myCoreTab.number('Average Range Periods', 25, { min: 1, max: 200 });
const myMultiplier = myCoreTab.number('Drop Multiplier', 2.5, { min: 0.1, max: 20, step: 0.1 });
const myIbsMax = myCoreTab.number('Max IBS Level', 0.3, { min: 0, max: 1, step: 0.01 });

// -- Regime filter --
const myRegimeTab = input.tab('Trend Regime Filter');
const myUseRegime = myRegimeTab.boolean('Enable Regime Filter', true);
const myRegimeLength = myRegimeTab.number('Regime MA Length', 50, { min: 10, max: 500 });

// -- Risk management --
const myRiskTab = input.tab('Exits and Risk Management');
const myAtrLen = myRiskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = myRiskTab.number('Hard Stop ATR Multiplier', 2.0, { min: 0.1, max: 20, step: 0.25 });
// Shortened input title (was too long and caused "name is too lengthy" error)
const myTrailMult = myRiskTab.number('Trail Stop ATR Mult Leg2', 1.5, { min: 0.1, max: 20, step: 0.25 });

// ============================================================
// Core math
// ============================================================
const myHighest10 = highest(high, myLookbackHigh);
const myAvgRange25 = sma(sub(high, low), myLookbackAvg);
const myBuyThreshold = sub(myHighest10, mult(myAvgRange25, myMultiplier));
const myIbs = for_every(high, low, close, (_h, _l, _c) => (_h === _l) ? 0 : (_c - _l) / (_h - _l));
const myRegimeMA = sma(close, myRegimeLength);
const myAtr = atr(high, low, close, myAtrLen);
const myN = close.length;

// ============================================================
// Sequential state machine (position, stops, trailing)
// This replicates Pine's bar-by-bar strategy state, since this
// logic inherently depends on the previous bar's outcome and
// cannot be expressed via vectorized built-in functions.
// ============================================================
const myLongCondition = series_of(false);
const myHardStopFired = series_of(false);
const myLeg1Fired = series_of(false);
const myLeg2Fired = series_of(false);
const myInPosSeries = series_of(false);
const myTrailLevelSeries = series_of(null);
const myBuyThresholdColorSeries = series_of('green');

let myPositionSize = 0;
let myHardStopLevel = null;
let myPeakClose = null;
let myTrailLevel = null;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myCondPrice = close[myIndex] < myBuyThreshold[myIndex];
	const myCondIBS = myIbs[myIndex] < myIbsMax;
	const myCondRegime = myUseRegime ? (close[myIndex] > myRegimeMA[myIndex]) : true;
	const myLongConditionHere = myCondPrice && myCondIBS && myCondRegime && myPositionSize === 0;
	myLongCondition[myIndex] = myLongConditionHere;

	if (myLongConditionHere) {
		myHardStopLevel = close[myIndex] - (myAtrMult * myAtr[myIndex]);
		myPeakClose = close[myIndex];
		myTrailLevel = close[myIndex] - (myTrailMult * myAtr[myIndex]);
	}

	if (myPositionSize > 0) {
		myPeakClose = Math.max(myPeakClose, close[myIndex]);
		myTrailLevel = myPeakClose - (myTrailMult * myAtr[myIndex]);
	}

	const myInPos = myPositionSize > 0;
	const myPrevHigh = myIndex > 0 ? high[myIndex - 1] : null;
	const myHardStopFiredHere = myInPos && myHardStopLevel !== null && close[myIndex] <= myHardStopLevel;
	const myLeg1FiredHere = myInPos && !myHardStopFiredHere && myPrevHigh !== null && close[myIndex] > myPrevHigh;
	const myLeg2FiredHere = myInPos && !myHardStopFiredHere && !myLeg1FiredHere && myTrailLevel !== null && close[myIndex] <= myTrailLevel;

	myHardStopFired[myIndex] = myHardStopFiredHere;
	myLeg1Fired[myIndex] = myLeg1FiredHere;
	myLeg2Fired[myIndex] = myLeg2FiredHere;

	// Open new position (full size) after entry
	if (myLongConditionHere) {
		myPositionSize = 1;
	}

	// Leg1 closes 50%, hard stop and leg2 close the rest (we track binary in/out)
	if (myHardStopFiredHere || myLeg2FiredHere) {
		myPositionSize = 0;
	}

	// Leg1 only closes half; position stays open (size reduced) until leg2/hardstop/next
	// We approximate remaining exposure as still "in position" for trailing purposes.
	if (myPositionSize === 0) {
		myHardStopLevel = null;
		myPeakClose = null;
		myTrailLevel = null;
	}

	myInPosSeries[myIndex] = myPositionSize > 0;
	myTrailLevelSeries[myIndex] = (myPositionSize > 0) ? myTrailLevel : null;
	myBuyThresholdColorSeries[myIndex] = (myPositionSize > 0) ? 'red' : 'green';
}

// ============================================================
// Visuals
// ============================================================
paint(myBuyThreshold, { name: 'Buy Floor', color: myBuyThresholdColorSeries, thickness: 2 });
paint(myRegimeMA, { name: 'Regime Filter MA', color: '#FFA500', thickness: 1 });
paint(myTrailLevelSeries, { name: 'Trailing Stop', color: 'purple', style: 'ladder' });

const myLongShapeSeries = for_every(myLongCondition, _c => _c ? constants.icons.triangle_up : null);
paint(myLongShapeSeries, { name: 'Long Signal', style: 'labels_below', color: 'green' });

// ============================================================
// Signals for scanners, alerts and strategy tester
// ============================================================
register_signal(myLongCondition, 'Long Entry');
register_signal(myHardStopFired, 'Hard Stop Exit');
register_signal(myLeg1Fired, 'Leg 1 Exit 50 Percent');
register_signal(myLeg2Fired, 'Leg 2 Trail Exit');
register_signal(myInPosSeries, 'In Position');