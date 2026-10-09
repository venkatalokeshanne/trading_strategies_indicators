describe_indicator('MACD Plus EMA18 Signal Strategy', 'price');

// NOTE: This is a conversion of a TradingView Pine strategy into a
// TrendSpider indicator. Buy/Sell "signals" are reproduced exactly
// as the Pine logic defines them, including the "one trade at a
// time" state machine (noPosition logic). Since TrendSpider custom
// indicators cannot place actual orders, the strategy.entry/close
// logic is reproduced as a position state tracker used purely to
// decide when BUY/SELL labels should appear, and these states are
// also exposed via register_signal() so they can be used in
// Scanners, Alerts and the Strategy Tester.

const myEma18 = ema(close, 18);
const mySmaHigh = sma(high, 10);
const mySmaLow = sma(low, 10);

// MACD(12,26,9)
const myMacdLine = sub(ema(close, 12), ema(close, 26));
const mySignalLine = ema(myMacdLine, 9);

// Manual crossover/crossunder detection (previous vs current bar)
const myPrevMacd = shift(myMacdLine, 1);
const myPrevSignal = shift(mySignalLine, 1);

const myCandleCount = close.length;
// Replaced "new Array(...).fill(...)" with Array.from, since "new" is prohibited
const myPositionArr = Array.from({ length: myCandleCount }, () => 0);
const myBuySignalArr = Array.from({ length: myCandleCount }, () => false);
const mySellSignalArr = Array.from({ length: myCandleCount }, () => false);

for (let myIndex = 1; myIndex < myCandleCount; myIndex += 1) {
	const myCrossOver = myMacdLine[myIndex] > mySignalLine[myIndex] && myPrevMacd[myIndex] <= myPrevSignal[myIndex];
	const myCrossUnder = myMacdLine[myIndex] < mySignalLine[myIndex] && myPrevMacd[myIndex] >= myPrevSignal[myIndex];

	const myBuyCondition = myCrossOver && close[myIndex] > myEma18[myIndex];
	const mySellCondition = myCrossUnder && close[myIndex] < myEma18[myIndex];

	let myNewPosition = myPositionArr[myIndex - 1];

	// Exits (checked before new entries, matching Pine execution order)
	if (myNewPosition > 0 && (close[myIndex] < mySmaLow[myIndex] || myCrossUnder)) {
		myNewPosition = 0;
	}
	if (myNewPosition < 0 && (close[myIndex] > mySmaHigh[myIndex] || myCrossOver)) {
		myNewPosition = 0;
	}

	const myNoPosition = myNewPosition === 0;

	if (myBuyCondition && myNoPosition) {
		myNewPosition = 1;
		myBuySignalArr[myIndex] = true;
	}
	if (mySellCondition && myNoPosition) {
		myNewPosition = -1;
		mySellSignalArr[myIndex] = true;
	}

	myPositionArr[myIndex] = myNewPosition;
}

const myBuyLabels = myBuySignalArr.map(_v => _v ? constants.icons.triangle_up : null);
const mySellLabels = mySellSignalArr.map(_v => _v ? constants.icons.triangle_down : null);

paint(myEma18, { name: 'EMA18', color: '#4DA3FF', thickness: 2 });
paint(myBuyLabels, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellLabels, { name: 'Sell', style: 'labels_above', color: 'red' });

register_signal(myBuySignalArr, 'Buy Signal');
register_signal(mySellSignalArr, 'Sell Signal');
register_signal(myPositionArr.map(_p => _p > 0), 'In Long Position');
register_signal(myPositionArr.map(_p => _p < 0), 'In Short Position');