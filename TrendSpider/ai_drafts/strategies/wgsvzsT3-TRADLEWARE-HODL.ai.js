describe_indicator('TRADLEWARE HODL', 'lower');

// NOTE: TrendSpider Custom JS API does not have a strategy/backtest
// engine (strategy.entry, strategy.close_all, strategy.equity do
// not exist here). This indicator reproduces the HODL logic as a
// signal-based approximation: it finds the entry bar (first bar at
// or after Start Date), finds the exit bar (first bar at or after
// End Date, or the second-to-last bar on the chart) and plots a
// simulated equity curve, assuming a single 99.95% equity buy with
// 0.1% commission and a fixed slippage approximation.

const myDateTab = input.tab('Date Range');
const myStartRow = myDateTab.row();
const myStartYear = myStartRow.number('Start year', 2018, { min: 2000, max: 2099 });
const myStartMonth = myStartRow.number('Start month', 1, { min: 1, max: 12 });
const myStartDay = myStartRow.number('Start day', 1, { min: 1, max: 31 });

const myEndRow = myDateTab.row();
const myEndYear = myEndRow.number('End year', 2099, { min: 2000, max: 2099 });
const myEndMonth = myEndRow.number('End month', 12, { min: 1, max: 12 });
const myEndDay = myEndRow.number('End day', 31, { min: 1, max: 31 });

const myParamsTab = input.tab('Trade Parameters');
// Shortened input title to satisfy the platform's input name length limit
const myQtyPercent = myParamsTab.number('Position size percent', 99.95, { min: 1, max: 100 });
const myCommissionPercent = myParamsTab.number('Commission percent', 0.1, { min: 0, max: 10 });
const mySlippagePercent = myParamsTab.number('Approx slippage percent', 0.03, { min: 0, max: 5 });

const myInitialCapital = 10000;

// Build start/end Unix timestamps (UTC-based, seconds)
const myStartDate = Date.UTC(myStartYear, myStartMonth - 1, myStartDay, 0, 0) / 1000;
const myEndDate = Date.UTC(myEndYear, myEndMonth - 1, myEndDay, 23, 59) / 1000;

const myBarCount = close.length;
assert(myBarCount > 0, 'No candle data available');

// Find entry index: first bar where time >= startDate
let myEntryIndex = -1;
for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	if (time[myIndex] >= myStartDate) {
		myEntryIndex = myIndex;
		break;
	}
}

// Find exit index: first bar where time >= endDate, or second-to-last bar
let myExitIndex = myBarCount - 2 >= 0 ? myBarCount - 2 : myBarCount - 1;
for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	if (time[myIndex] >= myEndDate) {
		myExitIndex = Math.min(myExitIndex, myIndex);
		break;
	}
}

if (myEntryIndex === -1 || myEntryIndex > myExitIndex) {
	myEntryIndex = -1;
}

// Entry/exit signals, constant number of outputs regardless of data
const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);

if (myEntryIndex !== -1) {
	myEntrySignal[myEntryIndex] = true;
}
myExitSignal[myExitIndex] = true;

register_signal(myEntrySignal, 'HODL Entry');
register_signal(myExitSignal, 'HODL Exit');

// Simulated equity curve
const myEquitySeries = series_of(myInitialCapital);
let myPositionUnits = 0;
let myCashRemaining = myInitialCapital;

for (let myIndex = 0; myIndex < myBarCount; myIndex += 1) {
	if (myIndex === myEntryIndex && myEntryIndex !== -1) {
		// Apply slippage to the fill price, then commission on the notional
		const myFillPrice = close[myIndex] * (1 + mySlippagePercent / 100);
		const myEquityBeforeTrade = myCashRemaining;
		const myNotional = myEquityBeforeTrade * (myQtyPercent / 100);
		const myCommissionCost = myNotional * (myCommissionPercent / 100);
		myPositionUnits = (myNotional - myCommissionCost) / myFillPrice;
		myCashRemaining = myEquityBeforeTrade - myNotional;
	}

	if (myPositionUnits > 0) {
		myEquitySeries[myIndex] = myCashRemaining + myPositionUnits * close[myIndex];
	}
	else {
		myEquitySeries[myIndex] = myCashRemaining;
	}

	if (myIndex === myExitIndex && myPositionUnits > 0) {
		const myExitFillPrice = close[myIndex] * (1 - mySlippagePercent / 100);
		const myExitNotional = myPositionUnits * myExitFillPrice;
		const myExitCommission = myExitNotional * (myCommissionPercent / 100);
		myCashRemaining = myCashRemaining + myExitNotional - myExitCommission;
		myPositionUnits = 0;
		myEquitySeries[myIndex] = myCashRemaining;
	}
}

paint(myEquitySeries, { name: 'Equity', color: 'teal', thickness: 2, style: 'line' });