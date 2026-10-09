describe_indicator('Auto S/R Levels (5 Strongest)', 'price');

// ── Inputs (mapped 1:1 from the Pine Script inputs) ──────────────────────────
const myPivotLen   = input.number('Pivot Length (bars each side)', 10, { min: 2, max: 20 });
const myLookback   = input.number('Lookback (bars)', 500, { min: 100, max: 500 });
const myClusterPct = input.number('Cluster Tolerance (%)', 0.5, { min: 0.1, max: 2.0, step: 0.1 });
const myExtBars    = input.number('Extend Forward (bars)', 30, { min: 1, max: 200 });
const myNLevels    = input.number('Levels to Draw', 5, { min: 1, max: 5 });
const mySupColor   = input.color('Support Color', 'green');
const myResColor   = input.color('Resistance Color', 'red');

// Maximum amount of lines we will ever paint (Pine's max_lines_count = 10,
// but only up to 5 "strongest" levels are actually drawn here).
const MY_MAX_LEVELS = 5;

// ── Pivot detection ───────────────────────────────────────────────────────────
// Pine's ta.pivothigh/pivotlow(len, len) is equivalent to pivot_high/pivot_low
// with equal left/right length.
const myPivotHighSeries = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLowSeries  = pivot_low(low, myPivotLen, myPivotLen);

const myLastIndex = close.length - 1;
const myLookbackFromIndex = Math.max(0, myLastIndex - myLookback);

// Collect raw pivot prices, restricted to "bar_index >= last_bar_index - lookback"
const myRawPivots = [];
for (const myPoint of indexed_points_of(myPivotHighSeries)) {
	if (myPoint.candleIndex >= myLookbackFromIndex) {
		myRawPivots.push(myPoint.value);
	}
}
for (const myPoint of indexed_points_of(myPivotLowSeries)) {
	if (myPoint.candleIndex >= myLookbackFromIndex) {
		myRawPivots.push(myPoint.value);
	}
}

// ── Cluster nearby pivots (same merge logic as the Pine script) ─────────────
const myClusterPrices = [];
const myClusterHits = [];
for (const myPrice of myRawPivots) {
	const myTolerance = myPrice * myClusterPct / 100.0;
	let myMerged = false;
	for (let myClusterIndex = 0; myClusterIndex < myClusterPrices.length; myClusterIndex += 1) {
		const myClusterPrice = myClusterPrices[myClusterIndex];
		const myHits = myClusterHits[myClusterIndex];
		if (Math.abs(myClusterPrice - myPrice) <= myTolerance) {
			myClusterPrices[myClusterIndex] = (myClusterPrice * myHits + myPrice) / (myHits + 1);
			myClusterHits[myClusterIndex] = myHits + 1;
			myMerged = true;
			break;
		}
	}
	if (!myMerged) {
		myClusterPrices.push(myPrice);
		myClusterHits.push(1);
	}
}

// ── Rank clusters by hit count, pick the strongest MY_MAX_LEVELS ────────────
const myRemainingPrices = myClusterPrices.slice();
const myRemainingHits = myClusterHits.slice();
const myDrawnLevels = [];

while (myDrawnLevels.length < myNLevels && myRemainingPrices.length > 0) {
	let myMaxHits = myRemainingHits[0];
	let myMaxIndex = 0;
	for (let myIndex = 1; myIndex < myRemainingHits.length; myIndex += 1) {
		if (myRemainingHits[myIndex] > myMaxHits) {
			myMaxHits = myRemainingHits[myIndex];
			myMaxIndex = myIndex;
		}
	}
	myDrawnLevels.push(myRemainingPrices[myMaxIndex]);
	myRemainingPrices.splice(myMaxIndex, 1);
	myRemainingHits.splice(myMaxIndex, 1);
}

const myLastClose = close[myLastIndex];

// Fixed, unique names for each of the 5 possible level slots. Using the
// same name ("Level") for every paint() call caused the "out series
// already exists" error, since output series names must be unique.
const MY_LEVEL_NAMES = ['Level1', 'Level2', 'Level3', 'Level4', 'Level5'];

// ── Paint the (up to) 5 strongest levels, always the same amount of lines ──
// Unused slots (beyond myNLevels or when fewer clusters exist) are painted
// as null so the number/order of paint() calls never changes.
const myLineIds = [];
const myLevelValues = [];
const myIsResistance = [];

for (let mySlot = 0; mySlot < MY_MAX_LEVELS; mySlot += 1) {
	const myHasLevel = mySlot < myNLevels && mySlot < myDrawnLevels.length;
	const myLevelValue = myHasLevel ? myDrawnLevels[mySlot] : null;
	const myResistance = myHasLevel ? (myLevelValue >= myLastClose) : false;
	const myLevelLine = myHasLevel
		? horizontal_line(myLevelValue, myLookbackFromIndex, myLastIndex)
		: series_of(null);

	const myLineId = paint(myLevelLine, {
		name: MY_LEVEL_NAMES[mySlot],
		color: myResistance ? myResColor : mySupColor,
		thickness: 2,
		style: 'line'
	});

	// Extend the line forward by extBars, like Pine's x2 = bar_index + extBars
	const myProjectionValues = myHasLevel ? Array(myExtBars).fill(myLevelValue) : [];
	paint_projection(myLineId, myProjectionValues);

	myLineIds.push(myLineId);
	myLevelValues.push(myLevelValue);
	myIsResistance.push(myResistance);
}

// ── Scanner / Alert / Strategy signals ───────────────────────────────────────
// Price is "near" a level if it sits within the cluster tolerance of that level.
const myNearSupport = series_of(false);
const myNearResistance = series_of(false);

for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	let mySupportHit = false;
	let myResistanceHit = false;

	for (let mySlot = 0; mySlot < MY_MAX_LEVELS; mySlot += 1) {
		const myLevelValue = myLevelValues[mySlot];
		if (myLevelValue === null) continue;
		const myTolerance = myLevelValue * myClusterPct / 100.0;
		if (Math.abs(close[myCandleIndex] - myLevelValue) <= myTolerance) {
			if (myIsResistance[mySlot]) {
				myResistanceHit = true;
			}
			else {
				mySupportHit = true;
			}
		}
	}

	myNearSupport[myCandleIndex] = mySupportHit;
	myNearResistance[myCandleIndex] = myResistanceHit;
}

register_signal(myNearSupport, 'Price Near Support Level');
register_signal(myNearResistance, 'Price Near Resistance Level');