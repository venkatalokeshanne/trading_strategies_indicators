describe_indicator('Swing Trend Strategy PRO (Sideways Filtered)', 'price');

// ──────────────────────────────────────────
// INPUTS
// ──────────────────────────────────────────
const myTab = input.tab('Settings');

const myStopLossPercent = myTab.number('Stop Loss %', 8.0, { min: 1, max: 50 });
const myRsiLength = myTab.number('RSI Length', 14, { min: 1, max: 100 });

const myEmaRow = myTab.row();
const myEmaFastLength = myEmaRow.number('Fast EMA', 20, { min: 1, max: 500 });
const myEmaMidLength = myEmaRow.number('Mid EMA', 50, { min: 1, max: 500 });
const myEmaLongLength = myEmaRow.number('Long EMA', 200, { min: 1, max: 500 });

const myAdxRow = myTab.row();
const myAdxLength = myAdxRow.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThreshold = myAdxRow.number('ADX Minimum Trend Strength', 20, { min: 1, max: 100 });

// ──────────────────────────────────────────
// INDICATORS
// ──────────────────────────────────────────
const myEmaFast = ema(close, myEmaFastLength);
const myEmaMid = ema(close, myEmaMidLength);
const myEmaLong = ema(close, myEmaLongLength);
const myRsiVal = rsi(close, myRsiLength);
const myAdxObject = indicators.adx(myAdxLength);
const myAdxVal = myAdxObject.adx;

// ──────────────────────────────────────────
// TREND CONDITIONS
// ──────────────────────────────────────────
const myTrendUp = for_every(close, myEmaMid, myEmaLong, (_c, _emaMid, _emaLong) => _c > _emaLong && _emaMid > _emaLong);
const myStrongTrend = for_every(myAdxVal, _adx => _adx > myAdxThreshold);

// crossover of RSI above 55 (strict: current > 55, previous <= 55)
const myRsiCrossOver55 = for_every(myRsiVal, (_rsi, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevRsi = myRsiVal[_index - 1];
	return _rsi > 55 && myPrevRsi <= 55;
});

// ──────────────────────────────────────────
// ENTRY CONDITION
// ──────────────────────────────────────────
const myEntryCondition = for_every(myTrendUp, myStrongTrend, close, myEmaFast, myRsiCrossOver55,
	(_trendUp, _strongTrend, _c, _emaFast, _crossOver) => _trendUp && _strongTrend && _c > _emaFast && _crossOver
);

// ──────────────────────────────────────────
// POSITION SIMULATION (stateful loop, required to replicate
// strategy.entry / strategy.exit / strategy.close behavior)
// ──────────────────────────────────────────
const myPositionSize = series_of(0);
const myEntryPrice = series_of(null);
const myLongOpened = series_of(false);
const myLongClosed = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevSize = myIndex > 0 ? myPositionSize[myIndex - 1] : 0;
	const myPrevEntryPrice = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;

	let mySize = myPrevSize;
	let myEntry = myPrevEntryPrice;
	let myOpened = false;
	let myClosed = false;

	if (mySize === 0) {
		// flat: check for new entry (orders process on close, so entry
		// happens at this same candle's close, like process_orders_on_close)
		if (myEntryCondition[myIndex]) {
			mySize = 1;
			myEntry = close[myIndex];
			myOpened = true;
		}
	}
	else {
		// in position: check stop loss and trend exit
		const myStopPrice = myEntry * (1 - myStopLossPercent / 100);
		const myTrendExit = close[myIndex] < myEmaMid[myIndex];

		if (low[myIndex] <= myStopPrice) {
			mySize = 0;
			myEntry = null;
			myClosed = true;
		}
		else if (myTrendExit) {
			mySize = 0;
			myEntry = null;
			myClosed = true;
		}
	}

	myPositionSize[myIndex] = mySize;
	myEntryPrice[myIndex] = myEntry;
	myLongOpened[myIndex] = myOpened;
	myLongClosed[myIndex] = myClosed;
}

// ──────────────────────────────────────────
// PLOTS
// ──────────────────────────────────────────
paint(myEmaFast, { name: 'Fast EMA', color: '#FF9800', thickness: 2 });
paint(myEmaMid, { name: 'Mid EMA', color: '#2196F3', thickness: 2 });
paint(myEmaLong, { name: 'Long EMA', color: '#E53935', thickness: 2 });

const myBuyMarks = for_every(myLongOpened, _opened => _opened ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myLongClosed, _closed => _closed ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// ──────────────────────────────────────────
// SIGNALS FOR SCANNERS, ALERTS AND STRATEGY TESTER
// ──────────────────────────────────────────
register_signal(myEntryCondition, 'Entry Condition');
register_signal(myLongOpened, 'Long Opened');
register_signal(myLongClosed, 'Long Closed');
register_signal(myTrendUp, 'Trend Up');
register_signal(myStrongTrend, 'Strong Trend');