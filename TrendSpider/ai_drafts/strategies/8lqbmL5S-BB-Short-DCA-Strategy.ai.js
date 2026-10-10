describe_indicator('BB Short DCA Strategy', 'price');

// Converts the Pine Script BB Short DCA strategy. Since the strategy
// is inherently sequential/stateful (DCA entries depend on prior bar
// state), the simulation is done in a single forward loop, which is
// allowed since no indicator functions are called inside the loop.

const myBbLength = input.number('BB Length', 20, { min: 1, max: 500 });
const myBbStd = input.number('BB StdDev', 2.0, { min: 0.1, max: 10 });
const mySignalAboveBBPercent = input.number('Percent Above BB', 1.0, { min: 0, max: 100 });
const myTakeProfitPercent = input.number('Take Profit Percent', 3.0, { min: 0.01, max: 100 });

const myEntry1USD = input.number('Entry 1 USD', 3000, { min: 1 });
const myEntry2USD = input.number('Entry 2 USD', 6000, { min: 1 });
const myEntry3USD = input.number('Entry 3 USD', 12000, { min: 1 });

// Start date filter: 1st Jan 2026, 00:00 UTC
const myStartTimestamp = Date.UTC(2026, 0, 1, 0, 0, 0) / 1000;

const mySignalAboveBB = mySignalAboveBBPercent / 100;
const myTpPercent = myTakeProfitPercent / 100;

const myBasis = sma(close, myBbLength);
const myDev = mult(stdev(close, myBbLength), myBbStd);
const myUpper = add(myBasis, myDev);
const myLower = sub(myBasis, myDev);

const myN = close.length;

// Output series
const mySignalMarks = series_of(null);
const myAvgPriceLine = series_of(null);
const myShortEntry1Signal = series_of(false);
const myShortEntry2Signal = series_of(false);
const myShortEntry3Signal = series_of(false);
const myTakeProfitSignal = series_of(false);

// Strategy state
let myPositionSize = 0;
let myEntry1Price = null;
let myEntry2Price = null;
let myEntry3Price = null;
let myEntry1Opened = false;
let myEntry2Opened = false;
let myEntry3Opened = false;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myClose = close[myIndex];
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myInTradeWindow = time[myIndex] >= myStartTimestamp;

	const myUpperValue = myUpper[myIndex];
	const mySignal = (myUpperValue != null) && (myClose > myUpperValue * (1 + mySignalAboveBB));

	if (mySignal && myInTradeWindow) {
		mySignalMarks[myIndex] = myHigh;
	}

	// Reset state when flat
	if (myPositionSize === 0) {
		myEntry1Opened = false;
		myEntry2Opened = false;
		myEntry3Opened = false;
		myEntry1Price = null;
		myEntry2Price = null;
		myEntry3Price = null;
	}

	let myClosedThisBar = false;

	// Entry #1
	if (mySignal && myPositionSize === 0 && myInTradeWindow) {
		myEntry1Price = myClose;
		myEntry1Opened = true;
		myPositionSize = -(myEntry1USD / myClose);
		myShortEntry1Signal[myIndex] = true;
	}

	// Only entry #1 opened
	if (myEntry1Opened && !myEntry2Opened) {
		const myAvgPrice = myEntry1Price;
		const myTpPrice = myAvgPrice * (1 - myTpPercent);

		if (myLow <= myTpPrice) {
			myPositionSize = 0;
			myTakeProfitSignal[myIndex] = true;
			myClosedThisBar = true;
		}

		if (!myClosedThisBar && myHigh >= myEntry1Price * 1.02) {
			myEntry2Price = myClose;
			myEntry2Opened = true;
			myPositionSize += -(myEntry2USD / myClose);
			myShortEntry2Signal[myIndex] = true;
		}
	}

	// Entry #1 + #2 opened
	if (!myClosedThisBar && myEntry1Opened && myEntry2Opened && !myEntry3Opened) {
		const myAvgPrice = (myEntry1Price * myEntry1USD + myEntry2Price * myEntry2USD) / (myEntry1USD + myEntry2USD);
		const myTpPrice = myAvgPrice * (1 - myTpPercent);

		if (myLow <= myTpPrice) {
			myPositionSize = 0;
			myTakeProfitSignal[myIndex] = true;
			myClosedThisBar = true;
		}

		if (!myClosedThisBar && myHigh >= myEntry2Price * 1.04) {
			myEntry3Price = myClose;
			myEntry3Opened = true;
			myPositionSize += -(myEntry3USD / myClose);
			myShortEntry3Signal[myIndex] = true;
		}
	}

	// Entry #1 + #2 + #3 opened
	if (!myClosedThisBar && myEntry1Opened && myEntry2Opened && myEntry3Opened) {
		const myAvgPrice = (myEntry1Price * myEntry1USD + myEntry2Price * myEntry2USD + myEntry3Price * myEntry3USD) / (myEntry1USD + myEntry2USD + myEntry3USD);
		const myTpPrice = myAvgPrice * (1 - myTpPercent);

		if (myLow <= myTpPrice) {
			myPositionSize = 0;
			myTakeProfitSignal[myIndex] = true;
			myClosedThisBar = true;
		}
	}

	// Average entry price for plotting
	if (myPositionSize !== 0) {
		let myWeightedSum = 0;
		let myWeightTotal = 0;
		if (myEntry1Opened) { myWeightedSum += myEntry1Price * myEntry1USD; myWeightTotal += myEntry1USD; }
		if (myEntry2Opened) { myWeightedSum += myEntry2Price * myEntry2USD; myWeightTotal += myEntry2USD; }
		if (myEntry3Opened) { myWeightedSum += myEntry3Price * myEntry3USD; myWeightTotal += myEntry3USD; }
		myAvgPriceLine[myIndex] = myWeightTotal > 0 ? (myWeightedSum / myWeightTotal) : null;
	}
	else {
		myAvgPriceLine[myIndex] = null;
	}
}

paint(myBasis, { name: 'BB Basis', color: '#f0c000', style: 'line' });
paint(myUpper, { name: 'BB Upper', color: '#e04040', style: 'line' });
paint(myLower, { name: 'BB Lower', color: '#2fa84f', style: 'line' });
paint(myAvgPriceLine, { name: 'Average Entry Price', color: '#ff8c00', thickness: 2, style: 'line' });
paint(mySignalMarks, { name: 'Short Signal', color: '#e04040', style: 'labels_above' });

register_signal(myShortEntry1Signal, 'Short Entry 1');
register_signal(myShortEntry2Signal, 'Short Entry 2');
register_signal(myShortEntry3Signal, 'Short Entry 3');
register_signal(myTakeProfitSignal, 'Take Profit Close');