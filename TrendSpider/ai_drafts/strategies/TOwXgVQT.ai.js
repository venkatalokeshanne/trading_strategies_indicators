// NOTE: This script reproduces the QQE calculation and the long/short
// opposite-signal logic from the Pine Script exactly. However, TrendSpider's
// Custom JS API has no strategy/backtesting engine (strategy.entry,
// strategy.closedtrades, equity tracking, commissions, pyramiding, etc.),
// so the "points table" and trade bookkeeping from the Pine strategy cannot
// be reproduced. This indicator exposes the same long/short signals as
// register_signal() outputs (usable in Scanner/Alerts/Strategy Tester) and
// paints them on the chart, which is the closest equivalent available.
describe_indicator('QQE System Opposite Signal', 'lower');

const myRsiPeriod = input.number('RSI Length', 14, { min: 1, max: 200 });
const mySmoothFactor = input.number('RSI Smoothing', 5, { min: 1, max: 200 });
const myQqeFactor = input.number('Fast QQE Factor', 4.238, { min: 0.1, max: 20 });
const myShowLabels = input.boolean('Show BUY/SELL Labels', true);

const myWildersPeriod = myRsiPeriod * 2 - 1;

// === Core QQE math ===
const myRsi = rsi(close, myRsiPeriod);
const myRsiMa = ema(myRsi, mySmoothFactor);

// AtrRsi = abs(RsiMa[1] - RsiMa)
const myShiftedRsiMa = shift(myRsiMa, 1);
const myAtrRsi = for_every(myShiftedRsiMa, myRsiMa, (_prev, _cur) => (_prev == null ? 0 : Math.abs(_prev - _cur)));

const myMaAtrRsi = ema(myAtrRsi, myWildersPeriod);
const myDar = mult(ema(myMaAtrRsi, myWildersPeriod), myQqeFactor);

const myCandleCount = close.length;

const myLongband = series_of(null);
const myShortband = series_of(null);
const myTrend = series_of(null);
const myFastLine = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myRsIndex = myRsiMa[myIndex];
	const myDelta = myDar[myIndex];
	const myNewLong = myRsIndex - myDelta;
	const myNewShort = myRsIndex + myDelta;

	const myPrevRsIndex = myIndex > 0 ? myRsiMa[myIndex - 1] : null;
	const myPrevLongband = myIndex > 0 ? myLongband[myIndex - 1] : null;
	const myPrevShortband = myIndex > 0 ? myShortband[myIndex - 1] : null;
	const myPrevTrend = myIndex > 0 ? myTrend[myIndex - 1] : null;

	let myLong;
	if (myPrevRsIndex != null && myPrevLongband != null && myPrevRsIndex > myPrevLongband && myRsIndex > myPrevLongband) {
		myLong = Math.max(myPrevLongband, myNewLong);
	}
	else {
		myLong = myNewLong;
	}

	let myShort;
	if (myPrevRsIndex != null && myPrevShortband != null && myPrevRsIndex < myPrevShortband && myRsIndex < myPrevShortband) {
		myShort = Math.min(myPrevShortband, myNewShort);
	}
	else {
		myShort = myNewShort;
	}

	myLongband[myIndex] = myLong;
	myShortband[myIndex] = myShort;

	let myCrossUp = false;
	let myCrossDown = false;

	if (myIndex >= 2) {
		// cross(RSIndex, shortband[1])
		const myA0 = myRsiMa[myIndex - 1];
		const myB0 = myShortband[myIndex - 2];
		const myA1 = myRsiMa[myIndex];
		const myB1 = myShortband[myIndex - 1];
		myCrossUp = (myA0 - myB0) * (myA1 - myB1) < 0;

		// cross(longband[1], RSIndex)
		const myC0 = myLongband[myIndex - 2];
		const myD0 = myRsiMa[myIndex - 1];
		const myC1 = myLongband[myIndex - 1];
		const myD1 = myRsiMa[myIndex];
		myCrossDown = (myC0 - myD0) * (myC1 - myD1) < 0;
	}

	myTrend[myIndex] = myCrossUp ? 1 : (myCrossDown ? -1 : (myPrevTrend != null ? myPrevTrend : 1));
	myFastLine[myIndex] = myTrend[myIndex] == 1 ? myLong : myShort;

	if (myIndex > 0) {
		const myPrevFastLine = myFastLine[myIndex - 1];
		myLongSignal[myIndex] = myFastLine[myIndex] < myRsIndex && myPrevFastLine >= myPrevRsIndex;
		myShortSignal[myIndex] = myFastLine[myIndex] > myRsIndex && myPrevFastLine <= myPrevRsIndex;
	}
}

const myBuyMarkers = for_every(myLongSignal, myRsiMa, (_signal, _value) => (_signal ? _value : null));
const mySellMarkers = for_every(myShortSignal, myRsiMa, (_signal, _value) => (_signal ? _value : null));

paint(myRsiMa, { name: 'RsiMa', color: '#4DA3FF', thickness: 1 });
paint(myFastLine, { name: 'FastLine', color: '#FFB300', thickness: 2 });

// Labels approximate the Pine label.new() markers; custom per-bar text is
// not supported for multi-bar label series in the Custom JS API, so plain
// colored markers are used instead.
paint(myShowLabels ? myBuyMarkers : constants.empty_series, { name: 'BuySignal', style: 'labels_below', color: 'green', thickness: 6 });
paint(myShowLabels ? mySellMarkers : constants.empty_series, { name: 'SellSignal', style: 'labels_above', color: 'red', thickness: 6 });

register_signal(myLongSignal, 'QQE Long Signal');
register_signal(myShortSignal, 'QQE Short Signal');