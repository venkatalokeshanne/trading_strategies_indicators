describe_indicator('Joey Strategy (converted)', 'lower');

// ============================================================
// Inputs (mirroring the Pine Script "Joey Strategy" inputs)
// ============================================================
const myStochLength = input.number('Stochastic Length', 14, { min: 1, max: 500 });
const myOversold = input.number('Oversold', 30, { min: 1, max: 99 });
const mySmoothK = input.number('Smooth K', 3, { min: 1, max: 100 });
const mySmoothD = input.number('Smooth D', 3, { min: 1, max: 100 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
// Shortened input name (previous name was too long for the engine)
const myAtrMultiplier = input.number('ATR TP/SL Mult', 1.5, { min: 0.1, max: 50, step: 0.1 });

// ============================================================
// Stochastic calculation (identical to ta.stoch + double smoothing)
// ============================================================
const myRawStoch = stochastic(close, high, low, myStochLength);
const myK = sma(myRawStoch, mySmoothK);
const myD = sma(myK, mySmoothD);

// Crossover of K above D, while K is below Oversold level
const myLongSignalRaw = for_every(myK, myD, (_k, _d, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevK = myK[_i - 1];
	const myPrevD = myD[_i - 1];
	const myCrossOver = (myPrevK <= myPrevD) && (_k > _d);
	return myCrossOver && (_k < myOversold);
});

// ATR used for Take Profit / Stop Loss distance
const myAtr = atr(high, low, close, myAtrLength);

// ============================================================
// Trade simulation (position state machine), approximating
// Pine Script's strategy.entry / strategy.exit behavior.
// Assumption: entry fills at the signal bar's close, and the
// exit (limit TP / stop SL) is checked against High/Low of the
// following bars, same as strategy.exit() intrabar logic.
// ============================================================
const myPositionSize = series_of(0);
const myEntryPrice = series_of(null);
const myTakeProfit = series_of(null);
const myStopLoss = series_of(null);
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevPosition = myIndex > 0 ? myPositionSize[myIndex - 1] : 0;
	const myPrevEntryPrice = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;
	const myPrevTakeProfit = myIndex > 0 ? myTakeProfit[myIndex - 1] : null;
	const myPrevStopLoss = myIndex > 0 ? myStopLoss[myIndex - 1] : null;

	let myCurrentPosition = myPrevPosition;
	let myCurrentEntryPrice = myPrevEntryPrice;
	let myCurrentTakeProfit = myPrevTakeProfit;
	let myCurrentStopLoss = myPrevStopLoss;
	let myDidEnter = false;
	let myDidExit = false;

	if (myPrevPosition > 0) {
		// check for exit via TP/SL hit on this bar
		const myHitTakeProfit = myPrevTakeProfit !== null && high[myIndex] >= myPrevTakeProfit;
		const myHitStopLoss = myPrevStopLoss !== null && low[myIndex] <= myPrevStopLoss;

		if (myHitTakeProfit || myHitStopLoss) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myCurrentTakeProfit = null;
			myCurrentStopLoss = null;
			myDidExit = true;
		}
	}

	if (myCurrentPosition === 0 && myLongSignalRaw[myIndex]) {
		myCurrentPosition = 1;
		myCurrentEntryPrice = close[myIndex];
		const myAtrAtEntry = myAtr[myIndex];
		myCurrentTakeProfit = myCurrentEntryPrice + myAtrAtEntry * myAtrMultiplier;
		myCurrentStopLoss = myCurrentEntryPrice - myAtrAtEntry * myAtrMultiplier;
		myDidEnter = true;
	}

	myPositionSize[myIndex] = myCurrentPosition;
	myEntryPrice[myIndex] = myCurrentEntryPrice;
	myTakeProfit[myIndex] = myCurrentTakeProfit;
	myStopLoss[myIndex] = myCurrentStopLoss;
	myEntrySignal[myIndex] = myDidEnter;
	myExitSignal[myIndex] = myDidExit;
}

// ============================================================
// Painting
// ============================================================
paint(myK, { name: 'K', color: '#4DA3FF', thickness: 2 });
paint(myD, { name: 'D', color: '#EF5350', thickness: 2 });
paint(horizontal_line(myOversold), { name: 'Oversold', color: 'gray', style: 'dotted' });
paint(myTakeProfit, { name: 'TakeProfit', color: '#26A69A', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myStopLoss, { name: 'StopLoss', color: '#EF5350', thickness: 1, style: 'dotted', forceUsePriceAxis: true });

const myEntryMarks = for_every(myEntrySignal, myK, (_e, _k) => (_e ? _k : null));
paint(myEntryMarks, { name: 'EntryMarker', color: '#26A69A', thickness: 4, style: 'dotted' });

// ============================================================
// Scanner / Alert / Strategy signals
// ============================================================
register_signal(myEntrySignal, 'Long Entry');
register_signal(myExitSignal, 'Long Exit');