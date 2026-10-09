describe_indicator('Sebbiottino Trailing Stop (ZLEMA Bands)', 'price');

// NOTE: this is a best-effort translation of a TradingView STRATEGY script.
// TrendSpider Custom JS indicators do not have a broker/strategy emulator
// (no strategy.entry/strategy.exit, no intrabar fill order). Position size,
// entries and trailing stop exits are reproduced here with a manual state
// machine that approximates Pine's logic as closely as possible: stop
// exits are tested against low/high of the bar, and only one position can
// be open at a time (no pyramiding), matching the default Pine behavior.

const myLength = input.number('Length', 20, { min: 1, max: 500 });
const myBandMultiplier = input.number('Band Multiplier', 0.2, { min: 0.01, max: 10, step: 0.01 });
const myEmaLength = input.number('EMA Length', 15, { min: 1, max: 500 });

const myLag = Math.floor((myLength - 1) / 2);

// ZLEMA (zero-lag EMA): ema(src + (src - src[lag]), length)
const myLaggedClose = shift(close, myLag);
const myZlemaInput = add(close, sub(close, myLaggedClose));
const myZlema = ema(myZlemaInput, myLength);

// Volatility bands
const myAtr = atr(high, low, close, myLength);
const myHighestAtr = highest(myAtr, myLength * 3);
const myVolatility = mult(myHighestAtr, myBandMultiplier);

const myUpper = add(myZlema, myVolatility);
const myLower = sub(myZlema, myVolatility);

// EMA filter
const myEmaFilter = ema(close, myEmaLength);

const myCandleCount = close.length;

const myLongStopSeries = series_of(null);
const myShortStopSeries = series_of(null);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
const myLongEntrySeries = series_of(null);
const myShortEntrySeries = series_of(null);

let myTrend = 0;
let myPositionSize = 0;
let myLongStop = null;
let myShortStop = null;

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myLongFilter = close[myIndex] > myEmaFilter[myIndex];
	const myShortFilter = close[myIndex] < myEmaFilter[myIndex];

	const myCrossoverUpper = close[myIndex] > myUpper[myIndex] && close[myIndex - 1] <= myUpper[myIndex - 1];
	const myCrossunderLower = close[myIndex] < myLower[myIndex] && close[myIndex - 1] >= myLower[myIndex - 1];

	if (myCrossoverUpper && myLongFilter) {
		myTrend = 1;
	}
	if (myCrossunderLower && myShortFilter) {
		myTrend = -1;
	}

	const myCrossoverZlema = close[myIndex] > myZlema[myIndex] && close[myIndex - 1] <= myZlema[myIndex - 1];
	const myCrossunderZlema = close[myIndex] < myZlema[myIndex] && close[myIndex - 1] >= myZlema[myIndex - 1];

	const myLongEntry = myCrossoverZlema && myTrend === 1 && myLongFilter;
	const myShortEntry = myCrossunderZlema && myTrend === -1 && myShortFilter;

	// Check stop-based exits before processing new entries (approximation)
	if (myPositionSize > 0 && myLongStop !== null && low[myIndex] <= myLongStop) {
		myPositionSize = 0;
		myLongStop = null;
	}
	if (myPositionSize < 0 && myShortStop !== null && high[myIndex] >= myShortStop) {
		myPositionSize = 0;
		myShortStop = null;
	}

	if (myLongEntry) {
		myPositionSize = 1;
		myShortStop = null;
	}
	if (myShortEntry) {
		myPositionSize = -1;
		myLongStop = null;
	}

	if (myPositionSize > 0) {
		myLongStop = myLongStop === null ? myLower[myIndex] : Math.max(myLongStop, myLower[myIndex]);
	}
	if (myPositionSize < 0) {
		myShortStop = myShortStop === null ? myUpper[myIndex] : Math.min(myShortStop, myUpper[myIndex]);
	}
	if (myPositionSize === 0) {
		myLongStop = null;
		myShortStop = null;
	}

	myLongStopSeries[myIndex] = myPositionSize > 0 ? myLongStop : null;
	myShortStopSeries[myIndex] = myPositionSize < 0 ? myShortStop : null;
	myBuySignal[myIndex] = myLongEntry;
	mySellSignal[myIndex] = myShortEntry;
	myLongEntrySeries[myIndex] = myLongEntry ? low[myIndex] : null;
	myShortEntrySeries[myIndex] = myShortEntry ? high[myIndex] : null;
}

paint(myZlema, { name: 'Zlema', color: 'gray', thickness: 1, style: 'line' });
paint(myUpper, { name: 'Upper Band', color: 'silver', thickness: 1, style: 'dotted' });
paint(myLower, { name: 'Lower Band', color: 'silver', thickness: 1, style: 'dotted' });

paint(myLongStopSeries, { name: 'Long Stop', color: '#26A69A', thickness: 2, style: 'line' });
paint(myShortStopSeries, { name: 'Short Stop', color: '#EF5350', thickness: 2, style: 'line' });

paint(myLongEntrySeries, { name: 'Buy Label', color: 'green', style: 'labels_below' });
paint(myShortEntrySeries, { name: 'Sell Label', color: 'red', style: 'labels_above' });

register_signal(myBuySignal, 'Long Entry');
register_signal(mySellSignal, 'Short Entry');