describe_indicator('Volume Exhaustion Trend Line', 'price');

// ---------------- Inputs ----------------
const pivotTab = input.tab('Pivot Detection');
const myLeftBars = pivotTab.number('Left Bars', 20, { min: 1, max: 500 });
const myRightBars = pivotTab.number('Right Bars', 1, { min: 1, max: 500 });
const myVolMaLength = pivotTab.number('Volume MA Length', 20, { min: 1, max: 500 });

const lineTab = input.tab('Line');
const myMaLength = lineTab.number('Line MA Length', 20, { min: 1, max: 500 });
const myAtrLength = lineTab.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMult = lineTab.number('ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });

// ---------------- Volume reference ----------------
const myVolMa = sma(volume, myVolMaLength);

// ---------------- Line construction ----------------
const myBasis = sma(close, myMaLength);
const myAtrVal = atr(high, low, close, myAtrLength);
const myUpperBand = add(myBasis, mult(myAtrVal, myAtrMult));
const myLowerBand = sub(myBasis, mult(myAtrVal, myAtrMult));

// ---------------- Pivot detection ----------------
// pivot_high/pivot_low place the value at the pivot candle itself, but in Pine
// the pivot only becomes known "rightBars" candles later (confirmation delay).
// We shift the pivot series (and the volume/volMA readings used alongside them)
// forward by rightBars to replicate that confirmation delay faithfully.
const myPivotHighRaw = pivot_high(high, myLeftBars, myRightBars);
const myPivotLowRaw = pivot_low(low, myLeftBars, myRightBars);
const myPivotHigh = shift(myPivotHighRaw, myRightBars);
const myPivotLow = shift(myPivotLowRaw, myRightBars);
const myVolAtPivot = shift(volume, myRightBars);
const myVolMaAtPivot = shift(myVolMa, myRightBars);

// ---------------- Persistent state machine (translated 1:1 from Pine) ----------------
const myLineValue = series_of(null);
const myTrendSeries = series_of(null);
const myPendingUpSeries = series_of(false);
const myPendingDownSeries = series_of(false);

let myLastHigh = null;
let myPrevHigh = null;
let myLastLow = null;
let myPrevLow = null;
let myTrend = 'none';
let myLastHighWasStrong = false;
let myLastLowWasStrong = false;
let myHasLastHigh = false;
let myHasLastLow = false;
let myPendingUp = false;
let myPendingDown = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// ---------------- New pivot high ----------------
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		const myPivotVolume = myVolAtPivot[myIndex];
		const myPivotVolMa = myVolMaAtPivot[myIndex];
		const myIsWeak = myPivotVolume < myPivotVolMa;
		const myTrendBefore = myTrend;

		if (myTrendBefore === 'up') {
			if (myIsWeak) {
				if (myPendingUp || (myHasLastHigh && myLastHighWasStrong)) {
					myPendingUp = true;
				}
			}
			else {
				myPendingUp = false;
			}
		}
		else {
			myPendingUp = false;
		}

		myLastHighWasStrong = !myIsWeak;
		myHasLastHigh = true;
		myPrevHigh = myLastHigh;
		myLastHigh = myPivotHigh[myIndex];

		if (myPrevHigh !== null && myLastLow !== null && myPrevLow !== null) {
			let myNewTrend = myTrend;

			if (myLastHigh > myPrevHigh && myLastLow > myPrevLow) {
				myNewTrend = 'up';
			}
			else if (myLastHigh < myPrevHigh && myLastLow < myPrevLow) {
				myNewTrend = 'down';
			}
			else {
				myNewTrend = 'none';
			}

			if (myNewTrend !== 'up') {
				myPendingUp = false;
			}
			if (myNewTrend !== 'down') {
				myPendingDown = false;
			}

			myTrend = myNewTrend;
		}
	}

	// ---------------- New pivot low ----------------
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		const myPivotVolume = myVolAtPivot[myIndex];
		const myPivotVolMa = myVolMaAtPivot[myIndex];
		const myIsWeak = myPivotVolume < myPivotVolMa;
		const myTrendBefore = myTrend;

		if (myTrendBefore === 'down') {
			if (myIsWeak) {
				if (myPendingDown || (myHasLastLow && myLastLowWasStrong)) {
					myPendingDown = true;
				}
			}
			else {
				myPendingDown = false;
			}
		}
		else {
			myPendingDown = false;
		}

		myLastLowWasStrong = !myIsWeak;
		myHasLastLow = true;
		myPrevLow = myLastLow;
		myLastLow = myPivotLow[myIndex];

		if (myPrevHigh !== null && myLastHigh !== null && myPrevLow !== null) {
			let myNewTrend = myTrend;

			if (myLastHigh > myPrevHigh && myLastLow > myPrevLow) {
				myNewTrend = 'up';
			}
			else if (myLastHigh < myPrevHigh && myLastLow < myPrevLow) {
				myNewTrend = 'down';
			}
			else {
				myNewTrend = 'none';
			}

			if (myNewTrend !== 'up') {
				myPendingUp = false;
			}
			if (myNewTrend !== 'down') {
				myPendingDown = false;
			}

			myTrend = myNewTrend;
		}
	}

	// ---------------- Line value (recalculated every bar) ----------------
	if (myTrend === 'up') {
		myLineValue[myIndex] = myPendingUp ? myUpperBand[myIndex] : myLowerBand[myIndex];
	}
	else if (myTrend === 'down') {
		myLineValue[myIndex] = myPendingDown ? myLowerBand[myIndex] : myUpperBand[myIndex];
	}
	else {
		myLineValue[myIndex] = null;
	}

	myTrendSeries[myIndex] = myTrend;
	myPendingUpSeries[myIndex] = myPendingUp;
	myPendingDownSeries[myIndex] = myPendingDown;
}

// ---------------- Coloring ----------------
const myLineColor = for_every(myLineValue, close, (_lineValue, _close) => {
	if (_lineValue === null || _lineValue === undefined) {
		return 'gray';
	}
	return _lineValue < _close ? '#00e676' : '#ff5252';
});

// ---------------- Painting ----------------
const myLinePainted = paint(myLineValue, { name: 'Volume Exhaustion Line', color: myLineColor, thickness: 2, style: 'line' });
const myClosePainted = paint(close, { name: 'Close Fill Anchor', hidden: true });

fill(myLinePainted, myClosePainted, '#808080', 0.15);

// ---------------- Signals for scanner/alerts/strategy ----------------
const myIsBullish = for_every(myLineValue, close, (_lineValue, _close) => _lineValue !== null && _lineValue < _close);
const myIsBearish = for_every(myLineValue, close, (_lineValue, _close) => _lineValue !== null && _lineValue >= _close);
const myIsTrendUp = for_every(series_of(null), (_x, _prev, _idx) => myTrendSeries[_idx] === 'up');
const myIsTrendDown = for_every(series_of(null), (_x, _prev, _idx) => myTrendSeries[_idx] === 'down');
const myIsPendingUp = for_every(series_of(null), (_x, _prev, _idx) => myPendingUpSeries[_idx] === true);
const myIsPendingDown = for_every(series_of(null), (_x, _prev, _idx) => myPendingDownSeries[_idx] === true);

register_signal(myIsBullish, 'Bullish Line Below Price');
register_signal(myIsBearish, 'Bearish Line Above Price');
register_signal(myIsTrendUp, 'Trend Up');
register_signal(myIsTrendDown, 'Trend Down');
register_signal(myIsPendingUp, 'Pending Exhaustion Up');
register_signal(myIsPendingDown, 'Pending Exhaustion Down');