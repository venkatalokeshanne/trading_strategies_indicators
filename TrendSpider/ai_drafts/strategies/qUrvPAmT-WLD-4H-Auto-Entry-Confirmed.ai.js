describe_indicator('WLD 4H Auto Entry Confirmed', 'overlay');

// NOTE: TrendSpider Custom JS indicators cannot place real orders or run
// a backtesting engine like Pine's strategy.*. This script reproduces the
// UT Bot + EMA/MACD signal logic exactly, and simulates the "virtual"
// position/exit bookkeeping from the Pine script so that entry/exit bars
// match exactly. These are exposed as signals (for scanners/alerts) and
// as labels, instead of actual broker orders.

const myKeyValue = input.number('UT Bot Key Value', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myAtrPeriod = input.number('UT Bot ATR Period', 1, { min: 1, max: 50 });
const myEmaLength = input.number('EMA Length', 50, { min: 1, max: 500 });
const myMaxBarsHold = input.number('Max Bars to Hold', 4, { min: 1, max: 100 });

const myEma50 = ema(close, myEmaLength);
const myEma12 = ema(close, 12);
const myEma26 = ema(close, 26);
const myMacdLine = sub(myEma12, myEma26);
const mySignalLine = ema(myMacdLine, 9);
const myAtr = atr(high, low, close, myAtrPeriod);

const myCandleCount = close.length;

// UT Bot trailing stop & pos (stateful recursive calc, must be done in a loop)
// NOTE: "new Array()" is prohibited by the scripting engine, so we use
// series_of() instead, which creates a filled array of the chart length.
const myTrailingStop = series_of(null);
const myPos = series_of(0);
const myAbove = series_of(false);
const myBelow = series_of(false);
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const mySrc = close[myIndex];
	const myNLoss = myKeyValue * (myAtr[myIndex] || 0);

	if (myIndex === 0 || myTrailingStop[myIndex - 1] === null) {
		myTrailingStop[myIndex] = mySrc - myNLoss;
	}
	else {
		const myPrevStop = myTrailingStop[myIndex - 1];
		const myPrevSrc = close[myIndex - 1];

		if (mySrc > myPrevStop && myPrevSrc > myPrevStop) {
			myTrailingStop[myIndex] = Math.max(myPrevStop, mySrc - myNLoss);
		}
		else if (mySrc < myPrevStop && myPrevSrc < myPrevStop) {
			myTrailingStop[myIndex] = Math.min(myPrevStop, mySrc + myNLoss);
		}
		else if (mySrc > myPrevStop) {
			myTrailingStop[myIndex] = mySrc - myNLoss;
		}
		else {
			myTrailingStop[myIndex] = mySrc + myNLoss;
		}
	}

	if (myIndex === 0) {
		myPos[myIndex] = 0;
	}
	else {
		const myPrevStop = myTrailingStop[myIndex - 1];
		const myPrevSrc = close[myIndex - 1];

		if (myPrevSrc < myPrevStop && mySrc > myTrailingStop[myIndex]) {
			myPos[myIndex] = 1;
		}
		else if (myPrevSrc > myPrevStop && mySrc < myTrailingStop[myIndex]) {
			myPos[myIndex] = -1;
		}
		else {
			myPos[myIndex] = myPos[myIndex - 1];
		}
	}

	// ema1 = ema(close, 1) is just close itself; crossover of close vs trailing stop
	if (myIndex > 0) {
		const myPrevClose = close[myIndex - 1];
		const myPrevStop = myTrailingStop[myIndex - 1];
		myAbove[myIndex] = myPrevClose <= myPrevStop && mySrc > myTrailingStop[myIndex];
		myBelow[myIndex] = myPrevClose >= myPrevStop && mySrc < myTrailingStop[myIndex];
	}

	myBuySignal[myIndex] = mySrc > myTrailingStop[myIndex] && myAbove[myIndex];
	mySellSignal[myIndex] = mySrc < myTrailingStop[myIndex] && myBelow[myIndex];
}

// Signal tracking, confirmed entries, simulated open position and exits
const myEnterLong = series_of(false);
const myEnterShort = series_of(false);
const myExitTrade = series_of(false);

let mySignalBar = null;
let mySignalType = 'none';
let myInPosition = false;
let myEntryBarIndex = null;
let myPositionType = 'none';

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myMacdValue = myMacdLine[myIndex];
	const mySignalValue = mySignalLine[myIndex];
	const myEmaValue = myEma50[myIndex];

	// Detect new UT signal (only if no active tracked signal or hold window expired)
	if (mySignalBar === null || myIndex > mySignalBar + myMaxBarsHold) {
		if (myBuySignal[myIndex] && myMacdValue > mySignalValue && close[myIndex] > myEmaValue && low[myIndex] > myEmaValue) {
			mySignalBar = myIndex;
			mySignalType = 'long';
		}
		else if (mySellSignal[myIndex] && myMacdValue < mySignalValue && close[myIndex] < myEmaValue && high[myIndex] < myEmaValue) {
			mySignalBar = myIndex;
			mySignalType = 'short';
		}
	}

	// Confirm entry on the signal bar itself
	const myConfirmLong = mySignalType === 'long' && myIndex === mySignalBar && close[myIndex] > myEmaValue && myMacdValue > mySignalValue;
	const myConfirmShort = mySignalType === 'short' && myIndex === mySignalBar && close[myIndex] < myEmaValue && myMacdValue < mySignalValue;

	if (myConfirmLong && !myInPosition) {
		myEnterLong[myIndex] = true;
		myInPosition = true;
		myEntryBarIndex = myIndex;
		myPositionType = 'long';
	}

	if (myConfirmShort && !myInPosition) {
		myEnterShort[myIndex] = true;
		myInPosition = true;
		myEntryBarIndex = myIndex;
		myPositionType = 'short';
	}

	let myExitNow = false;

	if (myInPosition) {
		const myBarsSinceEntry = myIndex - myEntryBarIndex;

		if (myBarsSinceEntry >= myMaxBarsHold) {
			myExitNow = true;
		}

		let myOppositeConfirmed = false;

		if (mySignalType === 'long') {
			myOppositeConfirmed = mySellSignal[myIndex] && close[myIndex] < myEmaValue && myMacdValue < mySignalValue;
		}
		else if (mySignalType === 'short') {
			myOppositeConfirmed = myBuySignal[myIndex] && close[myIndex] > myEmaValue && myMacdValue > mySignalValue;
		}

		if (myOppositeConfirmed) {
			myExitNow = true;
		}
	}

	if (myExitNow) {
		myExitTrade[myIndex] = true;
		myInPosition = false;
		myEntryBarIndex = null;
		myPositionType = 'none';
		mySignalBar = null;
		mySignalType = 'none';
	}
}

// Build label series for UT Bot buy/sell shapes
const myBuyLabels = myBuySignal.map(_myFlag => _myFlag ? constants.icons.triangle_up : null);
const mySellLabels = mySellSignal.map(_myFlag => _myFlag ? constants.icons.triangle_down : null);

paint(myBuyLabels, { style: 'labels_below', color: 'green', name: 'UTBotBuy' });
paint(mySellLabels, { style: 'labels_above', color: 'red', name: 'UTBotSell' });

// Confirmed entry/exit markers
const myEnterLongLabels = myEnterLong.map(_myFlag => _myFlag ? constants.icons.arrow_up : null);
const myEnterShortLabels = myEnterShort.map(_myFlag => _myFlag ? constants.icons.arrow_down : null);
const myExitLabels = myExitTrade.map(_myFlag => _myFlag ? constants.icons.circle : null);

paint(myEnterLongLabels, { style: 'labels_below', color: 'lime', name: 'EnterLong' });
paint(myEnterShortLabels, { style: 'labels_above', color: 'orange', name: 'EnterShort' });
paint(myExitLabels, { style: 'labels_above', color: 'gray', name: 'ExitTrade' });

// EMA line for reference
paint(myEma50, { color: 'blue', name: 'EMA50' });

// Signals usable in scanners, alerts, strategy tester
register_signal(myEnterLong, 'Enter Long');
register_signal(myEnterShort, 'Enter Short');
register_signal(myExitTrade, 'Exit Trade');
register_signal(myBuySignal, 'UT Bot Buy');
register_signal(mySellSignal, 'UT Bot Sell');