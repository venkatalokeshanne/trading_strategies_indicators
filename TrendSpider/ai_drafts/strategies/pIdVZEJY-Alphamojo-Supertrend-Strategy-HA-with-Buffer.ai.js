describe_indicator('Supertrend Strategy HA with Buffer', 'price');

// Converts the given Pine Script Supertrend-on-Heikin-Ashi strategy.
// Pine's strategy.entry(..., stop=price) places a STOP order which only
// fills once price actually trades through that stop level on a future
// bar. This script can't simulate broker order fills/pyramiding, so it
// approximates "entry" as a signal fired on the bar where the Heikin
// Ashi Supertrend direction flips, using the same buffered stop price
// as a reference level (painted as a label), not as a guaranteed fill.

const myAtrPeriod = input.number('ATR Length', 10, { min: 1, max: 200 });
const myFactor = input.number('Factor', 3.0, { min: 0.05, max: 20, step: 0.05 });
const myBufferPercent = input.number('Buffer Percentage', 0.05, { min: 0, max: 10, step: 0.01 });
const myBufferDecimal = myBufferPercent / 100;

const myLength = close.length;

// Build Heikin Ashi OHLC manually (recursive, cannot be vectorized)
// Using series_of() instead of "new Array()" since "new" is prohibited
const myHaOpen = series_of(null);
const myHaClose = series_of(null);
const myHaHigh = series_of(null);
const myHaLow = series_of(null);

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myRawClose = (open[myIndex] + high[myIndex] + low[myIndex] + close[myIndex]) / 4;
	const myRawOpen = myIndex === 0
		? (open[myIndex] + close[myIndex]) / 2
		: (myHaOpen[myIndex - 1] + myHaClose[myIndex - 1]) / 2;

	myHaClose[myIndex] = myRawClose;
	myHaOpen[myIndex] = myRawOpen;
	myHaHigh[myIndex] = Math.max(high[myIndex], myRawOpen, myRawClose);
	myHaLow[myIndex] = Math.min(low[myIndex], myRawOpen, myRawClose);
}

// ATR computed on the synthetic Heikin Ashi series (built-in atr supports custom series)
const myHaAtr = atr(myHaHigh, myHaLow, myHaClose, myAtrPeriod);

// Manual Supertrend computation on HA data (final bands + direction + line)
const mySupertrendLine = series_of(null);
const myDirection = series_of(null);

let myPrevUpperBand = null;
let myPrevLowerBand = null;
let myPrevDirection = -1;
let myPrevSupertrend = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myHl2 = (myHaHigh[myIndex] + myHaLow[myIndex]) / 2;
	const myAtrValue = myHaAtr[myIndex];

	if (myAtrValue === null || myAtrValue === undefined || isNaN(myAtrValue)) {
		mySupertrendLine[myIndex] = null;
		myDirection[myIndex] = myPrevDirection;
		continue;
	}

	let myBasicUpper = myHl2 + myFactor * myAtrValue;
	let myBasicLower = myHl2 - myFactor * myAtrValue;

	if (myPrevUpperBand === null) {
		myPrevUpperBand = myBasicUpper;
		myPrevLowerBand = myBasicLower;
	}
	else {
		myBasicUpper = (myBasicUpper < myPrevUpperBand || myHaClose[myIndex - 1] > myPrevUpperBand)
			? myBasicUpper
			: myPrevUpperBand;
		myBasicLower = (myBasicLower > myPrevLowerBand || myHaClose[myIndex - 1] < myPrevLowerBand)
			? myBasicLower
			: myPrevLowerBand;
	}

	let myCurrDirection = myPrevDirection;

	if (myPrevSupertrend === null) {
		myCurrDirection = -1;
	}
	else if (myPrevSupertrend === myPrevUpperBand) {
		myCurrDirection = myHaClose[myIndex] > myBasicUpper ? -1 : 1;
	}
	else {
		myCurrDirection = myHaClose[myIndex] < myBasicLower ? 1 : -1;
	}

	const myCurrSupertrend = myCurrDirection === -1 ? myBasicLower : myBasicUpper;

	mySupertrendLine[myIndex] = myCurrSupertrend;
	myDirection[myIndex] = myCurrDirection;

	myPrevUpperBand = myBasicUpper;
	myPrevLowerBand = myBasicLower;
	myPrevSupertrend = myCurrSupertrend;
	myPrevDirection = myCurrDirection;
}

// Buffered stop prices (reference levels, not guaranteed fills)
const myBufferLong = mult(myHaHigh, myBufferDecimal);
const myBufferShort = mult(myHaLow, myBufferDecimal);
const myLongStopPrice = add(myHaHigh, myBufferLong);
const myShortStopPrice = sub(myHaLow, myBufferShort);

// Detect direction flips (equivalent of ta.change(haDirection))
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myLongLevel = series_of(null);
const myShortLevel = series_of(null);

for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	const myChange = myDirection[myIndex] - myDirection[myIndex - 1];

	if (myChange < 0) {
		myLongSignal[myIndex] = true;
		myLongLevel[myIndex] = myLongStopPrice[myIndex];
	}
	if (myChange > 0) {
		myShortSignal[myIndex] = true;
		myShortLevel[myIndex] = myShortStopPrice[myIndex];
	}
}

// Color the Supertrend line like the Pine plot (green on uptrend, red on downtrend)
const mySupertrendColor = for_every(series_of(0), (_zero, _prev, _index) => myDirection[_index] < 0 ? 'green' : 'red');

const mySupertrendPainted = paint(mySupertrendLine, { name: 'HASupertrend', color: mySupertrendColor, thickness: 2 });

// Reference stop levels at the flip bars (approximation of entry trigger prices)
paint(myLongLevel, { name: 'LongStopLevel', color: '#26A69A', style: 'dotted', thickness: 1 });
paint(myShortLevel, { name: 'ShortStopLevel', color: '#EF5350', style: 'dotted', thickness: 1 });

// Scanner / Alert / Strategy applicable signals
register_signal(myLongSignal, 'Long Entry Signal');
register_signal(myShortSignal, 'Short Entry Signal');