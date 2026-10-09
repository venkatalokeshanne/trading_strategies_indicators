describe_indicator('Trend Pivot Scale In', 'price');

// NOTE: TrendSpider Custom JS has no native strategy/order engine
// (no strategy.entry, pyramiding, position tracking, intrabar fills).
// This script re-implements the Pine strategy logic manually using a
// candle-by-candle simulation loop. It reproduces the trend/pivot
// signal logic exactly, and approximates the scale-in / TP basket
// logic as closely as possible, but exact bar-by-bar fills (which
// depend on Pine's intrabar order execution model) cannot be
// guaranteed to be identical.

const myEmaLen = input.number('EMA Length', 200, { min: 1, max: 1000 });
const myPivotLen = input.number('Pivot Strength', 8, { min: 1, max: 100 });
const myAdxLen = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxMin = input.number('Min ADX', 25, { min: 1, max: 100 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 100 });

const myEma200 = ema(close, myEmaLen);

// NOTE: Pine's ta.dmi() allows separate smoothing length for ADX vs DI.
// indicators.adx() only exposes a single period parameter, so the
// "ADX Smooth" input from the original script could not be mapped
// one-to-one; we use myAdxLen for both DI and ADX smoothing.
const myAdxObject = indicators.adx(myAdxLen);
const myDiPlus = myAdxObject.dmiPlus;
const myDiMinus = myAdxObject.dmiMinus;
const myAdx = myAdxObject.adx;

const myBullTrend = for_every(close, myEma200, myDiPlus, myDiMinus, myAdx, (_c, _e, _dp, _dm, _a) =>
	_c > _e && _dp > _dm && _a > myAdxMin
);
const myBearTrend = for_every(close, myEma200, myDiPlus, myDiMinus, myAdx, (_c, _e, _dp, _dm, _a) =>
	_c < _e && _dm > _dp && _a > myAdxMin
);

const myPivotLow = pivot_low(low, myPivotLen, myPivotLen);
const myPivotHigh = pivot_high(high, myPivotLen, myPivotLen);

const myBuySignal = for_every(myBullTrend, myPivotLow, (_b, _p) => _b && _p !== null);
const mySellSignal = for_every(myBearTrend, myPivotHigh, (_b, _p) => _b && _p !== null);

const myAtr = atr(high, low, close, myAtrLen);

// Manual simulation of the scale-in strategy (10/10/20/40/80 cash sizing,
// averaging into losers only, basket closed on ATR-based TP).
const myCashTable = [10, 10, 20, 40, 80];

const myLongTPSeries = series_of(null);
const myShortTPSeries = series_of(null);

let myPositionSize = 0;
let myAvgPrice = 0;
let myLongAdds = 0;
let myShortAdds = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPositionSize === 0) {
		myLongAdds = 0;
		myShortAdds = 0;
	}

	const myLongCash = myCashTable[Math.min(myLongAdds, 4)];
	const myShortCash = myCashTable[Math.min(myShortAdds, 4)];
	const myLongQty = myLongCash / close[myIndex];
	const myShortQty = myShortCash / close[myIndex];

	// long entries (scale into losers only)
	if (myBuySignal[myIndex] && myLongAdds < 5 && myPositionSize >= 0) {
		if (myPositionSize === 0 || close[myIndex] < myAvgPrice) {
			const myNewSize = myPositionSize + myLongQty;
			myAvgPrice = myPositionSize > 0
				? (myAvgPrice * myPositionSize + close[myIndex] * myLongQty) / myNewSize
				: close[myIndex];
			myPositionSize = myNewSize;
			myLongAdds += 1;
		}
	}

	// short entries (scale into losers only)
	if (mySellSignal[myIndex] && myShortAdds < 5 && myPositionSize <= 0) {
		if (myPositionSize === 0 || close[myIndex] > myAvgPrice) {
			const myAbsSize = Math.abs(myPositionSize) + myShortQty;
			myAvgPrice = myPositionSize < 0
				? (myAvgPrice * Math.abs(myPositionSize) + close[myIndex] * myShortQty) / myAbsSize
				: close[myIndex];
			myPositionSize = -myAbsSize;
			myShortAdds += 1;
		}
	}

	const myOpenTrades = myPositionSize > 0 ? myLongAdds : (myPositionSize < 0 ? myShortAdds : 0);
	let myTpAtrMult = 3.0;
	if (myOpenTrades === 2) myTpAtrMult = 2.0;
	if (myOpenTrades === 3) myTpAtrMult = 1.5;
	if (myOpenTrades >= 4) myTpAtrMult = 1.2;

	if (myPositionSize > 0) {
		const myLongTP = myAvgPrice + (myAtr[myIndex] || 0) * myTpAtrMult;
		myLongTPSeries[myIndex] = myLongTP;
		// basket exit if TP touched intra-candle (approximation of strategy.exit limit)
		if (high[myIndex] >= myLongTP) {
			myPositionSize = 0;
			myAvgPrice = 0;
			myLongAdds = 0;
			myShortAdds = 0;
		}
	}
	else if (myPositionSize < 0) {
		const myShortTP = myAvgPrice - (myAtr[myIndex] || 0) * myTpAtrMult;
		myShortTPSeries[myIndex] = myShortTP;
		if (low[myIndex] <= myShortTP) {
			myPositionSize = 0;
			myAvgPrice = 0;
			myLongAdds = 0;
			myShortAdds = 0;
		}
	}
}

paint(myEma200, { name: 'EMA', color: '#FF9800', thickness: 2 });

const myBuyMarks = for_every(myBuySignal, _b => _b ? 1 : null);
const mySellMarks = for_every(mySellSignal, _s => _s ? 1 : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#00E676' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#FF1744' });

paint(myLongTPSeries, { name: 'LongTP', color: '#00E676', thickness: 2, style: 'line' });
paint(myShortTPSeries, { name: 'ShortTP', color: '#00E5FF', thickness: 2, style: 'line' });

register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');