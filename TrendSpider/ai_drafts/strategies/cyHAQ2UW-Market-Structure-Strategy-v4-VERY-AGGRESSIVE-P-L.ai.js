describe_indicator('Market Structure Strategy v4', 'price');

// ─────────────────────────────────────────────
// Inputs
// ─────────────────────────────────────────────
const myTab = input.tab('Structure');
const myExtLen = myTab.number('External Structure Length', 15, { min: 5, max: 100 });
const myIntLen = myTab.number('Internal Structure Length', 4, { min: 2, max: 100 });

const myRRTab = input.tab('Targets');
const myRRPartial = myRRTab.number('Partial Profit R', 1.0, { min: 0.1, max: 10 });
const myRRFinal = myRRTab.number('Final Target R', 1.8, { min: 0.1, max: 10 });

const myAtrTab = input.tab('ATR / ADX');
const myAtrLen = myAtrTab.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrMult = myAtrTab.number('ATR Stop Buffer', 0.4, { min: 0, max: 10 });
const myAdxLen = myAtrTab.number('DI Length', 14, { min: 1, max: 100 });
const myAdxSmooth = myAtrTab.number('ADX Smoothing', 14, { min: 1, max: 100 });
const myAdxMin = myAtrTab.number('Minimum ADX', 15, { min: 0, max: 100 });

// ─────────────────────────────────────────────
// Indicators
// ─────────────────────────────────────────────
const myAtr = atr(high, low, close, myAtrLen);

// NOTE: Pine's ta.dmi() takes a separate DI length and ADX smoothing length.
// Our built-in indicators.adx() only exposes one "period" parameter, so we
// approximate by using the ADX smoothing length for the whole computation.
const myAdxObject = indicators.adx(myAdxSmooth);
const myAdx = myAdxObject.adx;

// External structure pivots (left = right = length, matches ta.pivothigh/low)
const myExtHigh = pivot_high(high, myExtLen, myExtLen);
const myExtLow = pivot_low(low, myExtLen, myExtLen);

// Internal structure pivots
const myIntHigh = pivot_high(high, myIntLen, myIntLen);
const myIntLow = pivot_low(low, myIntLen, myIntLen);

const myCandleCount = close.length;
const myExtBiasSeries = series_of(0);
const myPbTopSeries = series_of(null);
const myPbBotSeries = series_of(null);
const myLongAllowedSeries = series_of(false);
const myShortAllowedSeries = series_of(false);
const myLongEntrySeries = series_of(false);
const myShortEntrySeries = series_of(false);
const myColorSeries = series_of(null);

let myLastExtHigh = null;
let myLastExtLow = null;
let myExtBias = 0;
let myLastHL = null;
let myLastLH = null;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myExtHigh[myIndex] !== null && myExtHigh[myIndex] !== undefined) {
		myLastExtHigh = myExtHigh[myIndex];
	}
	if (myExtLow[myIndex] !== null && myExtLow[myIndex] !== undefined) {
		myLastExtLow = myExtLow[myIndex];
	}
	if (myLastExtHigh !== null && close[myIndex] > myLastExtHigh) {
		myExtBias = 1;
	}
	if (myLastExtLow !== null && close[myIndex] < myLastExtLow) {
		myExtBias = -1;
	}
	if (myExtBias === 1 && myIntLow[myIndex] !== null && myIntLow[myIndex] !== undefined) {
		myLastHL = myIntLow[myIndex];
	}
	if (myExtBias === -1 && myIntHigh[myIndex] !== null && myIntHigh[myIndex] !== undefined) {
		myLastLH = myIntHigh[myIndex];
	}

	let myPbTop = null;
	let myPbBot = null;

	if (myExtBias === 1 && myLastHL !== null && myLastExtHigh !== null) {
		const myStructRange = myLastExtHigh - myLastHL;
		myPbTop = myLastExtHigh - myStructRange * 0.30;
		myPbBot = myLastExtHigh - myStructRange * 0.85;
	}
	if (myExtBias === -1 && myLastLH !== null && myLastExtLow !== null) {
		const myStructRange = myLastLH - myLastExtLow;
		myPbBot = myLastExtLow + myStructRange * 0.30;
		myPbTop = myLastExtLow + myStructRange * 0.85;
	}

	const myLongAllowed = myExtBias === 1 && myAdx[myIndex] > myAdxMin && myPbTop !== null && myPbBot !== null && low[myIndex] <= myPbTop && low[myIndex] >= myPbBot;
	const myShortAllowed = myExtBias === -1 && myAdx[myIndex] > myAdxMin && myPbTop !== null && myPbBot !== null && high[myIndex] >= myPbBot && high[myIndex] <= myPbTop;

	myExtBiasSeries[myIndex] = myExtBias;
	myPbTopSeries[myIndex] = myPbTop;
	myPbBotSeries[myIndex] = myPbBot;
	myLongAllowedSeries[myIndex] = myLongAllowed;
	myShortAllowedSeries[myIndex] = myShortAllowed;
	myLongEntrySeries[myIndex] = myLongAllowed && myLastHL !== null;
	myShortEntrySeries[myIndex] = myShortAllowed && myLastLH !== null;

	if (myExtBias === 1) {
		myColorSeries[myIndex] = 'rgba(38,166,154,0.15)';
	}
	else if (myExtBias === -1) {
		myColorSeries[myIndex] = 'rgba(239,83,80,0.15)';
	}
	else {
		myColorSeries[myIndex] = null;
	}
}

// Approximates Pine's bgcolor() by tinting candles, since the engine has
// no direct way to paint a full-panel background color.
color_candles(myColorSeries);

// ─────────────────────────────────────────────
// Visualization
// ─────────────────────────────────────────────
fill(
	paint(myPbTopSeries, { name: 'Pullback Top', color: '#4DA3FF', thickness: 1, style: 'dotted' }),
	paint(myPbBotSeries, { name: 'Pullback Bottom', color: '#4DA3FF', thickness: 1, style: 'dotted' }),
	'blue',
	0.1
);

const myLongMarks = for_every(myLongEntrySeries, low, (_long, _low) => _long ? _low : null);
const myShortMarks = for_every(myShortEntrySeries, high, (_short, _high) => _short ? _high : null);

paint(myLongMarks, { name: 'Long Entry', color: '#26A69A', thickness: 3, style: 'labels_below' });
paint(myShortMarks, { name: 'Short Entry', color: '#EF5350', thickness: 3, style: 'labels_above' });

// ─────────────────────────────────────────────
// Signals for Scanner / Alerts / Strategy Tester
// Each register_signal() call below uses a unique name, called exactly
// once, unconditionally, so the "already exists" collision cannot recur.
// ─────────────────────────────────────────────
register_signal(myLongEntrySeries, 'Long Entry Signal');
register_signal(myShortEntrySeries, 'Short Entry Signal');
register_signal(for_every(myExtBiasSeries, _bias => _bias === 1), 'Bullish Bias Signal');
register_signal(for_every(myExtBiasSeries, _bias => _bias === -1), 'Bearish Bias Signal');