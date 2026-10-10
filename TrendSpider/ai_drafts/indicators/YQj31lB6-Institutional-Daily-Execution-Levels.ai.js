describe_indicator('Institutional Daily Execution Levels', 'price');

// --- Inputs ---
const myAtrLen = input.number('ATR Length for Stop Cushion', 14, { min: 1, max: 100 });
const myRiskReward = input.number('Risk to Reward Ratio Target', 2.0, { min: 0.1, max: 10, step: 0.1 });
const myShowOnlyToday = input.boolean('Show Only Today Levels', true);

// --- Fetch Daily Data ---
// Using request.history to get Daily OHLC, equivalent to Pine's request.security(..., "D", ...)
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

// ATR computed on Daily series
const myDailyAtr = atr(myDailyData.high, myDailyData.low, myDailyData.close, myAtrLen);

// Shift by 1 to get "previous day" values, matching Pine's [1] offset
const myPrevHigh = shift(myDailyData.high, 1);
const myPrevLow = shift(myDailyData.low, 1);
const myPrevClose = shift(myDailyData.close, 1);
const myPrevAtr = shift(myDailyAtr, 1);

// --- Central Pivot & Ranges ---
const myPivotPoint = div(add(add(myPrevHigh, myPrevLow), myPrevClose), 3.0);
const myDayRange = sub(myPrevHigh, myPrevLow);

// --- Buy Levels ---
const myBuyEntry = sub(myPivotPoint, mult(myDayRange, 0.382));
const myBuyStop = sub(myPrevLow, mult(myPrevAtr, 0.25));
const myBuyRisk = sub(myBuyEntry, myBuyStop);
const myBuyTarget = add(myBuyEntry, mult(myBuyRisk, myRiskReward));

// --- Sell Levels ---
const mySellEntry = add(myPivotPoint, mult(myDayRange, 0.382));
const mySellStop = add(myPrevHigh, mult(myPrevAtr, 0.25));
const mySellRisk = sub(mySellStop, mySellEntry);
const mySellTarget = sub(mySellEntry, mult(mySellRisk, myRiskReward));

// --- Land daily levels onto current chart timeframe ---
// 'le' matches each candle to the daily bar whose timestamp is <= candle time,
// which reproduces Pine's lookahead_on security behavior (today uses yesterday's data)
const myBuyEntryLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myBuyEntry, time, 'le'),
	'constant'
);
const myBuyStopLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myBuyStop, time, 'le'),
	'constant'
);
const myBuyTargetLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myBuyTarget, time, 'le'),
	'constant'
);
const mySellEntryLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, mySellEntry, time, 'le'),
	'constant'
);
const mySellStopLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, mySellStop, time, 'le'),
	'constant'
);
const mySellTargetLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, mySellTarget, time, 'le'),
	'constant'
);

// --- Optionally restrict display to the current trading day only ---
// Pine draws fresh lines only for "today"; here we mask out all prior days
// if the user wants that behavior (default on).
const myLastDaySession = time.length > 0 ? bar_at(time[time.length - 1]).session : null;
const mySessionAtCandle = time.map(myTime => bar_at(myTime).session);

function myMaskIfNeeded(mySeries) {
	if (!myShowOnlyToday) {
		return mySeries;
	}
	return for_every(mySeries, (myValue, myPrev, myIndex) => mySessionAtCandle[myIndex] == myLastDaySession ? myValue : null);
}

// --- Paint lines ---
paint(myMaskIfNeeded(myBuyEntryLanded), { name: 'Buy Entry', color: '#2962FF', thickness: 2, style: 'ladder' });
paint(myMaskIfNeeded(myBuyStopLanded), { name: 'Buy Stop Loss', color: '#EF5350', thickness: 1, style: 'dotted' });
paint(myMaskIfNeeded(myBuyTargetLanded), { name: 'Buy Target', color: '#26A69A', thickness: 1, style: 'dotted' });

paint(myMaskIfNeeded(mySellEntryLanded), { name: 'Sell Entry', color: '#FF9800', thickness: 2, style: 'ladder' });
paint(myMaskIfNeeded(mySellStopLanded), { name: 'Sell Stop Loss', color: '#EF5350', thickness: 1, style: 'dotted' });
paint(myMaskIfNeeded(mySellTargetLanded), { name: 'Sell Target', color: '#26A69A', thickness: 1, style: 'dotted' });

// --- Register signals for scanners, alerts and strategy use ---
const myBuyEntrySignal = for_every(close, myBuyEntryLanded, (myClose, myLevel) => myLevel != null && myClose >= myLevel);
const myBuyStopSignal = for_every(close, myBuyStopLanded, (myClose, myLevel) => myLevel != null && myClose <= myLevel);
const myBuyTargetSignal = for_every(close, myBuyTargetLanded, (myClose, myLevel) => myLevel != null && myClose >= myLevel);

const mySellEntrySignal = for_every(close, mySellEntryLanded, (myClose, myLevel) => myLevel != null && myClose <= myLevel);
const mySellStopSignal = for_every(close, mySellStopLanded, (myClose, myLevel) => myLevel != null && myClose >= myLevel);
const mySellTargetSignal = for_every(close, mySellTargetLanded, (myClose, myLevel) => myLevel != null && myClose <= myLevel);

register_signal(myBuyEntrySignal, 'Price Crossed Buy Entry');
register_signal(myBuyStopSignal, 'Price Hit Buy Stop Loss');
register_signal(myBuyTargetSignal, 'Price Hit Buy Target');
register_signal(mySellEntrySignal, 'Price Crossed Sell Entry');
register_signal(mySellStopSignal, 'Price Hit Sell Stop Loss');
register_signal(mySellTargetSignal, 'Price Hit Sell Target');