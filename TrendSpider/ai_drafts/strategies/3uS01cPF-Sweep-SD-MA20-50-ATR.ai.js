describe_indicator('Sweep + SD + MA20/50 + ATR', 'price');

// ===== INPUTS =====
const mySwingLen = input.number('Swing Length', 5, { min: 2, max: 50 });
const myRR = input.number('Risk Reward', 3.0, { min: 0.1, max: 20, step: 0.5 });
const myAtrMult = input.number('Minimum Sweep ATR', 0.5, { min: 0, max: 10, step: 0.1 });

// ===== MOVING AVERAGES =====
const myMa20 = sma(close, 20);
const myMa50 = sma(close, 50);

paint(myMa20, { name: 'MA20', color: 'green', thickness: 2 });
paint(myMa50, { name: 'MA50', color: 'red', thickness: 2 });

// ===== ATR =====
const myAtr = atr(high, low, close, 14);

// ===== PIVOT HIGH / LOW (peak located at the peak bar itself) =====
const myPivotHighAtPeak = pivot_high(high, mySwingLen, mySwingLen);
const myPivotLowAtPeak = pivot_low(low, mySwingLen, mySwingLen);

const myCandleCount = close.length;

// Pine's ta.pivothigh/pivotlow only "fires" (confirms) `swingLen` bars AFTER
// the peak bar. We shift the pivot events forward by `swingLen` bars to
// reproduce that confirmation delay exactly.
const myConfirmedSupplyEvent = series_of(null);
const myConfirmedDemandEvent = series_of(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myPivotHighAtPeak[myIndex] !== null && myPivotHighAtPeak[myIndex] !== undefined) {
		const myConfirmIndex = myIndex + mySwingLen;
		if (myConfirmIndex < myCandleCount) {
			myConfirmedSupplyEvent[myConfirmIndex] = {
				top: high[myIndex],
				bottom: Math.max(open[myIndex], close[myIndex])
			};
		}
	}
	if (myPivotLowAtPeak[myIndex] !== null && myPivotLowAtPeak[myIndex] !== undefined) {
		const myConfirmIndex = myIndex + mySwingLen;
		if (myConfirmIndex < myCandleCount) {
			myConfirmedDemandEvent[myConfirmIndex] = {
				bottom: low[myIndex],
				top: Math.min(open[myIndex], close[myIndex])
			};
		}
	}
}

// ===== STATEFUL LOOP: zones persistence, trend filters, sweeps, signals, =====
// ===== and a simplified single-position simulation (long/short exclusive) =====
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);

let mySupplyTop = null;
let mySupplyBottom = null;
let myDemandTop = null;
let myDemandBottom = null;

// Simplified position simulation, used only to reproduce
// Pine's "strategy.position_size == 0" gating condition.
// This is NOT a full backtest engine (no intrabar fill order logic),
// it only tracks whether a simulated position is open or closed.
let myPositionDirection = 0; // 0 = flat, 1 = long, -1 = short
let myStopLoss = null;
let myTakeProfit = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myConfirmedSupplyEvent[myIndex]) {
		mySupplyTop = myConfirmedSupplyEvent[myIndex].top;
		mySupplyBottom = myConfirmedSupplyEvent[myIndex].bottom;
	}
	if (myConfirmedDemandEvent[myIndex]) {
		myDemandTop = myConfirmedDemandEvent[myIndex].top;
		myDemandBottom = myConfirmedDemandEvent[myIndex].bottom;
	}

	// manage open simulated position (check exits before new entries, as in Pine's bar order)
	if (myPositionDirection === 1) {
		if (low[myIndex] <= myStopLoss || high[myIndex] >= myTakeProfit) {
			myPositionDirection = 0;
			myStopLoss = null;
			myTakeProfit = null;
		}
	}
	else if (myPositionDirection === -1) {
		if (high[myIndex] >= myStopLoss || low[myIndex] <= myTakeProfit) {
			myPositionDirection = 0;
			myStopLoss = null;
			myTakeProfit = null;
		}
	}

	const myMa20Now = myMa20[myIndex];
	const myMa50Now = myMa50[myIndex];
	const myMa20Prev = myIndex > 0 ? myMa20[myIndex - 1] : null;
	const myMa50Prev = myIndex > 0 ? myMa50[myIndex - 1] : null;
	const myAtrNow = myAtr[myIndex];

	const myBullTrend = myMa20Now !== null && myMa50Now !== null && myMa20Prev !== null && myMa50Prev !== null &&
		myMa20Now > myMa50Now && myMa20Now > myMa20Prev && myMa50Now > myMa50Prev;

	const myBearTrend = myMa20Now !== null && myMa50Now !== null && myMa20Prev !== null && myMa50Prev !== null &&
		myMa20Now < myMa50Now && myMa20Now < myMa20Prev && myMa50Now < myMa50Prev;

	const myTrendStrength = (myMa20Now !== null && myMa50Now !== null) ? Math.abs(myMa20Now - myMa50Now) : null;
	const myValidTrend = myTrendStrength !== null && myAtrNow !== null && myTrendStrength > myAtrNow * 0.2;

	const myLongSweep = myDemandBottom !== null && myAtrNow !== null &&
		low[myIndex] < myDemandBottom &&
		close[myIndex] > myDemandBottom &&
		(myDemandBottom - low[myIndex]) > myAtrNow * myAtrMult;

	const myShortSweep = mySupplyTop !== null && myAtrNow !== null &&
		high[myIndex] > mySupplyTop &&
		close[myIndex] < mySupplyTop &&
		(high[myIndex] - mySupplyTop) > myAtrNow * myAtrMult;

	const myIsFlat = myPositionDirection === 0;

	const myLong = myLongSweep && myBullTrend && myValidTrend && myIsFlat;
	const myShort = myShortSweep && myBearTrend && myValidTrend && myIsFlat;

	myLongCondition[myIndex] = myLong;
	myShortCondition[myIndex] = myShort;

	if (myLong) {
		myStopLoss = low[myIndex];
		const myRisk = close[myIndex] - myStopLoss;
		myTakeProfit = close[myIndex] + myRisk * myRR;
		myPositionDirection = 1;
	}
	else if (myShort) {
		myStopLoss = high[myIndex];
		const myRisk = myStopLoss - close[myIndex];
		myTakeProfit = close[myIndex] - myRisk * myRR;
		myPositionDirection = -1;
	}
}

// ===== SIGNAL MARKERS =====
const myBuyMarks = for_every(myLongCondition, _long => _long ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortCondition, _short => _short ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'lime' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// ===== VISUAL SCRIPT SIGNALS =====
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');