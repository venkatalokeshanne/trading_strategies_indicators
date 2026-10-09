describe_indicator('Momentum Squeeze Breakout Engine', 'price');

const myTab = input.tab('Settings');
const mySqueezeLength = myTab.number('Consolidation Lookback Period', 20, { min: 1, max: 500 });
const myBbMult = myTab.number('Bollinger Bands Width', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myKcMult = myTab.number('Keltner Channel Width', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myStructuralLen = myTab.number('Holistic Trend Bias Period', 20, { min: 1, max: 500 });
const myTrendFilter = myTab.number('Macro Trend Baseline EMA', 200, { min: 1, max: 1000 });

const myN = close.length;

// --- 1. Consolidation Block (Squeeze) ---
const myBasis = sma(close, mySqueezeLength);
const myDev = mult(stdev(close, mySqueezeLength), myBbMult);
const myUpperBB = add(myBasis, myDev);
const myLowerBB = sub(myBasis, myDev);

// True Range, computed manually since this needs previous close
const myPrevClose = shift(close, 1);
const myTrueRange = for_every(high, low, myPrevClose, (_h, _l, _pc) => {
	if (_pc === null || _pc === undefined) {
		return _h - _l;
	}
	return Math.max(_h - _l, Math.abs(_h - _pc), Math.abs(_l - _pc));
});

const myMaKC = sma(close, mySqueezeLength);
const myTrSMA = sma(myTrueRange, mySqueezeLength);
const myUpperKC = add(myMaKC, mult(myTrSMA, myKcMult));
const myLowerKC = sub(myMaKC, mult(myTrSMA, myKcMult));

const myIsSqueezed = for_every(myLowerBB, myLowerKC, myUpperBB, myUpperKC, (_lb, _lk, _ub, _uk) => (_lb > _lk) && (_ub < _uk));

// --- 2. Macro Trend Filter ---
const myMacroFilter = ema(close, myTrendFilter);

// --- 3. Holistic Bias ---
const myClosePos = for_every(high, low, close, (_h, _l, _c) => (_h - _l === 0) ? 0.0 : (((_c - _l) / (_h - _l)) * 2.0 - 1.0));
const myCumBias = sma(myClosePos, myStructuralLen);

// --- 4. Rate of Change ---
const myPriceROC = roc(close, 3);

// --- 5 & 6. Loop-driven state logic (barssince squeeze, crossover/crossunder, signal spacing) ---
const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);
const myConfirmedAccumulation = series_of(false);
const myConfirmedDistribution = series_of(false);

let myLastSignalBar = -1000;
let myBarsSinceSqueeze = 1000;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myIsSqueezed[myIndex]) {
		myBarsSinceSqueeze = 0;
	}
	else {
		myBarsSinceSqueeze += 1;
	}

	const myWasSqueezedRecently = myBarsSinceSqueeze <= 3;

	const myCrossOverUpperBB = myIndex > 0 && close[myIndex - 1] <= myUpperBB[myIndex - 1] && close[myIndex] > myUpperBB[myIndex];
	const myCrossUnderLowerBB = myIndex > 0 && close[myIndex - 1] >= myLowerBB[myIndex - 1] && close[myIndex] < myLowerBB[myIndex];

	const myAccumulation = myWasSqueezedRecently
		&& myCrossOverUpperBB
		&& (myCumBias[myIndex] > 0)
		&& (close[myIndex] > myMacroFilter[myIndex])
		&& (myPriceROC[myIndex] > 0);

	const myDistribution = myWasSqueezedRecently
		&& myCrossUnderLowerBB
		&& (myCumBias[myIndex] <= 0);

	myConfirmedAccumulation[myIndex] = myAccumulation;
	myConfirmedDistribution[myIndex] = myDistribution;

	if (myAccumulation && myIndex > myLastSignalBar + 15) {
		myBuyMarks[myIndex] = high[myIndex];
		myLastSignalBar = myIndex;
	}

	if (myDistribution && myIndex > myLastSignalBar + 15) {
		mySellMarks[myIndex] = low[myIndex];
		myLastSignalBar = myIndex;
	}
}

// --- 7. Visualization ---
const myUpperBBPainted = paint(myUpperBB, { name: 'Upper BB', color: 'silver', thickness: 1, style: 'dotted' });
const myLowerBBPainted = paint(myLowerBB, { name: 'Lower BB', color: 'silver', thickness: 1, style: 'dotted' });
fill(myUpperBBPainted, myLowerBBPainted, 'blue', 0.08);

paint(myMacroFilter, { name: 'EMA200 Baseline', color: 'orange', thickness: 2 });

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red', thickness: 3 });

// Squeeze zone background approximated as a thin marker line, since
// bgcolor() shading is not available in Custom JS API
const mySqueezeMarker = for_every(myIsSqueezed, _s => _s ? 1 : null);
paint(mySqueezeMarker, { name: 'Squeeze Zone', style: 'labels_below', color: 'blue', thickness: 1 });

register_signal(myConfirmedAccumulation, 'Confirmed Accumulation Buy Signal');
register_signal(myConfirmedDistribution, 'Confirmed Distribution Exit Signal');
register_signal(for_every(myBuyMarks, _m => _m !== null), 'Buy Signal Bar');
register_signal(for_every(mySellMarks, _m => _m !== null), 'Exit Signal Bar');