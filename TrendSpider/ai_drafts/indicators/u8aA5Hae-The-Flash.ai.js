describe_indicator('The Flash', 'price');

// ============================================================================
// INPUTS
// ============================================================================
const myAdxLength = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThreshold = input.number('ADX Threshold', 13.0, { min: 0, max: 100, step: 0.1 });
const myFlashColor = input.color('Flash Color', 'rgba(128,128,128,0.3)');
const myBullishArrowColor = input.color('Bullish Signal Arrow Color', 'lime');
const myBearishArrowColor = input.color('Bearish Signal Arrow Color', 'red');

// ============================================================================
// ADX / DMI CALCULATION
// ============================================================================
const myAdxObject = indicators.adx(myAdxLength);
const myAdx = myAdxObject.adx;
const myDiPlus = myAdxObject.dmiPlus;
const myDiMinus = myAdxObject.dmiMinus;

const myBarsCount = close.length;

// ============================================================================
// FLASH / SIGNAL STATE MACHINE (reproduces the Pine Script var-based logic)
// ============================================================================
const myFlashActiveSeries = series_of(false);
const myFlashEndedSeries = series_of(false);
const myShowSignalSeries = series_of(false);
const mySignalIsBullishSeries = series_of(false);

let myFlashActive = false;

for (let myIndex = 0; myIndex < myBarsCount; myIndex += 1) {
	const myAdxValue = myAdx[myIndex];
	const myAdxPrev = myIndex > 0 ? myAdx[myIndex - 1] : null;
	const myDiPlusValue = myDiPlus[myIndex];
	const myDiMinusValue = myDiMinus[myIndex];

	// crossunder(adx, threshold)
	const myAdxCrossBelowThreshold = (myAdxPrev != null && myAdxValue != null)
		&& (myAdxPrev >= myAdxThreshold) && (myAdxValue < myAdxThreshold);

	if (myAdxCrossBelowThreshold) {
		myFlashActive = true;
	}

	// crossover(adx, diPlus) and crossover(adx, diMinus), only relevant while flash is active
	const myDiPlusPrev = myIndex > 0 ? myDiPlus[myIndex - 1] : null;
	const myDiMinusPrev = myIndex > 0 ? myDiMinus[myIndex - 1] : null;

	const myAdxCrossAboveDIPlus = myFlashActive && myAdxPrev != null && myDiPlusPrev != null
		&& (myAdxPrev <= myDiPlusPrev) && (myAdxValue > myDiPlusValue);
	const myAdxCrossAboveDIMinus = myFlashActive && myAdxPrev != null && myDiMinusPrev != null
		&& (myAdxPrev <= myDiMinusPrev) && (myAdxValue > myDiMinusValue);

	const myFlashEnded = myAdxCrossAboveDIPlus || myAdxCrossAboveDIMinus;

	if (myFlashEnded) {
		myFlashActive = false;
	}

	myFlashActiveSeries[myIndex] = myFlashActive;
	myFlashEndedSeries[myIndex] = myFlashEnded;

	// signal is on the candle right AFTER flash ended (uses previous bar's flashEnded flag)
	const myFlashEndedPrevBar = myIndex > 0 ? myFlashEndedSeries[myIndex - 1] : false;

	if (myFlashEndedPrevBar) {
		myShowSignalSeries[myIndex] = true;
		mySignalIsBullishSeries[myIndex] = myDiPlusValue > myDiMinusValue;
	}
	else {
		myShowSignalSeries[myIndex] = false;
		mySignalIsBullishSeries[myIndex] = false;
	}
}

// ============================================================================
// VISUALIZATION
// ============================================================================

// Flash zone: colors candles while flash is active (closest equivalent
// to Pine's bgcolor, since custom JS has no background-paint primitive)
const myFlashCandleColors = for_every(series_of(0), (_v, _p, _i) => myFlashActiveSeries[_i] ? myFlashColor : null);
color_candles(myFlashCandleColors);

// Bullish / Bearish signal arrows
const myBullishMarks = for_every(low, (_low, _p, _i) => (myShowSignalSeries[_i] && mySignalIsBullishSeries[_i]) ? _low : null);
const myBearishMarks = for_every(high, (_high, _p, _i) => (myShowSignalSeries[_i] && !mySignalIsBullishSeries[_i]) ? _high : null);

paint(myBullishMarks, { name: 'BullishSignal', style: 'labels_below', color: myBullishArrowColor });
paint(myBearishMarks, { name: 'BearishSignal', style: 'labels_above', color: myBearishArrowColor });

// ============================================================================
// SIGNALS FOR SCANNER / ALERTS / STRATEGY TESTER
// ============================================================================
const myFlashActivatedSignal = for_every(series_of(0), (_v, _p, _i) =>
	(_i > 0 && myAdx[_i - 1] != null && myAdx[_i] != null && myAdx[_i - 1] >= myAdxThreshold && myAdx[_i] < myAdxThreshold)
);
const myBullishSignalSignal = for_every(series_of(0), (_v, _p, _i) => myShowSignalSeries[_i] && mySignalIsBullishSeries[_i]);
const myBearishSignalSignal = for_every(series_of(0), (_v, _p, _i) => myShowSignalSeries[_i] && !mySignalIsBullishSeries[_i]);

register_signal(myFlashActivatedSignal, 'Flash Activated');
register_signal(myBullishSignalSignal, 'Bullish Signal');
register_signal(myBearishSignalSignal, 'Bearish Signal');