describe_indicator('Grover Llorens Activator', 'price');

// Pine inputs replicated as TrendSpider inputs
const myLength = input.number('Length', 480, { min: 1, max: 5000 });
const myMult = input.number('Mult', 14, { min: 1, max: 100 });
const mySource = input.select('Source', 'close', constants.price_source_options);
const myPrice = market[mySource];
const myAtr = atr(high, low, close, myLength);
const myN = close.length;

// Output series
const myTS = series_of(null);
const myUp = series_of(false);
const myDn = series_of(false);

// Internal state replicating Pine's "valuewhen" and "barssince"
let myLastVal = null;
let myBarsSince = 0;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	const myPrevTS = myIndex > 0 ? myTS[myIndex - 1] : null;
	const myPrevSrc = myIndex > 0 ? myPrice[myIndex - 1] : myPrice[myIndex];

	// nz(ts[1], src[1])
	const myTSBase = myPrevTS !== null && myPrevTS !== undefined ? myPrevTS : myPrevSrc;
	const myDiff = myPrice[myIndex] - myTSBase;
	const myPrevDiff = myIndex > 0 ? (myPrice[myIndex - 1] - (myIndex > 1 ? (myTS[myIndex - 2] !== null && myTS[myIndex - 2] !== undefined ? myTS[myIndex - 2] : myPrice[myIndex - 2]) : myPrice[myIndex - 1])) : 0;

	// crossover / crossunder of diff vs 0
	const myIsUp = myIndex > 0 && myDiff > 0 && myPrevDiff <= 0;
	const myIsDn = myIndex > 0 && myDiff < 0 && myPrevDiff >= 0;

	myUp[myIndex] = myIsUp;
	myDn[myIndex] = myIsDn;

	if (myIsUp || myIsDn) {
		myLastVal = myAtr[myIndex] / myLength;
		myBarsSince = 0;
	}
	else {
		myBarsSince += 1;
	}

	const myNzTSBase = myPrevTS !== null && myPrevTS !== undefined ? myPrevTS : myPrice[myIndex];
	const mySign = myDiff > 0 ? 1 : (myDiff < 0 ? -1 : 0);
	const myVal = myLastVal !== null ? myLastVal : 0;
	let myTSValue;

	if (myIsUp) {
		myTSValue = myNzTSBase - myAtr[myIndex] * myMult;
	}
	else if (myIsDn) {
		myTSValue = myNzTSBase + myAtr[myIndex] * myMult;
	}
	else {
		myTSValue = myNzTSBase + mySign * myVal * myBarsSince;
	}

	myTS[myIndex] = myTSValue;
}

// Buy/Sell signal markers on the price chart
const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myUp[myIndex]) {
		myBuyMarks[myIndex] = low[myIndex];
	}
	if (myDn[myIndex]) {
		mySellMarks[myIndex] = high[myIndex];
	}
}

paint(myTS, { name: 'Activator', color: '#2196f3', thickness: 2, style: 'line' });
paint(myBuyMarks, { name: 'Buy Signal', color: '#0cb51a', style: 'labels_below' });
paint(mySellMarks, { name: 'Sell Signal', color: '#e65100', style: 'labels_above' });

// Signals usable in Scanner/Alerts/Strategy Tester
// Renamed to avoid name clash with the paint() calls above,
// which use the same labels for the on-chart markers.
register_signal(myUp, 'Buy Signal Trigger');
register_signal(myDn, 'Sell Signal Trigger');