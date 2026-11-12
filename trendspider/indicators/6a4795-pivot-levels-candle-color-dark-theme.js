<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pivot Levels & Candle Color (Dark Theme)');

// ── Inputs ──────────────────────────────────────────────────────────────────
const pivotLeftBars = input.number('Pivot Left Bars', 10, { min: 1, max: 50 });
const pivotRightBars = input.number('Pivot Right Bars', 10, { min: 1, max: 50 });
const neutralLookbackBars = input.number('Neutral Lookback Bars', 5, { min: 2, max: 20 });

// ── Timeframe-Aware Calibration ─────────────────────────────────────────────
// Diagnose the current timeframe and compute a sensitivity multiplier.
// Daily charts need more relaxed confirmation thresholds to match 4h responsiveness.
const myResolutionMinutes = isNaN(current.resolution) ? 1440 : Number(current.resolution);
const myBaselineMinutes = 240; // 4-hour reference
const myTimeframeSensitivity = Math.sqrt(myResolutionMinutes / myBaselineMinutes);

// Adjust breakout/breakdown confirmation thresholds to be more forgiving on larger timeframes
const myBreakoutConfirmationFactor = 0.995 + (1 - myTimeframeSensitivity) * 0.003;
const myBreakdownConfirmationFactor = 1.005 - (1 - myTimeframeSensitivity) * 0.003;

// Adjust progress threshold strictness for neutralization on larger timeframes
const myBullishProgressRelaxation = (myTimeframeSensitivity - 1) * 0.002;
const myBearishProgressRelaxation = (myTimeframeSensitivity - 1) * 0.002;

// Adjust range tightness threshold to prevent premature neutralization on Daily
const myRangeTightnessMultiplier = 0.4 + (myTimeframeSensitivity - 1) * 0.15;

// ── Professional-Grade Adaptive Pivot Detection ──────────────────────────────
const myPivotHighs = series_of(null);
const myPivotLows = series_of(null);
const myPotentialPivotHighs = [];
const myPotentialPivotLows = [];

for (let i = pivotLeftBars; i < high.length - pivotRightBars; i += 1) {
	let myIsHighCandidate = true;
	const myCurrentHigh = high[i];
	
	for (let j = 1; j <= pivotLeftBars; j += 1) {
		if (high[i - j] > myCurrentHigh) {
			myIsHighCandidate = false;
			break;
		}
	}
	
	if (myIsHighCandidate) {
		let myConfirmedReversal = false;
		let myRightSideMax = -Infinity;
		
		for (let j = 1; j <= pivotRightBars; j += 1) {
			myRightSideMax = Math.max(myRightSideMax, high[i + j]);
			if (high[i + j] < myCurrentHigh * myBreakoutConfirmationFactor) {
				myConfirmedReversal = true;
			}
		}
		
		if (myConfirmedReversal && myRightSideMax < myCurrentHigh) {
			myPotentialPivotHighs.push({ index: i, value: myCurrentHigh });
		}
	}
	
	let myIsLowCandidate = true;
	const myCurrentLow = low[i];
	
	for (let j = 1; j <= pivotLeftBars; j += 1) {
		if (low[i - j] < myCurrentLow) {
			myIsLowCandidate = false;
			break;
		}
	}
	
	if (myIsLowCandidate) {
		let myConfirmedReversal = false;
		let myRightSideMin = Infinity;
		
		for (let j = 1; j <= pivotRightBars; j += 1) {
			myRightSideMin = Math.min(myRightSideMin, low[i + j]);
			if (low[i + j] > myCurrentLow * myBreakdownConfirmationFactor) {
				myConfirmedReversal = true;
			}
		}
		
		if (myConfirmedReversal && myRightSideMin > myCurrentLow) {
			myPotentialPivotLows.push({ index: i, value: myCurrentLow });
		}
	}
}

const myMinPivotSpacing = Math.max(5, Math.floor((pivotLeftBars + pivotRightBars) / 3));

for (let i = 0; i < myPotentialPivotHighs.length; i += 1) {
	const myCurrentPivot = myPotentialPivotHighs[i];
	let myIsSignificant = true;
	
	for (let j = 0; j < myPotentialPivotHighs.length; j += 1) {
		if (i === j) continue;
		const myOtherPivot = myPotentialPivotHighs[j];
		const myDistance = Math.abs(myCurrentPivot.index - myOtherPivot.index);
		
		if (myDistance < myMinPivotSpacing && myOtherPivot.value > myCurrentPivot.value) {
			myIsSignificant = false;
			break;
		}
	}
	
	if (myIsSignificant) {
		myPivotHighs[myCurrentPivot.index] = myCurrentPivot.value;
	}
}

for (let i = 0; i < myPotentialPivotLows.length; i += 1) {
	const myCurrentPivot = myPotentialPivotLows[i];
	let myIsSignificant = true;
	
	for (let j = 0; j < myPotentialPivotLows.length; j += 1) {
		if (i === j) continue;
		const myOtherPivot = myPotentialPivotLows[j];
		const myDistance = Math.abs(myCurrentPivot.index - myOtherPivot.index);
		
		if (myDistance < myMinPivotSpacing && myOtherPivot.value < myCurrentPivot.value) {
			myIsSignificant = false;
			break;
		}
	}
	
	if (myIsSignificant) {
		myPivotLows[myCurrentPivot.index] = myCurrentPivot.value;
	}
}

// ── Livermore-Inspired Market Structure State Machine ────────────────────────
const bullishBreakoutMarker = series_of(null);
const bearishBreakdownMarker = series_of(null);
const trendState = series_of(null);

let myLastActivePivotHigh = null;
let myLastActivePivotLow = null;
let myCurrentTrendState = 'neutral';
let myLastBullishBreakoutIndex = -999;
let myLastBearishBreakdownIndex = -999;
let myBullishHighWaterMark = -Infinity;
let myBearishLowWaterMark = Infinity;
let myBullishLegReactionLow = Infinity;
let myBearishLegReactionHigh = -Infinity;
let myLastBullishBreakoutLevel = -Infinity;
let myLastBearishBreakdownLevel = Infinity;

for (let i = 0; i < close.length; i += 1) {
	if (myPivotHighs[i] !== null) {
		myLastActivePivotHigh = myPivotHighs[i];
	}
	
	if (myPivotLows[i] !== null) {
		myLastActivePivotLow = myPivotLows[i];
	}
	
	if (myLastActivePivotHigh !== null && close[i] > myLastActivePivotHigh) {
		bullishBreakoutMarker[i] = low[i];
		myCurrentTrendState = 'bullish';
		myLastBullishBreakoutLevel = myLastActivePivotHigh;
		myLastActivePivotHigh = null;
		myLastBullishBreakoutIndex = i;
		myBullishHighWaterMark = high[i];
		myBullishLegReactionLow = low[i];
	}
	
	if (myLastActivePivotLow !== null && close[i] < myLastActivePivotLow) {
		bearishBreakdownMarker[i] = high[i];
		myCurrentTrendState = 'bearish';
		myLastBearishBreakdownLevel = myLastActivePivotLow;
		myLastActivePivotLow = null;
		myLastBearishBreakdownIndex = i;
		myBearishLowWaterMark = low[i];
		myBearishLegReactionHigh = high[i];
	}
	
	if (myCurrentTrendState === 'neutral' && myLastBullishBreakoutLevel > -Infinity) {
		if (close[i] > myLastBullishBreakoutLevel && high[i] > myBullishHighWaterMark) {
			myCurrentTrendState = 'bullish';
			myLastBullishBreakoutIndex = i;
			myBullishHighWaterMark = high[i];
			myBullishLegReactionLow = low[i];
		}
	}
	
	if (myCurrentTrendState === 'neutral' && myLastBearishBreakdownLevel < Infinity) {
		if (close[i] < myLastBearishBreakdownLevel && low[i] < myBearishLowWaterMark) {
			myCurrentTrendState = 'bearish';
			myLastBearishBreakdownIndex = i;
			myBearishLowWaterMark = low[i];
			myBearishLegReactionHigh = high[i];
		}
	}
	
	if (myCurrentTrendState === 'bullish') {
		const myPreviousHigh = myBullishHighWaterMark;
		myBullishHighWaterMark = Math.max(myBullishHighWaterMark, high[i]);
		
		if (high[i] > myPreviousHigh) {
			myBullishLegReactionLow = Infinity;
			for (let j = myLastBullishBreakoutIndex; j <= i; j += 1) {
				myBullishLegReactionLow = Math.min(myBullishLegReactionLow, low[j]);
			}
		}
		
		const myBarsSinceBreakout = i - myLastBullishBreakoutIndex;
		
		if (myBarsSinceBreakout >= 2 && low[i] < myBullishLegReactionLow) {
			myCurrentTrendState = 'neutral';
		} else if (myBarsSinceBreakout >= neutralLookbackBars * 3) {
			const myWindowStart = Math.max(0, i - neutralLookbackBars + 1);
			const myRecentHighestHigh = Math.max(...high.slice(myWindowStart, i + 1));
			const myRecentLowestLow = Math.min(...low.slice(myWindowStart, i + 1));
			const myRecentRange = myRecentHighestHigh - myRecentLowestLow;
			
			const myProgressThreshold = myBullishHighWaterMark * (0.997 - myBullishProgressRelaxation);
			const myNoMeaningfulProgress = myRecentHighestHigh < myProgressThreshold;
			const myRangeTight = myRecentRange < (myBullishHighWaterMark - myRecentLowestLow) * myRangeTightnessMultiplier;
			const myMidpointHover = Math.abs(close[i] - (myRecentHighestHigh + myRecentLowestLow) / 2) < myRecentRange * 0.35;
			
			if (myNoMeaningfulProgress && myRangeTight && myMidpointHover) {
				myCurrentTrendState = 'neutral';
			}
		}
	}
	
	if (myCurrentTrendState === 'bearish') {
		const myPreviousLow = myBearishLowWaterMark;
		myBearishLowWaterMark = Math.min(myBearishLowWaterMark, low[i]);
		
		if (low[i] < myPreviousLow) {
			myBearishLegReactionHigh = -Infinity;
			for (let j = myLastBearishBreakdownIndex; j <= i; j += 1) {
				myBearishLegReactionHigh = Math.max(myBearishLegReactionHigh, high[j]);
			}
		}
		
		const myBarsSinceBreakdown = i - myLastBearishBreakdownIndex;
		
		if (myBarsSinceBreakdown >= 2 && high[i] > myBearishLegReactionHigh) {
			myCurrentTrendState = 'neutral';
		} else if (myBarsSinceBreakdown >= neutralLookbackBars * 3) {
			const myWindowStart = Math.max(0, i - neutralLookbackBars + 1);
			const myRecentLowestLow = Math.min(...low.slice(myWindowStart, i + 1));
			const myRecentHighestHigh = Math.max(...high.slice(myWindowStart, i + 1));
			const myRecentRange = myRecentHighestHigh - myRecentLowestLow;
			
			const myProgressThreshold = myBearishLowWaterMark * (1.003 + myBearishProgressRelaxation);
			const myNoMeaningfulProgress = myRecentLowestLow > myProgressThreshold;
			const myRangeTight = myRecentRange < (myRecentHighestHigh - myBearishLowWaterMark) * myRangeTightnessMultiplier;
			const myMidpointHover = Math.abs(close[i] - (myRecentHighestHigh + myRecentLowestLow) / 2) < myRecentRange * 0.35;
			
			if (myNoMeaningfulProgress && myRangeTight && myMidpointHover) {
				myCurrentTrendState = 'neutral';
			}
		}
	}
	
	trendState[i] = myCurrentTrendState;
}

const myCandleColors = for_every(trendState, (_state) => {
	if (_state === 'bullish') {
		return '#7bed9f';
	} else if (_state === 'bearish') {
		return '#ff6b81';
	} else {
		return '#95a5a6';
	}
});

color_candles(myCandleColors);

paint(interpolate_sparse_series(myPivotHighs, 'constant'), {
	name: 'Pivot High',
	style: 'ladder',
	color: '#e74c3c',
	thickness: 2
});

paint(interpolate_sparse_series(myPivotLows, 'constant'), {
	name: 'Pivot Low',
	style: 'ladder',
	color: '#2ecc71',
	thickness: 2
});

const bullishBreakoutIcons = for_every(bullishBreakoutMarker, (_marker) => {
	return _marker !== null ? constants.icons.triangle_up : null;
});

const bearishBreakdownIcons = for_every(bearishBreakdownMarker, (_marker) => {
	return _marker !== null ? constants.icons.triangle_down : null;
});

paint(bullishBreakoutIcons, {
	name: 'Bullish Breakout',
	style: 'labels_below',
	color: '#2ecc71'
});

paint(bearishBreakdownIcons, {
	name: 'Bearish Breakdown',
	style: 'labels_above',
	color: '#e74c3c'
});
</code>