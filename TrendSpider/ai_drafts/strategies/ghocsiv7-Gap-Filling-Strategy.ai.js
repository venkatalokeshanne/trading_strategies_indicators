describe_indicator('Gap Filling Strategy', 'price');

// NOTE: TrendSpider Custom JS indicators cannot manage actual
// strategy positions, order fills or stop/limit exits like Pine
// Script strategies do. This script reproduces the Pine logic's
// underlying math (gap detection, the "lim" level) and exposes
// Buy/Sell/Close conditions as signals so they can be used in
// scanners, alerts and the Strategy Tester, but the actual
// position management (stops/limits execution) is not simulated.

const myInvert = input.boolean('Invert', false);
const myCloseWhen = input.select('Close When', 'New Session', ['New Session', 'New Gap', 'Reverse Position']);

const myLength = close.length;

// detect a new session (equivalent of change(time("D")) in Pine)
const mySessionId = time.map(_t => {
	const myParsed = time_of(_t);
	return `${myParsed.year}-${myParsed.dayOfYear}`;
});

const mySes = series_of(false);
for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	mySes[myIndex] = mySessionId[myIndex] !== mySessionId[myIndex - 1];
}
mySes[0] = false;

// gap detection, using previous candle's open/close
const myUpGap = series_of(false);
const myDnGap = series_of(false);
const myVal = series_of(null);

for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	const myO = open[myIndex];
	const myC = close[myIndex];
	const myPrevO = open[myIndex - 1];
	const myPrevC = close[myIndex - 1];

	const myUp = myO > high[myIndex - 1] && Math.min(myC, myO) > Math.max(myPrevC, myPrevO);
	const myDn = myO < low[myIndex - 1] && Math.min(myPrevC, myPrevO) > Math.max(myC, myO);

	myUpGap[myIndex] = myUp;
	myDnGap[myIndex] = myDn;
	myVal[myIndex] = myUp ? Math.max(myPrevC, myPrevO) : (myDn ? Math.min(myPrevC, myPrevO) : null);
}
myUpGap[0] = false;
myDnGap[0] = false;

// valuewhen(ses and (upgap or dngap), val, 0): carries forward the
// last value of "val" captured at a bar satisfying the condition
const myLim = series_of(null);
for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myCondition = mySes[myIndex] && (myUpGap[myIndex] || myDnGap[myIndex]);
	if (myCondition) {
		myLim[myIndex] = myVal[myIndex];
	}
	else {
		myLim[myIndex] = myIndex > 0 ? myLim[myIndex - 1] : null;
	}
}

// entry conditions, respecting the "invert" toggle
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);
for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	if (myInvert) {
		myBuySignal[myIndex] = mySes[myIndex] && myUpGap[myIndex];
		mySellSignal[myIndex] = mySes[myIndex] && myDnGap[myIndex];
	}
	else {
		myBuySignal[myIndex] = mySes[myIndex] && myDnGap[myIndex];
		mySellSignal[myIndex] = mySes[myIndex] && myUpGap[myIndex];
	}
}

// strategy.close_all condition
const myCloseAllSignal = series_of(false);
for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	if (myCloseWhen === 'New Session') {
		myCloseAllSignal[myIndex] = mySes[myIndex];
	}
	else if (myCloseWhen === 'New Gap') {
		myCloseAllSignal[myIndex] = mySes[myIndex] && (myUpGap[myIndex] || myDnGap[myIndex]);
	}
	else {
		myCloseAllSignal[myIndex] = false;
	}
}

// exit conditions: price reaching the lim level (limit for non
// inverted mode, stop for inverted mode) - approximated as price
// crossing the lim level, since real order fill simulation is not
// available in this environment
const myExitBuySignal = series_of(false);
const myExitSellSignal = series_of(false);
for (let myIndex = 1; myIndex < myLength; myIndex += 1) {
	if (myLim[myIndex] === null) {
		continue;
	}
	if (myInvert) {
		myExitBuySignal[myIndex] = low[myIndex] <= myLim[myIndex];
		myExitSellSignal[myIndex] = high[myIndex] >= myLim[myIndex];
	}
	else {
		myExitBuySignal[myIndex] = high[myIndex] >= myLim[myIndex];
		myExitSellSignal[myIndex] = low[myIndex] <= myLim[myIndex];
	}
}

paint(myLim, { name: 'LimitStop', color: '#ff1100', thickness: 2 });

register_signal(myBuySignal, 'Buy');
register_signal(mySellSignal, 'Sell');
register_signal(myCloseAllSignal, 'CloseAll');
register_signal(myExitBuySignal, 'ExitBuy');
register_signal(myExitSellSignal, 'ExitSell');