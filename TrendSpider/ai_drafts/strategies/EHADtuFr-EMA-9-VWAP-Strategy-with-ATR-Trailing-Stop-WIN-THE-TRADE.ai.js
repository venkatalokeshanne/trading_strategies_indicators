describe_indicator('EMA 9 plus VWAP Strategy with ATR Trailing Stop', 'price');

// Inputs matching the Pine script (shortened titles to satisfy
// the platform's input name length limit)
const myAtrLength = input.number('ATR Len', 14, { min: 1, max: 200 });
const myAtrMult = input.number('ATR Mult', 2, { min: 0.1, max: 20 });

// Core indicators. VWAP here is session based (resets each session),
// matching ta.vwap(close) behavior in Pine (which resets daily by default).
const myEma9 = ema(close, 9);
const myVwap = vwap(hlc3, volume, 0);
const myAtr = atr(high, low, close, myAtrLength);

// Crossover / crossunder detection, same bar logic as ta.crossover/crossunder
const myLongCondition = for_every(myEma9, myVwap, (_ema, _vwap, _prev, _i) => {
	if (_i === 0) return false;
	return myEma9[_i - 1] <= myVwap[_i - 1] && _ema > _vwap;
});

const myShortCondition = for_every(myEma9, myVwap, (_ema, _vwap, _prev, _i) => {
	if (_i === 0) return false;
	return myEma9[_i - 1] >= myVwap[_i - 1] && _ema < _vwap;
});

// Position state simulation (long/short/flat) based on entry conditions
// Once a long/short is entered, it stays open until an opposite signal occurs
// (Pine's strategy.entry on same direction does not pyramid by default here,
// and there is no explicit opposite-close logic in the original script other
// than the trailing stop exit, which we approximate as "stop touched").
const myPositionState = series_of(0);
const myLongStopLine = series_of(null);
const myShortStopLine = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevState = myIndex > 0 ? myPositionState[myIndex - 1] : 0;
	const myPrevLongStop = myIndex > 0 ? myLongStopLine[myIndex - 1] : null;
	const myPrevShortStop = myIndex > 0 ? myShortStopLine[myIndex - 1] : null;

	let myState = myPrevState;

	// Entries
	if (myLongCondition[myIndex]) {
		myState = 1;
	}
	else if (myShortCondition[myIndex]) {
		myState = -1;
	}

	// Trailing stop exit check (approximation of strategy.exit trail logic)
	const myAtrValue = myAtr[myIndex] != null ? myAtr[myIndex] * myAtrMult : null;

	if (myState > 0 && myAtrValue != null) {
		const myCandidate = close[myIndex] - myAtrValue;
		const myNewStop = myPrevLongStop == null || myPrevState <= 0 ? myCandidate : Math.max(myPrevLongStop, myCandidate);

		if (low[myIndex] < myNewStop) {
			myState = 0;
			myLongStopLine[myIndex] = null;
		}
		else {
			myLongStopLine[myIndex] = myNewStop;
		}
	}
	else {
		myLongStopLine[myIndex] = null;
	}

	if (myState < 0 && myAtrValue != null) {
		const myCandidate = close[myIndex] + myAtrValue;
		const myNewStop = myPrevShortStop == null || myPrevState >= 0 ? myCandidate : Math.min(myPrevShortStop, myCandidate);

		if (high[myIndex] > myNewStop) {
			myState = 0;
			myShortStopLine[myIndex] = null;
		}
		else {
			myShortStopLine[myIndex] = myNewStop;
		}
	}
	else {
		myShortStopLine[myIndex] = null;
	}

	myPositionState[myIndex] = myState;
}

// Plot EMA and VWAP
paint(myEma9, { name: 'EMA9', color: '#ff9800', thickness: 2 });
paint(myVwap, { name: 'VWAP', color: '#2962ff', thickness: 2 });

// Plot trailing stop lines (ladder style approximates linebr behavior)
paint(myLongStopLine, { name: 'Long Trail Stop', color: '#2e7d32', style: 'ladder', thickness: 1 });
paint(myShortStopLine, { name: 'Short Trail Stop', color: '#c62828', style: 'ladder', thickness: 1 });

// Buy / Sell signal labels
const myBuyLabels = for_every(myLongCondition, _c => _c ? constants.icons.triangle_up : null);
const mySellLabels = for_every(myShortCondition, _c => _c ? constants.icons.triangle_down : null);

paint(myBuyLabels, { name: 'Buy Signal', style: 'labels_below', color: 'green' });
paint(mySellLabels, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// Register signals for scanners, alerts and strategy tester
register_signal(myLongCondition, 'Long Entry EMA9 Crosses Above VWAP');
register_signal(myShortCondition, 'Short Entry EMA9 Crosses Below VWAP');
register_signal(for_every(myPositionState, _s => _s > 0), 'In Long Position');
register_signal(for_every(myPositionState, _s => _s < 0), 'In Short Position');