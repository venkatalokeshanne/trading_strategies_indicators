// This indicator is a best-effort translation of a TradingView Pine Script
// strategy into a TrendSpider indicator. TrendSpider custom indicators
// cannot behave like Pine strategies (no equity, no actual order
// management, no "input.source" referencing an arbitrary external
// indicator). We reproduce the SIGNAL LOGIC (entries/exits/stops) using
// plain price series as proxies for the Buy/Sell and Cancel sources, and
// expose the resulting events as register_signal() outputs so they can be
// used in Scanners / Alerts / Strategy Tester.
describe_indicator('Simple Pyramid Strategy Signals', 'lower');

const myTab = input.tab('Indicators');
const myBuySellSource = myTab.select('Buy/Sell Source', 'close', constants.price_source_options);
const myCancelSource = myTab.select('Cancel Source', 'close', constants.price_source_options);
const myCancelType = myTab.select('Cancel Type', 'None', ['Not New', 'Close and Not New', 'None']);

const myStopTab = input.tab('Strategy Stop');
const myStopValue = myStopTab.number('Stop', 0, { min: 0, max: 10000000 });
const myStopType = myStopTab.select('Stop Type', 'Value', ['Value', 'Percent']);

const myBuySell = market[myBuySellSource];
const myCancel = market[myCancelSource];

const myCandleCount = close.length;

// Position state tracking: 1 = long, -1 = short, 0 = flat
const myPositionSize = series_of(0);
const myEntryPrice = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myPositionClosedSignal = series_of(false);

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	let myPrevPosition = myIndex > 0 ? myPositionSize[myIndex - 1] : 0;
	let myPrevEntryPrice = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;

	let myCurrentPosition = myPrevPosition;
	let myCurrentEntryPrice = myPrevEntryPrice;
	let myClosedThisBar = false;

	// "Close and Not New" cancel handling
	if (myCancelType === 'Close and Not New') {
		if (myCurrentPosition > 0 && myCancel[myIndex] < 0) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myClosedThisBar = true;
		}
		else if (myCurrentPosition < 0 && myCancel[myIndex] > 0) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myClosedThisBar = true;
		}
	}

	// Stop handling (based on open profit vs current price)
	let myStopSize = myStopValue;
	if (myStopType === 'Percent') {
		myStopSize = (myStopValue / 100) * high[myIndex];
	}
	myStopSize *= -1;

	if (myStopSize !== 0 && myCurrentPosition !== 0 && myCurrentEntryPrice !== null) {
		const myOpenProfit = myCurrentPosition > 0
			? (close[myIndex] - myCurrentEntryPrice)
			: (myCurrentEntryPrice - close[myIndex]);

		if (myOpenProfit < myStopSize) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myClosedThisBar = true;
		}
	}

	let myLongEntry = false;
	let myShortEntry = false;

	if (myBuySell[myIndex] > 0) {
		if (myCancelType === 'None' || myCancel[myIndex] >= 0) {
			myCurrentPosition = 1;
			myCurrentEntryPrice = close[myIndex];
			myLongEntry = true;
		}
		else if (myCurrentPosition < 0) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myClosedThisBar = true;
		}
	}
	else if (myBuySell[myIndex] < 0) {
		if (myCancelType === 'None' || myCancel[myIndex] <= 0) {
			myCurrentPosition = -1;
			myCurrentEntryPrice = close[myIndex];
			myShortEntry = true;
		}
		else if (myCurrentPosition > 0) {
			myCurrentPosition = 0;
			myCurrentEntryPrice = null;
			myClosedThisBar = true;
		}
	}

	myPositionSize[myIndex] = myCurrentPosition;
	myEntryPrice[myIndex] = myCurrentEntryPrice;
	myLongEntrySignal[myIndex] = myLongEntry;
	myShortEntrySignal[myIndex] = myShortEntry;
	myPositionClosedSignal[myIndex] = myClosedThisBar;
}

const myPositionLine = for_every(close, (_c, _prev, _i) => myPositionSize[_i]);

paint(myPositionLine, { name: 'Position Size', color: '#4DA3FF', style: 'line' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myPositionClosedSignal, 'Position Closed');