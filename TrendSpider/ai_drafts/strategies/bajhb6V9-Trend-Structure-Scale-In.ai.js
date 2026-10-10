// This indicator approximates the Pine Script "Trend Structure Scale-In"
// strategy as a TrendSpider indicator with register_signal() outputs.
// IMPORTANT: Custom JS API has no concept of strategy.equity, strategy.position_size,
// strategy.position_avg_price, box.new() or line.set_xy...() objects that mutate
// over time. Position/avg-price/equity tracking below is approximated with a
// simplified running state machine computed in a single forward loop, using
// relative weights (pct) instead of real dollar equity (which is not
// retrievable from this API). TP / box zones are approximated with painted
// series instead of TradingView box/line objects.
describe_indicator('Trend Structure Scale In', 'price');

const myPivotLeft = input.number('Pivot Left Bars', 5, { min: 1, max: 50 });
const myPivotRight = input.number('Pivot Right Bars', 5, { min: 1, max: 50 });
const myZoneMaxBars = input.number('Max Bars to Mitigate', 20, { min: 1, max: 200 });

const myEmaColor = 'orange';
const myBuyColor = 'gray';
const mySellColor = 'red';

// --- EMA 200 ---
const myEma200 = ema(close, 200);

// --- Pivots ---
// TrendSpider pivot_high/pivot_low already return a sparse series aligned
// the same way Pine's ta.pivothigh/pivotlow does (value placed at the pivot
// bar, confirmed `pivotRight` bars later).
const myPivotHighSeries = pivot_high(high, myPivotLeft, myPivotRight);
const myPivotLowSeries = pivot_low(low, myPivotLeft, myPivotRight);

const myOpenPrev = shift(open, 1);
const myClosePrev = shift(close, 1);

// --- Engulfing patterns ---
const myBullEngulfing = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _oPrev, _cPrev) => {
	return _c > _o && _c > _oPrev && _o < _cPrev && _cPrev < _oPrev;
});

const myBearEngulfing = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _oPrev, _cPrev) => {
	return _c < _o && _c < _oPrev && _o > _cPrev && _cPrev > _oPrev;
});

const myBarCount = close.length;

// Output series
const myBullTouchSignal = series_of(false);
const myBearTouchSignal = series_of(false);

const myLongEntry1 = series_of(false);
const myLongEntry2 = series_of(false);
const myLongEntry3 = series_of(false);
const myLongEntry4 = series_of(false);
const myLongEntry5 = series_of(false);

const myShortEntry1 = series_of(false);
const myShortEntry2 = series_of(false);
const myShortEntry3 = series_of(false);
const myShortEntry4 = series_of(false);
const myShortEntry5 = series_of(false);

const myLongTpSignal = series_of(false);
const myShortTpSignal = series_of(false);

const myTpLine = series_of(null);
const myBullBoxTop = series_of(null);
const myBullBoxBot = series_of(null);
const myBearBoxTop = series_of(null);
const myBearBoxBot = series_of(null);

// Forward-looping state (mirrors the Pine var-state machine)
let myLastPivotLowBar = 0;
let myLastPivotHighBar = 0;

let myBullZoneTop = null;
let myBullZoneBot = null;
let myBullZoneStart = 0;

let myBearZoneTop = null;
let myBearZoneBot = null;
let myBearZoneStart = 0;

let myNumTrades = 0;
let myIsLong = false;
let myIsShort = false;

// Weighted-average entry price approximation: since real strategy equity
// is unavailable, weights use the Pine `pct` ratios directly (0.005, 0.005,
// 0.01, 0.02, 0.04) instead of `equity * pct`. This preserves the relative
// scale-in weighting logic but not the absolute dollar amounts.
const myPctByTrade = [0.005, 0.005, 0.01, 0.02, 0.04];
let myWeightedPriceSum = 0;
let myWeightSum = 0;
let myAvgPrice = null;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	if (myPivotLowSeries[myIndex] !== null && myPivotLowSeries[myIndex] !== undefined) {
		myLastPivotLowBar = myIndex;
	}
	if (myPivotHighSeries[myIndex] !== null && myPivotHighSeries[myIndex] !== undefined) {
		myLastPivotHighBar = myIndex;
	}

	// Bullish setup
	if (
		myBullEngulfing[myIndex] &&
		(myIndex - myLastPivotLowBar <= 10) &&
		(myLastPivotLowBar > myBullZoneStart) &&
		close[myIndex] > myEma200[myIndex]
	) {
		myBullZoneTop = close[myIndex];
		myBullZoneBot = open[myIndex];
		myBullZoneStart = myIndex;
	}

	// Bearish setup
	if (
		myBearEngulfing[myIndex] &&
		(myIndex - myLastPivotHighBar <= 10) &&
		(myLastPivotHighBar > myBearZoneStart) &&
		close[myIndex] < myEma200[myIndex]
	) {
		myBearZoneTop = open[myIndex];
		myBearZoneBot = close[myIndex];
		myBearZoneStart = myIndex;
	}

	myBullBoxTop[myIndex] = myBullZoneTop;
	myBullBoxBot[myIndex] = myBullZoneBot;
	myBearBoxTop[myIndex] = myBearZoneTop;
	myBearBoxBot[myIndex] = myBearZoneBot;

	// Touch logic
	let myBullTouch = false;
	let myBearTouch = false;

	if (
		myBullZoneTop !== null &&
		low[myIndex] <= myBullZoneTop &&
		high[myIndex] >= myBullZoneBot &&
		myIndex > myBullZoneStart &&
		(myIndex - myBullZoneStart <= myZoneMaxBars)
	) {
		myBullTouch = true;
		myBullZoneTop = null;
	}

	if (
		myBearZoneTop !== null &&
		high[myIndex] >= myBearZoneBot &&
		low[myIndex] <= myBearZoneTop &&
		myIndex > myBearZoneStart &&
		(myIndex - myBearZoneStart <= myZoneMaxBars)
	) {
		myBearTouch = true;
		myBearZoneTop = null;
	}

	myBullTouchSignal[myIndex] = myBullTouch;
	myBearTouchSignal[myIndex] = myBearTouch;

	// Entries
	if (myBullTouch && close[myIndex] > myEma200[myIndex] && !myIsShort) {
		if (myNumTrades === 0) {
			myLongEntry1[myIndex] = true;
			myIsLong = true;
			myNumTrades = 1;
			myWeightedPriceSum = close[myIndex] * myPctByTrade[0];
			myWeightSum = myPctByTrade[0];
			myAvgPrice = myWeightedPriceSum / myWeightSum;
		}
		else if (myIsLong && myNumTrades < 5 && close[myIndex] < myAvgPrice) {
			const myWeight = myPctByTrade[myNumTrades];
			myWeightedPriceSum += close[myIndex] * myWeight;
			myWeightSum += myWeight;
			myAvgPrice = myWeightedPriceSum / myWeightSum;

			if (myNumTrades === 1) myLongEntry2[myIndex] = true;
			else if (myNumTrades === 2) myLongEntry3[myIndex] = true;
			else if (myNumTrades === 3) myLongEntry4[myIndex] = true;
			else if (myNumTrades === 4) myLongEntry5[myIndex] = true;

			myNumTrades += 1;
		}
	}

	if (myBearTouch && close[myIndex] < myEma200[myIndex] && !myIsLong) {
		if (myNumTrades === 0) {
			myShortEntry1[myIndex] = true;
			myIsShort = true;
			myNumTrades = 1;
			myWeightedPriceSum = close[myIndex] * myPctByTrade[0];
			myWeightSum = myPctByTrade[0];
			myAvgPrice = myWeightedPriceSum / myWeightSum;
		}
		else if (myIsShort && myNumTrades < 5 && close[myIndex] > myAvgPrice) {
			const myWeight = myPctByTrade[myNumTrades];
			myWeightedPriceSum += close[myIndex] * myWeight;
			myWeightSum += myWeight;
			myAvgPrice = myWeightedPriceSum / myWeightSum;

			if (myNumTrades === 1) myShortEntry2[myIndex] = true;
			else if (myNumTrades === 2) myShortEntry3[myIndex] = true;
			else if (myNumTrades === 3) myShortEntry4[myIndex] = true;
			else if (myNumTrades === 4) myShortEntry5[myIndex] = true;

			myNumTrades += 1;
		}
	}

	// Take profit check and position reset
	if (myIsLong && myAvgPrice !== null) {
		const myLongTp = myAvgPrice * 1.02;
		myTpLine[myIndex] = myLongTp;
		if (high[myIndex] >= myLongTp) {
			myLongTpSignal[myIndex] = true;
			myIsLong = false;
			myNumTrades = 0;
			myAvgPrice = null;
			myWeightedPriceSum = 0;
			myWeightSum = 0;
		}
	}
	else if (myIsShort && myAvgPrice !== null) {
		const myShortTp = myAvgPrice * 0.98;
		myTpLine[myIndex] = myShortTp;
		if (low[myIndex] <= myShortTp) {
			myShortTpSignal[myIndex] = true;
			myIsShort = false;
			myNumTrades = 0;
			myAvgPrice = null;
			myWeightedPriceSum = 0;
			myWeightSum = 0;
		}
	}
	else {
		myTpLine[myIndex] = null;
	}
}

// --- Paint ---
paint(myEma200, { name: 'EMA200', color: myEmaColor, thickness: 2 });

fill(
	paint(myBullBoxTop, { name: 'BullZoneTop', color: myBuyColor, style: 'ladder' }),
	paint(myBullBoxBot, { name: 'BullZoneBottom', color: myBuyColor, style: 'ladder' }),
	myBuyColor,
	0.15
);

fill(
	paint(myBearBoxTop, { name: 'BearZoneTop', color: mySellColor, style: 'ladder' }),
	paint(myBearBoxBot, { name: 'BearZoneBottom', color: mySellColor, style: 'ladder' }),
	mySellColor,
	0.15
);

paint(myTpLine, { name: 'TakeProfitLine', color: 'blue', style: 'dotted', thickness: 2 });

const myBuyMarks = for_every(myLongEntry1, myLongEntry2, myLongEntry3, myLongEntry4, myLongEntry5, low,
	(_e1, _e2, _e3, _e4, _e5, _low) => (_e1 || _e2 || _e3 || _e4 || _e5) ? _low : null);

const mySellMarks = for_every(myShortEntry1, myShortEntry2, myShortEntry3, myShortEntry4, myShortEntry5, high,
	(_e1, _e2, _e3, _e4, _e5, _high) => (_e1 || _e2 || _e3 || _e4 || _e5) ? _high : null);

paint(myBuyMarks, { name: 'BuyEntries', style: 'labels_below', color: myBuyColor });
paint(mySellMarks, { name: 'SellEntries', style: 'labels_above', color: mySellColor });

// --- Signals (for scanners/alerts/strategy tester) ---
register_signal(myBullTouchSignal, 'Bull Zone Touch');
register_signal(myBearTouchSignal, 'Bear Zone Touch');

register_signal(myLongEntry1, 'Long Entry 1');
register_signal(myLongEntry2, 'Long Entry 2');
register_signal(myLongEntry3, 'Long Entry 3');
register_signal(myLongEntry4, 'Long Entry 4');
register_signal(myLongEntry5, 'Long Entry 5');

register_signal(myShortEntry1, 'Short Entry 1');
register_signal(myShortEntry2, 'Short Entry 2');
register_signal(myShortEntry3, 'Short Entry 3');
register_signal(myShortEntry4, 'Short Entry 4');
register_signal(myShortEntry5, 'Short Entry 5');

register_signal(myLongTpSignal, 'Long Take Profit');
register_signal(myShortTpSignal, 'Short Take Profit');