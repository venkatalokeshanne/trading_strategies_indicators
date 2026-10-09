describe_indicator('BTC 4H RSI Plus Bullish Engulfing', 'price');

// This is a best-effort translation of a Pine Script v5 "strategy" into
// an indicator. TrendSpider custom indicators cannot run a full broker/
// position-sizing/order-execution engine like Pine strategies do, so the
// trade simulation below (entry price, stop, take profit tracking) is an
// approximation: entry price is approximated as the close of the signal
// bar, and the stop/exit check is evaluated using the following bar's
// low/high. The core signal logic (RSI, Bullish Engulfing, Volume High
// price lookup) is reproduced exactly as in the Pine script.

const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOversold = input.number('RSI Oversold', 30, { min: 1, max: 99 });
const myVolumeLookback = input.number('Volume Lookback', 100, { min: 1, max: 500 });
const mySlBufferPercent = input.number('SL Buffer Percent', 0.5, { min: 0, max: 50 });

const myRsi = rsi(close, myRsiLength);
const myHighestVol = highest(volume, myVolumeLookback);

const myCandleCount = close.length;

// Bullish Engulfing + oversold + long signal, computed bar by bar using
// plain array lookups (no built-in indicator calls inside the loop).
const myLongSignal = series_of(false);
const myStopLossCandidate = series_of(null);
const myVolumeHighPrice = series_of(null);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	// Replicates: stopLoss = low * (1 - slBuffer / 100), every bar
	myStopLossCandidate[myIndex] = low[myIndex] * (1 - mySlBufferPercent / 100);

	if (myIndex >= 1) {
		const myPrevBearish = close[myIndex - 1] < open[myIndex - 1];
		const myCurrentBullish = close[myIndex] > open[myIndex];
		const myBullishEngulfing = myPrevBearish
			&& myCurrentBullish
			&& open[myIndex] <= close[myIndex - 1]
			&& close[myIndex] >= open[myIndex - 1];

		const myOversoldCondition = myRsi[myIndex] !== null && myRsi[myIndex] < myRsiOversold;

		myLongSignal[myIndex] = Boolean(myBullishEngulfing && myOversoldCondition);
	}

	// Replicates the Pine "for i = 0 to lookbackVolume - 1" loop: scans
	// the trailing window and keeps the LAST match found (deepest in
	// history), exactly mirroring the Pine overwrite behavior.
	let myFoundVolumeHighClose = null;
	const myWindowSize = Math.min(myVolumeLookback, myIndex + 1);

	for (let myOffset = 0; myOffset < myWindowSize; myOffset += 1) {
		const myLookbackIndex = myIndex - myOffset;
		if (volume[myLookbackIndex] === myHighestVol[myIndex]) {
			myFoundVolumeHighClose = close[myLookbackIndex];
		}
	}

	myVolumeHighPrice[myIndex] = myFoundVolumeHighClose;
}

// Simplified position/exit simulation (approximation, see note above).
const myStopLossAtEntry = series_of(null);
const myTakeProfitAtEntry = series_of(null);
const myExitSignal = series_of(false);

let myInPosition = false;
let myEntryPrice = null;
let myActiveStopLoss = null;
let myActiveTakeProfit = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (!myInPosition) {
		if (myLongSignal[myIndex]) {
			myInPosition = true;
			myEntryPrice = close[myIndex];
			const myRisk = myEntryPrice - myStopLossCandidate[myIndex];
			const myMinTP = myEntryPrice + myRisk * 2;
			myActiveStopLoss = myStopLossCandidate[myIndex];
			myActiveTakeProfit = myVolumeHighPrice[myIndex] !== null
				? Math.max(myVolumeHighPrice[myIndex], myMinTP)
				: myMinTP;

			myStopLossAtEntry[myIndex] = myActiveStopLoss;
			myTakeProfitAtEntry[myIndex] = myActiveTakeProfit;
		}
	}
	else {
		myStopLossAtEntry[myIndex] = myActiveStopLoss;
		myTakeProfitAtEntry[myIndex] = myActiveTakeProfit;

		const myHitStop = low[myIndex] <= myActiveStopLoss;
		const myHitTarget = high[myIndex] >= myActiveTakeProfit;

		if (myHitStop || myHitTarget) {
			myExitSignal[myIndex] = true;
			myInPosition = false;
			myEntryPrice = null;
			myActiveStopLoss = null;
			myActiveTakeProfit = null;
		}
	}
}

// Visualization: Volume High price target line
paint(myVolumeHighPrice, { name: 'Volume Target', color: '#26A69A', thickness: 2 });

// Buy signal shapes below the bar
const myBuyMarks = for_every(close, (_c, _p, _i) => myLongSignal[_i] ? constants.icons.triangle_up : null);
paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#00E676' });

// Stop loss and take profit reference lines (only valid while in a trade)
paint(myStopLossAtEntry, { name: 'Stop Loss', color: '#EF5350', style: 'dotted' });
paint(myTakeProfitAtEntry, { name: 'Take Profit', color: '#4DA3FF', style: 'dotted' });

// Signals for scanners, alerts and strategy backtesting
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myExitSignal, 'Long Exit Signal');