describe_indicator('TWE 2 Bar Break Strategy', 'price');

// EMA trend filter length
const myEmaLength = input.number('EMA Trend Filter', 50, { min: 1, max: 500 });

const myEmaTrend = ema(close, myEmaLength);

// Two bar break levels: max/min of the 2 preceding bars
const myHigh1 = shift(high, 1);
const myHigh2 = shift(high, 2);
const myLow1 = shift(low, 1);
const myLow2 = shift(low, 2);

const myTwoBarHigh = max_of(myHigh1, myHigh2);
const myTwoBarLow = min_of(myLow1, myLow2);

const myN = close.length;

const myBuySignalSeries = series_of(false);
const mySellSignalSeries = series_of(false);
const myCloseBuySeries = series_of(false);
const myCloseSellSeries = series_of(false);

const myBuyMarks = series_of(null);
const mySellMarks = series_of(null);
const myCloseBuyMarks = series_of(null);
const myCloseSellMarks = series_of(null);

// Sequential position simulation (0 = flat, 1 = long, -1 = short).
// This replicates strategy.position_size behavior bar by bar, since
// this logic depends on prior state and must not call indicator
// functions in a loop (we only use plain arithmetic here).
let myPrevPosition = 0;

for (let myIndex = 0; myIndex < myN; myIndex += 1) {
	if (myIndex < 2) {
		// Not enough bars yet to compute two-bar high/low
		myBuySignalSeries[myIndex] = false;
		mySellSignalSeries[myIndex] = false;
		myCloseBuySeries[myIndex] = false;
		myCloseSellSeries[myIndex] = false;
		continue;
	}

	const myUpTrend = close[myIndex] > myEmaTrend[myIndex];
	const myDownTrend = close[myIndex] < myEmaTrend[myIndex];

	const myTwoBarHighValue = myTwoBarHigh[myIndex];
	const myTwoBarLowValue = myTwoBarLow[myIndex];

	const myBuySignal = high[myIndex] > myTwoBarHighValue && myUpTrend;
	const mySellSignal = low[myIndex] < myTwoBarLowValue && myDownTrend;

	const myCloseBuy = myPrevPosition > 0 && low[myIndex] < myTwoBarLowValue;
	const myCloseSell = myPrevPosition < 0 && high[myIndex] > myTwoBarHighValue;

	let myPosition = myPrevPosition;

	if (myBuySignal && myPosition <= 0) {
		myPosition = 1;
	}
	if (mySellSignal && myPosition >= 0) {
		myPosition = -1;
	}
	if (myCloseBuy && myPosition > 0) {
		myPosition = 0;
	}
	if (myCloseSell && myPosition < 0) {
		myPosition = 0;
	}

	myBuySignalSeries[myIndex] = myBuySignal;
	mySellSignalSeries[myIndex] = mySellSignal;
	myCloseBuySeries[myIndex] = myCloseBuy;
	myCloseSellSeries[myIndex] = myCloseSell;

	myBuyMarks[myIndex] = myBuySignal ? low[myIndex] : null;
	mySellMarks[myIndex] = mySellSignal ? high[myIndex] : null;
	myCloseBuyMarks[myIndex] = myCloseBuy ? high[myIndex] : null;
	myCloseSellMarks[myIndex] = myCloseSell ? low[myIndex] : null;

	myPrevPosition = myPosition;
}

paint(myEmaTrend, { name: 'EMA Trend', color: '#f5c542', thickness: 2 });

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });
paint(myCloseBuyMarks, { name: 'Close Buy', style: 'labels_above', color: 'orange' });
paint(myCloseSellMarks, { name: 'Close Sell', style: 'labels_below', color: 'orange' });

register_signal(myBuySignalSeries, 'Buy Signal');
register_signal(mySellSignalSeries, 'Sell Signal');
register_signal(myCloseBuySeries, 'Close Buy Signal');
register_signal(myCloseSellSeries, 'Close Sell Signal');