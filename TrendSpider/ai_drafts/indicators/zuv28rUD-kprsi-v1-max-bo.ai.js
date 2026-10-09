describe_indicator('KPRSI DivSell DivBuy V1', 'price');

// === INPUTS ===
const myInputsTab = input.tab('KPRSI Settings');
const myRow1 = myInputsTab.row();
const myEmaLen = myRow1.number('EMA Length', 20, { min: 1, max: 500 });
const myRsiLen = myRow1.number('RSI Length', 14, { min: 2, max: 100 });

const myRow2 = myInputsTab.row();
const myPivLeft = myRow2.number('Pivot Left', 5, { min: 1, max: 50 });
const myPivRight = myRow2.number('Pivot Right', 5, { min: 1, max: 50 });

const myRow3 = myInputsTab.row();
const mySlopeSens = myRow3.number('EMA Slope Threshold (%)', 0.05, { min: 0, max: 10 });
const myTolerance = myRow3.number('Price Equality Tolerance (%)', 0.2, { min: 0, max: 10 });

// === CORE SERIES ===
const myEma20 = ema(close, myEmaLen);
const myRsi = rsi(close, myRsiLen);

// pivot_high / pivot_low mark the pivot value at the pivot candle's own index,
// equivalent to Pine's "high[pivRight]" lookback once confirmed.
const myPh = pivot_high(high, myPivLeft, myPivRight);
const myPl = pivot_low(low, myPivLeft, myPivRight);

const myLength = close.length;

const myFilteredSellArr = series_of(null);
const myNewBuySignalArr = series_of(null);
const myBearDivArr = series_of(false);
const myBullDivArr = series_of(false);

// === STATEFUL LOOP (mirrors Pine's "var" persistent variables) ===
let myPrevPriceHigh = null, myLastPriceHigh = null;
let myPrevRsiHigh = null, myLastRsiHigh = null;
let myPrevHighBar = null, myLastHighBar = null;

let myPrevPriceLow = null, myLastPriceLow = null;
let myPrevRsiLow = null, myLastRsiLow = null;
let myPrevLowBar = null, myLastLowBar = null;

let myLastSellPivotBar = null;
let myLastBuyPivotBar = null;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	if (myPh[myIndex] != null) {
		myPrevPriceHigh = myLastPriceHigh;
		myPrevRsiHigh = myLastRsiHigh;
		myPrevHighBar = myLastHighBar;

		myLastPriceHigh = myPh[myIndex];
		myLastRsiHigh = myRsi[myIndex];
		myLastHighBar = myIndex;
	}

	if (myPl[myIndex] != null) {
		myPrevPriceLow = myLastPriceLow;
		myPrevRsiLow = myLastRsiLow;
		myPrevLowBar = myLastLowBar;

		myLastPriceLow = myPl[myIndex];
		myLastRsiLow = myRsi[myIndex];
		myLastLowBar = myIndex;
	}

	const myEmaSlope = (myIndex > 0 && myEma20[myIndex - 1])
		? (myEma20[myIndex] - myEma20[myIndex - 1]) / myEma20[myIndex - 1] * 100
		: 0;

	const myEmaUp = myEmaSlope > mySlopeSens;
	const myEmaDown = myEmaSlope < -mySlopeSens;

	const myPriceDiffLow = (myLastPriceLow != null && myPrevPriceLow != null && myPrevPriceLow !== 0)
		? Math.abs((myLastPriceLow - myPrevPriceLow) / myPrevPriceLow) * 100
		: null;

	const myPriceDiffHigh = (myLastPriceHigh != null && myPrevPriceHigh != null && myPrevPriceHigh !== 0)
		? Math.abs((myLastPriceHigh - myPrevPriceHigh) / myPrevPriceHigh) * 100
		: null;

	const myBullDiv = myLastPriceLow != null && myPrevPriceLow != null && myLastRsiLow != null && myPrevRsiLow != null &&
		((myLastPriceLow < myPrevPriceLow) || myPriceDiffLow <= myTolerance) &&
		(myLastRsiLow > myPrevRsiLow);

	const myBearDiv = myLastPriceHigh != null && myPrevPriceHigh != null && myLastRsiHigh != null && myPrevRsiHigh != null &&
		((myLastPriceHigh > myPrevPriceHigh) || myPriceDiffHigh <= myTolerance) &&
		(myLastRsiHigh < myPrevRsiHigh);

	const myDivSell = myBearDiv && myEmaDown && close[myIndex] < myEma20[myIndex];
	const myDivBuy = myBullDiv && myEmaUp && close[myIndex] > myEma20[myIndex];

	const myNewSellSignal = myDivSell && (myLastSellPivotBar == null || myLastSellPivotBar !== myLastHighBar);
	const myNewBuySignal = myDivBuy && (myLastBuyPivotBar == null || myLastBuyPivotBar !== myLastLowBar);

	if (myNewSellSignal) {
		myLastSellPivotBar = myLastHighBar;
	}
	if (myNewBuySignal) {
		myLastBuyPivotBar = myLastLowBar;
	}

	const myRsiDivStrength = (myPrevRsiHigh != null && myLastRsiHigh != null) ? (myPrevRsiHigh - myLastRsiHigh) : 0;
	const myCandleBody = open[myIndex] !== 0 ? Math.abs(close[myIndex] - open[myIndex]) / open[myIndex] * 100 : 0;

	const myFilteredSell = myNewSellSignal && myRsiDivStrength >= 1.5 && myCandleBody <= 2.0;

	myFilteredSellArr[myIndex] = myFilteredSell ? high[myIndex] : null;
	myNewBuySignalArr[myIndex] = myNewBuySignal ? low[myIndex] : null;
	myBearDivArr[myIndex] = myBearDiv;
	myBullDivArr[myIndex] = myBullDiv;
}

// === PAINT ===
paint(myEma20, { name: 'EMA20', color: 'orange', thickness: 2 });
paint(myFilteredSellArr, { name: 'DivSell', style: 'labels_above', color: 'red' });
paint(myNewBuySignalArr, { name: 'DivBuy', style: 'labels_below', color: 'teal' });

// === SCANNER AND STRATEGY SIGNALS ===
register_signal(for_every(myFilteredSellArr, _v => _v != null), 'Filtered Sell');
register_signal(for_every(myNewBuySignalArr, _v => _v != null), 'New Buy');
register_signal(myBearDivArr, 'Bearish Divergence');
register_signal(myBullDivArr, 'Bullish Divergence');