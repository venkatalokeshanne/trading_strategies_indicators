describe_indicator('EMA 9 20 SR Breakout Strategy', 'price');

const myTab = input.tab('Settings');
const myEma9Len = myTab.number('EMA Fast', 9, { min: 1, max: 200 });
const myEma20Len = myTab.number('EMA Slow', 20, { min: 1, max: 200 });
const mySrLookback = myTab.number('S/R Lookback Bars', 20, { min: 1, max: 200 });
const myTargetPct = myTab.number('Target Percent', 12, { min: 0.5, max: 100, step: 0.5 });
const mySlPct = myTab.number('Stop Loss Percent', 6, { min: 0.5, max: 100, step: 0.5 });
const myBodyRatioThreshold = myTab.number('Strong Candle Body Ratio', 0.3, { min: 0.01, max: 1, step: 0.01 });

// EMAs
const myEma9 = ema(close, myEma9Len);
const myEma20 = ema(close, myEma20Len);

paint(myEma9, { name: 'EMA9', color: 'orange', thickness: 2 });
paint(myEma20, { name: 'EMA20', color: 'blue', thickness: 2 });

// Pivot high/low, same window on both sides, like ta.pivothigh/pivotlow
const myPivotHigh = pivot_high(high, mySrLookback, mySrLookback);
const myPivotLow = pivot_low(low, mySrLookback, mySrLookback);

// Build short dotted segments around each pivot point (bar_index-4 to bar_index+4)
const mySrHighLine = series_of(null);
const mySrLowLine = series_of(null);

const myPivotHighPoints = indexed_points_of(myPivotHigh);
const myPivotLowPoints = indexed_points_of(myPivotLow);

myPivotHighPoints.forEach(_point => {
	const myFrom = Math.max(0, _point.candleIndex - 4);
	const myTo = Math.min(close.length - 1, _point.candleIndex + 4);
	for (let myIndex = myFrom; myIndex <= myTo; myIndex += 1) {
		mySrHighLine[myIndex] = _point.value;
	}
});

myPivotLowPoints.forEach(_point => {
	const myFrom = Math.max(0, _point.candleIndex - 4);
	const myTo = Math.min(close.length - 1, _point.candleIndex + 4);
	for (let myIndex = myFrom; myIndex <= myTo; myIndex += 1) {
		mySrLowLine[myIndex] = _point.value;
	}
});

paint(mySrHighLine, { name: 'Resistance', color: 'red', style: 'dotted', thickness: 2 });
paint(mySrLowLine, { name: 'Support', color: 'green', style: 'dotted', thickness: 2 });

// Strong candle filter
const myCandleRange = sub(high, low);
const myCandleBody = for_every(close, open, (_c, _o) => Math.abs(_c - _o));
const myStrongCandle = for_every(myCandleRange, myCandleBody, (_range, _body) => _range > 0 && (_body / _range) >= myBodyRatioThreshold);

// Crossover / crossunder of EMA9 vs EMA20
const myEmaCrossUp = for_every(myEma9, myEma20, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myEma9[_index - 1] <= myEma20[_index - 1] && _fast > _slow;
});

const myEmaCrossDown = for_every(myEma9, myEma20, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myEma9[_index - 1] >= myEma20[_index - 1] && _fast < _slow;
});

const myBuyCondition = for_every(myEmaCrossUp, close, myEma9, myStrongCandle, (_crossUp, _close, _fast9, _strong) => _crossUp && _close > _fast9 && _strong);
const mySellCondition = for_every(myEmaCrossDown, close, myEma9, myStrongCandle, (_crossDown, _close, _fast9, _strong) => _crossDown && _close < _fast9 && _strong);

// Position state machine, replicating the Pine strategy's entry/exit logic bar by bar.
// This is a stateful simulation (not a repeated indicator call), used to compute
// position state and exit triggers (target/stop) exactly like the Pine strategy.
const myPositionState = series_of(0); // 0 flat, 1 long, -1 short
const myEntryPrice = series_of(null);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);

let myCurrentState = 0;
let myCurrentEntryPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	let myExitLongThisBar = false;
	let myExitShortThisBar = false;

	if (myCurrentState === 1) {
		const myTargetPrice = myCurrentEntryPrice * (1 + myTargetPct / 100);
		const myStopPrice = myCurrentEntryPrice * (1 - mySlPct / 100);
		if (high[myIndex] >= myTargetPrice || low[myIndex] <= myStopPrice) {
			myExitLongThisBar = true;
			myCurrentState = 0;
			myCurrentEntryPrice = null;
		}
	}
	else if (myCurrentState === -1) {
		const myTargetPrice = myCurrentEntryPrice * (1 - myTargetPct / 100);
		const myStopPrice = myCurrentEntryPrice * (1 + mySlPct / 100);
		if (low[myIndex] <= myTargetPrice || high[myIndex] >= myStopPrice) {
			myExitShortThisBar = true;
			myCurrentState = 0;
			myCurrentEntryPrice = null;
		}
	}

	if (myCurrentState === 0) {
		if (myBuyCondition[myIndex]) {
			myCurrentState = 1;
			myCurrentEntryPrice = close[myIndex];
		}
		else if (mySellCondition[myIndex]) {
			myCurrentState = -1;
			myCurrentEntryPrice = close[myIndex];
		}
	}

	myPositionState[myIndex] = myCurrentState;
	myEntryPrice[myIndex] = myCurrentEntryPrice;
	myLongExitSignal[myIndex] = myExitLongThisBar;
	myShortExitSignal[myIndex] = myExitShortThisBar;
}

// Flat condition is based on the state BEFORE this bar's entry evaluation.
// Approximate using "not holding a position prior to signal evaluation this bar".
const myFlatBeforeEntry = for_every(myPositionState, (_state, _prev, _index) => {
	if (_index === 0) return true;
	return myPositionState[_index - 1] === 0;
});

const myBuySignal = for_every(myBuyCondition, myFlatBeforeEntry, (_buy, _flat) => _buy && _flat);
const mySellSignal = for_every(mySellCondition, myFlatBeforeEntry, (_sell, _flat) => _sell && _flat);

// Entry arrows
const myBuyMarks = for_every(myBuySignal, (_buy) => _buy ? true : null);
const mySellMarks = for_every(mySellSignal, (_sell) => _sell ? true : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Scanner / Alert / Strategy signals
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');
register_signal(myLongExitSignal, 'Long Exit Signal');
register_signal(myShortExitSignal, 'Short Exit Signal');
register_signal(for_every(myPositionState, _state => _state === 1), 'In Long Position');
register_signal(for_every(myPositionState, _state => _state === -1), 'In Short Position');