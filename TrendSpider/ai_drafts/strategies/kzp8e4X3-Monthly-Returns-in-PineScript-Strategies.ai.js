describe_indicator('Pivot Reversal Signals', 'price');

// This indicator reproduces the pivot-based entry logic of the
// Pine Script strategy (PivRevLE / PivRevSE). The monthly/yearly
// P&L table and the strategy equity simulation from the original
// script cannot be reproduced here (see notes below) because the
// Custom JS API has no strategy/backtesting engine or table.new()
// equivalent that tracks equity curves.

const myLeftBars = input.number('Left Bars', 2, { min: 1, max: 50 });
const myRightBars = input.number('Right Bars', 1, { min: 1, max: 50 });

// Pivot high / low, mirroring Pine's pivothigh/pivotlow(leftBars, rightBars)
const mySwingHigh = pivot_high(high, myLeftBars, myRightBars);
const mySwingLow = pivot_low(low, myLeftBars, myRightBars);

// hprice/lprice: persist last known pivot value
const myHPrice = series_of(null);
const myLPrice = series_of(null);

// le/se: long entry / short entry state
const myLongEntry = series_of(false);
const myShortEntry = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevHPrice = myIndex > 0 ? myHPrice[myIndex - 1] : 0;
	const myPrevLPrice = myIndex > 0 ? myLPrice[myIndex - 1] : 0;
	const myPrevLE = myIndex > 0 ? myLongEntry[myIndex - 1] : false;
	const myPrevSE = myIndex > 0 ? myShortEntry[myIndex - 1] : false;

	myHPrice[myIndex] = mySwingHigh[myIndex] !== null ? mySwingHigh[myIndex] : myPrevHPrice;
	myLPrice[myIndex] = mySwingLow[myIndex] !== null ? mySwingLow[myIndex] : myPrevLPrice;

	if (mySwingHigh[myIndex] !== null) {
		myLongEntry[myIndex] = true;
	}
	else if (myPrevLE && high[myIndex] > myHPrice[myIndex]) {
		myLongEntry[myIndex] = false;
	}
	else {
		myLongEntry[myIndex] = myPrevLE;
	}

	if (mySwingLow[myIndex] !== null) {
		myShortEntry[myIndex] = true;
	}
	else if (myPrevSE && low[myIndex] < myLPrice[myIndex]) {
		myShortEntry[myIndex] = false;
	}
	else {
		myShortEntry[myIndex] = myPrevSE;
	}
}

// Entry signal fires on the bar where the state transitions from false to true
// (equivalent to a fresh strategy.entry call in Pine on each "le"/"se" bar).
const myLongEntrySignal = for_every(myLongEntry, (_le, _prev, _idx) => _le === true);
const myShortEntrySignal = for_every(myShortEntry, (_se, _prev, _idx) => _se === true);

paint(myHPrice, { name: 'HPrice', color: 'green', thickness: 2, style: 'line' });
paint(myLPrice, { name: 'LPrice', color: 'red', thickness: 2, style: 'line' });

register_signal(myLongEntrySignal, 'Pivot Reversal Long Entry');
register_signal(myShortEntrySignal, 'Pivot Reversal Short Entry');