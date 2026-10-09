describe_indicator('ROC and RSI Tolerance Buy Sell Indicator', 'price');

// Inputs, organized following the original Pine script groups
const rocTab = input.tab('ROC Settings');
const myRocLength = rocTab.number('ROC Length', 9, { min: 1, max: 500 });

const rsiTab = input.tab('RSI Settings');
const myRsiLength = rsiTab.number('RSI Length', 14, { min: 1, max: 500 });
const myRsiMaLength = rsiTab.number('RSI MA Length', 14, { min: 1, max: 500 });

const signalTab = input.tab('Signal Settings');
const myTolerance = signalTab.number('Tolerance Bars', 2, { min: 0, max: 500 });

// Core calculations, mirroring ta.roc, ta.rsi and ta.sma from Pine
const myRoc = roc(close, myRocLength);
const myRsi = rsi(close, myRsiLength);
const myRsiMa = sma(myRsi, myRsiMaLength);
const myLength = close.length;

// Crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myRocCrossUp = series_of(false);
const myRocCrossDown = series_of(false);
const myRsiCrossUp = series_of(false);
const myRsiCrossDown = series_of(false);

for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	const myRocPrev = myRoc[myIndex - 1];
	const myRocCurr = myRoc[myIndex];
	const myRsiPrev = myRsi[myIndex - 1];
	const myRsiCurr = myRsi[myIndex];
	const myRsiMaPrev = myRsiMa[myIndex - 1];
	const myRsiMaCurr = myRsiMa[myIndex];

	if (myRocPrev != null && myRocCurr != null) {
		myRocCrossUp[myIndex] = myRocPrev <= 0 && myRocCurr > 0;
		myRocCrossDown[myIndex] = myRocPrev >= 0 && myRocCurr < 0;
	}
	if (myRsiPrev != null && myRsiCurr != null && myRsiMaPrev != null && myRsiMaCurr != null) {
		myRsiCrossUp[myIndex] = myRsiPrev <= myRsiMaPrev && myRsiCurr > myRsiMaCurr;
		myRsiCrossDown[myIndex] = myRsiPrev >= myRsiMaPrev && myRsiCurr < myRsiMaCurr;
	}
}

// Bars since last crossover/crossunder, replicating ta.barssince()
// null means "never happened yet", treated like Pine's na, which gets
// replaced with (tolerance + 1) via nz() in the original script.
const myBarsSinceRocUp = series_of(null);
const myBarsSinceRocDown = series_of(null);
const myBarsSinceRsiUp = series_of(null);
const myBarsSinceRsiDown = series_of(null);

let myLastRocUp = null;
let myLastRocDown = null;
let myLastRsiUp = null;
let myLastRsiDown = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	if (myRocCrossUp[myIndex]) { myLastRocUp = myIndex; }
	if (myRocCrossDown[myIndex]) { myLastRocDown = myIndex; }
	if (myRsiCrossUp[myIndex]) { myLastRsiUp = myIndex; }
	if (myRsiCrossDown[myIndex]) { myLastRsiDown = myIndex; }

	myBarsSinceRocUp[myIndex] = myLastRocUp === null ? null : myIndex - myLastRocUp;
	myBarsSinceRocDown[myIndex] = myLastRocDown === null ? null : myIndex - myLastRocDown;
	myBarsSinceRsiUp[myIndex] = myLastRsiUp === null ? null : myIndex - myLastRsiUp;
	myBarsSinceRsiDown[myIndex] = myLastRsiDown === null ? null : myIndex - myLastRsiDown;
}

// Signal logic, replicating the Pine buy_signal / sell_signal formulas
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myNzBarsSinceRsiUp = myBarsSinceRsiUp[myIndex] === null ? (myTolerance + 1) : myBarsSinceRsiUp[myIndex];
	const myNzBarsSinceRocUp = myBarsSinceRocUp[myIndex] === null ? (myTolerance + 1) : myBarsSinceRocUp[myIndex];
	const myNzBarsSinceRsiDown = myBarsSinceRsiDown[myIndex] === null ? (myTolerance + 1) : myBarsSinceRsiDown[myIndex];
	const myNzBarsSinceRocDown = myBarsSinceRocDown[myIndex] === null ? (myTolerance + 1) : myBarsSinceRocDown[myIndex];

	myBuySignal[myIndex] = (myRocCrossUp[myIndex] && myNzBarsSinceRsiUp <= myTolerance) ||
		(myRsiCrossUp[myIndex] && myNzBarsSinceRocUp <= myTolerance);
	mySellSignal[myIndex] = (myRocCrossDown[myIndex] && myNzBarsSinceRsiDown <= myTolerance) ||
		(myRsiCrossDown[myIndex] && myNzBarsSinceRocDown <= myTolerance);
}

// Build sparse series for plotshape-like markers below/above bars
const myBuyMarks = for_every(low, myBuySignal, (_low, _buy) => _buy ? _low : null);
const mySellMarks = for_every(high, mySellSignal, (_high, _sell) => _sell ? _high : null);

// Note: paint() and register_signal() output names must be unique across
// the whole indicator, so the registered signals use distinct names from
// the painted lines (that was the cause of the "already exists" error).
paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: 'red' });

// Register signals for use in Scanners, Alerts and Strategy Tester
register_signal(myBuySignal, 'Buy Signal Series');
register_signal(mySellSignal, 'Sell Signal Series');