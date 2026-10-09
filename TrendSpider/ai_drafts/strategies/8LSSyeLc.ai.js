describe_indicator('Europon Reversal FX Rush Ver2', 'lower');

// NOTE: This is a best-effort translation of a path-dependent Pine Script
// strategy into a stateless indicator engine. Several approximations were
// required (see flagged notes). This reproduces entry/exit SIGNALS, not an
// actual broker-accurate backtest.

const myTab1 = input.tab('RSI / Nanpin');
const myRsiPeriod = myTab1.number('RSI Period', 3, { min: 1, max: 100 });
const myRsiShift = myTab1.number('RSI Signal Shift', 2, { min: 0, max: 20 });
const myRsiRow = myTab1.row();
const myRsiHigh = myRsiRow.number('RSI High Level', 60, { min: 50, max: 100 });
const myRsiLow = myRsiRow.number('RSI Low Level', 40, { min: 0, max: 50 });
const myNanpin = myTab1.boolean('Enable Nanpin', true);
const myShortNanpin = myTab1.boolean('Enable Short Nanpin', true);
const myMaxPositions = myTab1.number('Max Positions', 3, { min: 1, max: 3 });

const myTab2 = input.tab('Trade Hours');
const myUseTradeHourFilter = myTab2.boolean('Use Trade Hour Filter', true);
const myHourRow = myTab2.row();
const myStartHour = myHourRow.number('Start Hour', 1, { min: 0, max: 23 });
const myEndHour = myHourRow.number('End Hour', 9, { min: 0, max: 23 });

const myTab3 = input.tab('Risk');
const myPriceUnit = myTab3.number('Price Unit', 0.01, { min: 0.00001, max: 100 });
const myRiskRow = myTab3.row();
const myStopLossRequest = myRiskRow.number('Stop Loss Request', 4, { min: 0.1, max: 100 });
const myTakeProfitRequest = myRiskRow.number('Take Profit Request', 4, { min: 0.1, max: 100 });

const myTab4 = input.tab('Display');
const myShowBackground = myTab4.boolean('Show Background', true);
const myShowSignals = myTab4.boolean('Show Additional Signals', false);

const myLength = close.length;

// RSI computed on close, then shifted (Pine's rsiRaw[rsiShift])
const myRsiRaw = rsi(close, myRsiPeriod);
const myRsiValue = shift(myRsiRaw, myRsiShift);

// Approximation: server time zone from Pine input is not selectable in the
// Custom JS API. We use the exchange time zone of the current symbol
// instead of the user-selected MT4/MT5 server time zone.
const myServerHour = time.map(_t => time_of(_t).hours);

const myIsH1 = current.resolution === '60';

const myIsTradeHour = myServerHour.map(_h => {
	if (!myUseTradeHourFilter) return true;
	if (myStartHour <= myEndHour) {
		return _h >= myStartHour && _h <= myEndHour;
	}
	else {
		return _h >= myStartHour || _h <= myEndHour;
	}
});

const myTradeAllowed = myIsTradeHour.map(_ok => myIsH1 && _ok);

const myLongNanpinLevel2 = myRsiLow - myRsiLow / 4.0;
const myLongNanpinLevel3 = myRsiLow - myRsiLow / 2.0;
const myShortNanpinLevel2 = myRsiHigh + (100.0 - myRsiHigh) / 4.0;
const myShortNanpinLevel3 = myRsiHigh + (100.0 - myRsiHigh) / 2.0;

const myPrevOpen = shift(open, 1);
const myPrevClose = shift(close, 1);

// Pre-compute condition arrays (no indicator calls inside loops)
const myBuySignalArr = series_of(false);
const mySellSignalArr = series_of(false);
const myLongNanpin2Arr = series_of(false);
const myLongNanpin3Arr = series_of(false);
const myShortNanpin2Arr = series_of(false);
const myShortNanpin3Arr = series_of(false);

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myRsiVal = myRsiValue[myIndex];
	const myAllowed = myTradeAllowed[myIndex];
	const myPreviousBull = myPrevOpen[myIndex] !== null && myPrevClose[myIndex] !== null && myPrevOpen[myIndex] < myPrevClose[myIndex];
	const myPreviousBear = myPrevOpen[myIndex] !== null && myPrevClose[myIndex] !== null && myPrevOpen[myIndex] > myPrevClose[myIndex];

	myBuySignalArr[myIndex] = myAllowed && myRsiVal !== null && myRsiVal < myRsiLow;
	mySellSignalArr[myIndex] = myAllowed && myRsiVal !== null && myRsiVal > myRsiHigh;
	myLongNanpin2Arr[myIndex] = myAllowed && myNanpin && myPreviousBull && myRsiVal !== null && myRsiVal < myLongNanpinLevel2;
	myLongNanpin3Arr[myIndex] = myAllowed && myNanpin && myPreviousBull && myRsiVal !== null && myRsiVal < myLongNanpinLevel3;
	myShortNanpin2Arr[myIndex] = myAllowed && myNanpin && myShortNanpin && myPreviousBear && myRsiVal !== null && myRsiVal > myShortNanpinLevel2;
	myShortNanpin3Arr[myIndex] = myAllowed && myNanpin && myShortNanpin && myPreviousBear && myRsiVal !== null && myRsiVal > myShortNanpinLevel3;
}

// Stateful simulation of the strategy's position machine.
// Approximation: average entry price assumes equal size per nanpin add
// (Pine's strategy.position_avg_price depends on actual order sizing,
// which this engine does not track per-contract).
const myLongEntryArr = series_of(false);
const myShortEntryArr = series_of(false);
const myLongExitArr = series_of(false);
const myShortExitArr = series_of(false);
const myPositionCountArr = series_of(0);

let myPosSize = 0; // 0 flat, 1 long, -1 short
let myPosCount = 0;
let myAvgPrice = 0;

const myStopDistance = myPriceUnit * myStopLossRequest;
const myTakeDistance = myPriceUnit * myTakeProfitRequest;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	let myEntryLong = false;
	let myEntryShort = false;
	let myExitLong = false;
	let myExitShort = false;

	let myFlat = myPosSize === 0;
	let myInLong = myPosSize > 0;
	let myInShort = myPosSize < 0;

	if (myBuySignalArr[myIndex] && myInShort) {
		myExitShort = true;
		myPosSize = 1;
		myPosCount = 1;
		myAvgPrice = close[myIndex];
		myEntryLong = true;
	}
	else if (myBuySignalArr[myIndex] && myFlat) {
		myPosSize = 1;
		myPosCount = 1;
		myAvgPrice = close[myIndex];
		myEntryLong = true;
	}

	myInLong = myPosSize > 0;
	myFlat = myPosSize === 0;

	if (mySellSignalArr[myIndex] && myInLong) {
		myExitLong = true;
		myPosSize = -1;
		myPosCount = 1;
		myAvgPrice = close[myIndex];
		myEntryShort = true;
	}
	else if (mySellSignalArr[myIndex] && myFlat) {
		myPosSize = -1;
		myPosCount = 1;
		myAvgPrice = close[myIndex];
		myEntryShort = true;
	}

	myInLong = myPosSize > 0;
	myInShort = myPosSize < 0;

	if (myInLong && myPosCount < myMaxPositions) {
		if (myPosCount === 1 && myLongNanpin2Arr[myIndex]) {
			myAvgPrice = (myAvgPrice * myPosCount + close[myIndex]) / (myPosCount + 1);
			myPosCount += 1;
			myEntryLong = true;
		}
		else if (myPosCount === 2 && myLongNanpin3Arr[myIndex]) {
			myAvgPrice = (myAvgPrice * myPosCount + close[myIndex]) / (myPosCount + 1);
			myPosCount += 1;
			myEntryLong = true;
		}
	}

	if (myInShort && myShortNanpin && myPosCount < myMaxPositions) {
		if (myPosCount === 1 && myShortNanpin2Arr[myIndex]) {
			myAvgPrice = (myAvgPrice * myPosCount + close[myIndex]) / (myPosCount + 1);
			myPosCount += 1;
			myEntryShort = true;
		}
		else if (myPosCount === 2 && myShortNanpin3Arr[myIndex]) {
			myAvgPrice = (myAvgPrice * myPosCount + close[myIndex]) / (myPosCount + 1);
			myPosCount += 1;
			myEntryShort = true;
		}
	}

	// Exit check (stop/limit touched intrabar, approximated with H/L of bar)
	myInLong = myPosSize > 0;
	myInShort = myPosSize < 0;

	if (myInLong) {
		const myStopPrice = myAvgPrice - myStopDistance;
		const myLimitPrice = myAvgPrice + myTakeDistance;
		if (low[myIndex] <= myStopPrice || high[myIndex] >= myLimitPrice) {
			myExitLong = true;
			myPosSize = 0;
			myPosCount = 0;
			myAvgPrice = 0;
		}
	}
	if (myInShort) {
		const myStopPrice = myAvgPrice + myStopDistance;
		const myLimitPrice = myAvgPrice - myTakeDistance;
		if (high[myIndex] >= myStopPrice || low[myIndex] <= myLimitPrice) {
			myExitShort = true;
			myPosSize = 0;
			myPosCount = 0;
			myAvgPrice = 0;
		}
	}

	myLongEntryArr[myIndex] = myEntryLong;
	myShortEntryArr[myIndex] = myEntryShort;
	myLongExitArr[myIndex] = myExitLong;
	myShortExitArr[myIndex] = myExitShort;
	myPositionCountArr[myIndex] = myPosCount;
}

// Background approximation: Custom JS API has no chart-background paint
// function, so we color candles instead (buy = teal tint, sell = red tint).
const myBackgroundColors = for_every(myBuySignalArr, mySellSignalArr, (_buy, _sell) => {
	if (!myShowBackground) return null;
	if (_buy) return 'rgba(0,120,255,0.18)';
	if (_sell) return 'rgba(255,70,90,0.18)';
	return null;
});
color_candles(myBackgroundColors);

// Optional signal markers
const myBuyMarkerSeries = for_every(myBuySignalArr, _buy => (myShowSignals && _buy) ? constants.icons.triangle_up : null);
const mySellMarkerSeries = for_every(mySellSignalArr, _sell => (myShowSignals && _sell) ? constants.icons.triangle_down : null);

paint(myBuyMarkerSeries, { style: 'labels_below', color: '#00FFAA', name: 'BuySignal' });
paint(mySellMarkerSeries, { style: 'labels_above', color: '#FF5A78', name: 'SellSignal' });

// Data window values
paint(myRsiValue, { style: 'line', color: '#4DA3FF', name: 'RSISignalValue' });
paint(myPositionCountArr, { style: 'line', color: 'gray', name: 'OpenPositionCount', forceUsePriceAxis: false });

// Scanner / Alert / Strategy signals
register_signal(myLongEntryArr, 'Long Entry');
register_signal(myShortEntryArr, 'Short Entry');
register_signal(myLongExitArr, 'Long Exit');
register_signal(myShortExitArr, 'Short Exit');
register_signal(myBuySignalArr, 'Buy Signal Raw');
register_signal(mySellSignalArr, 'Sell Signal Raw');