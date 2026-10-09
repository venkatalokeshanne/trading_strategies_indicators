describe_indicator('DCA Grid Strategy Simulator', 'price');

// This re-implements the Pine Script DCA grid strategy logic using a
// manual simulation loop (orderCount / lastEntryPrice / avgPrice / totalQty
// are all tracked bar by bar, exactly like Pine's `var` variables).
// Since this is an indicator (not a native backtester), the strategy
// mechanics (entries, averaging, TP exit) are simulated here and exposed
// as signals + plotted lines, so they can be used in scanners/alerts.

const myBaseOrder = input.number('Base Order Size ($)', 100, { min: 0.01, max: 1000000 });
const myGridStep = input.number('Grid Step (%)', 1.1, { min: 0.01, max: 100 });
const myTakeProfit = input.number('Take Profit (%)', 1.8, { min: 0.01, max: 100 });
const myMultiplier = input.number('Size Multiplier', 1.2, { min: 0.01, max: 10 });
const myMaxOrders = input.number('Max Orders', 15, { min: 1, max: 100 });

const myCandleCount = close.length;

const myAvgPriceSeries = series_of(null);
const myTpPriceSeries = series_of(null);
const myBuySignalSeries = series_of(false);
const mySellSignalSeries = series_of(false);

let myOrderCount = 0;
let myLastEntryPrice = null;
let myTotalQty = 0;
let myTotalCost = 0;
let myPositionSize = 0;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	const myClose = close[myIndex];
	const myLow = low[myIndex];
	const myHigh = high[myIndex];
	let myDidBuyThisBar = false;

	// Start first position when flat
	if (myPositionSize === 0) {
		const myQty = myBaseOrder / myClose;
		myTotalQty = myQty;
		myTotalCost = myBaseOrder;
		myOrderCount = 1;
		myLastEntryPrice = myClose;
		myPositionSize = myTotalQty;
		myDidBuyThisBar = true;
	}
	// Additional DCA orders
	else if (myPositionSize > 0 && myOrderCount < myMaxOrders) {
		const myNextBuyPrice = myLastEntryPrice * (1 - myGridStep / 100);

		if (myLow <= myNextBuyPrice) {
			const myOrderQtyCash = myBaseOrder * Math.pow(myMultiplier, myOrderCount);
			const myQty = myOrderQtyCash / myClose;

			myTotalQty += myQty;
			myTotalCost += myOrderQtyCash;
			myLastEntryPrice = myNextBuyPrice;
			myOrderCount += 1;
			myPositionSize = myTotalQty;
			myDidBuyThisBar = true;
		}
	}

	let myAvgPrice = null;
	let myTpPrice = null;
	let myDidSellThisBar = false;

	if (myPositionSize > 0) {
		myAvgPrice = myTotalCost / myTotalQty;
		myTpPrice = myAvgPrice * (1 + myTakeProfit / 100);

		// Take profit limit exit check (same bar as Pine's strategy.exit)
		if (myHigh >= myTpPrice) {
			myDidSellThisBar = true;
			myPositionSize = 0;
			myOrderCount = 0;
			myLastEntryPrice = null;
			myTotalQty = 0;
			myTotalCost = 0;
		}
	}

	myAvgPriceSeries[myIndex] = myAvgPrice;
	myTpPriceSeries[myIndex] = myTpPrice;
	myBuySignalSeries[myIndex] = myDidBuyThisBar;
	mySellSignalSeries[myIndex] = myDidSellThisBar;
}

paint(myAvgPriceSeries, { name: 'AveragePrice', color: '#FFC107', thickness: 2, style: 'line', forceUsePriceAxis: true });
paint(myTpPriceSeries, { name: 'TakeProfit', color: '#26A69A', thickness: 2, style: 'line', forceUsePriceAxis: true });

register_signal(myBuySignalSeries, 'DCA Entry');
register_signal(mySellSignalSeries, 'DCA Take Profit Exit');