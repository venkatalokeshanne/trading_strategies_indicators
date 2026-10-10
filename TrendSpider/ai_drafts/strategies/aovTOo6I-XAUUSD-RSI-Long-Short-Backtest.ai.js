describe_indicator('XAUUSD RSI Long Short Signals', 'price');

// NOTE: TrendSpider Custom JS API has no strategy/backtest engine
// (no strategy.entry/exit, no table.cell, no pyramiding model).
// This script reproduces the RSI-based entry/exit logic manually
// using a simple position simulation loop, and exposes the signals
// via register_signal() so they can be used in Scanners/Alerts.
// The PnL table from Pine is approximated via paint_overlay().

const myTab = input.tab('RSI Settings');
const myRsiTimeframe = myTab.select('RSI Timeframe', '5', constants.time_frames);
const myRsiLength = myTab.number('RSI Length', 14, { min: 1, max: 200 });

const myLevelsRow = myTab.row();
const myLongRsiLevel = myLevelsRow.number('Buy When RSI Below', 29, { min: 0, max: 100, step: 0.1 });
const myShortRsiLevel = myLevelsRow.number('Short When RSI Above', 71, { min: 0, max: 100, step: 0.1 });

const myEnableTab = input.tab('Trade Settings');
const myEnableRow = myEnableTab.row();
const myEnableLong = myEnableRow.boolean('Enable Buy Trades', true);
const myEnableShort = myEnableRow.boolean('Enable Short Trades', true);

const mySizeRow = myEnableTab.row();
const myLotSize = mySizeRow.number('Lot Size', 0.02, { min: 0.001, max: 100, step: 0.01 });
const myOuncesPerLot = mySizeRow.number('Ounces Per 1 Lot', 100, { min: 1, max: 10000, step: 1 });

const myTpSlRow = myEnableTab.row();
const myTakeProfitUsd = myTpSlRow.number('Take Profit USD', 20, { min: 0, max: 100000, step: 1 });
const myStopLossUsd = myTpSlRow.number('Stop Loss USD', 20, { min: 0, max: 100000, step: 1 });

const myDisplayTab = input.tab('Display');
const myShowTpSlLines = myDisplayTab.boolean('Show TP SL Lines', true);
const myShowSignals = myDisplayTab.boolean('Show Buy Short Signals', true);
const myShowTable = myDisplayTab.boolean('Show PnL Table', true);

// Position size (ounces)
const myTradeQty = myLotSize * myOuncesPerLot;
const myTpMove = myTradeQty > 0 ? myTakeProfitUsd / myTradeQty : 0;
const mySlMove = myTradeQty > 0 ? myStopLossUsd / myTradeQty : 0;

// Fetch RSI from the selected (possibly different) timeframe
const myRsiData = await request.history(current.ticker, myRsiTimeframe);
assert(!myRsiData.error, 'Error fetching RSI timeframe data: ' + myRsiData.error);

const myRsiRaw = rsi(myRsiData.close, myRsiLength);

// Land the other-timeframe RSI onto this chart's candles (no lookahead:
// each candle only sees RSI values from closed bars at or before it)
const myRsiLanded = land_points_onto_series(myRsiData.time, myRsiRaw, time, 'le');
const myRsiValue = interpolate_sparse_series(myRsiLanded, 'constant');

// --- Manual position simulation (replicates strategy.position_size logic) ---
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);
const myEntryPrice = series_of(null);
const myTakeProfitLine = series_of(null);
const myStopLossLine = series_of(null);
const myNetProfit = series_of(0);
const myOpenProfit = series_of(0);
const myClosedTrades = series_of(0);
const myWinTrades = series_of(0);

let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myPositionAvgPrice = 0;
let myRunningNetProfit = 0;
let myRunningClosedTrades = 0;
let myRunningWinTrades = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myRsi = myRsiValue[myIndex];
	let myLongTakeProfit = null;
	let myLongStopLoss = null;
	let myShortTakeProfit = null;
	let myShortStopLoss = null;

	if (myPositionSize !== 0) {
		myLongTakeProfit = myPositionAvgPrice + myTpMove;
		myLongStopLoss = myPositionAvgPrice - mySlMove;
		myShortTakeProfit = myPositionAvgPrice - myTpMove;
		myShortStopLoss = myPositionAvgPrice + mySlMove;
	}

	// Check exits first, using this candle's high/low (TP/SL hit)
	if (myPositionSize > 0 && myRsi !== null) {
		const myHitTp = high[myIndex] >= myLongTakeProfit;
		const myHitSl = low[myIndex] <= myLongStopLoss;
		if (myHitTp || myHitSl) {
			const myExitPrice = myHitTp ? myLongTakeProfit : myLongStopLoss;
			const myTradePnl = (myExitPrice - myPositionAvgPrice) * myTradeQty;
			myRunningNetProfit += myTradePnl;
			myRunningClosedTrades += 1;
			if (myTradePnl > 0) myRunningWinTrades += 1;
			myPositionSize = 0;
			myPositionAvgPrice = 0;
		}
	}
	else if (myPositionSize < 0 && myRsi !== null) {
		const myHitTp = low[myIndex] <= myShortTakeProfit;
		const myHitSl = high[myIndex] >= myShortStopLoss;
		if (myHitTp || myHitSl) {
			const myExitPrice = myHitTp ? myShortTakeProfit : myShortStopLoss;
			const myTradePnl = (myPositionAvgPrice - myExitPrice) * myTradeQty;
			myRunningNetProfit += myTradePnl;
			myRunningClosedTrades += 1;
			if (myTradePnl > 0) myRunningWinTrades += 1;
			myPositionSize = 0;
			myPositionAvgPrice = 0;
		}
	}

	// Entry conditions (only when flat)
	const myLong = myEnableLong && myRsi !== null && myRsi < myLongRsiLevel && myPositionSize === 0;
	const myShort = myEnableShort && myRsi !== null && myRsi > myShortRsiLevel && myPositionSize === 0;

	myLongCondition[myIndex] = myLong;
	myShortCondition[myIndex] = myShort;

	if (myLong) {
		myPositionSize = myTradeQty;
		myPositionAvgPrice = close[myIndex];
	}
	else if (myShort) {
		myPositionSize = -myTradeQty;
		myPositionAvgPrice = close[myIndex];
	}

	// Recompute active TP/SL/entry lines after any entry/exit this candle
	if (myPositionSize > 0) {
		myEntryPrice[myIndex] = myPositionAvgPrice;
		myTakeProfitLine[myIndex] = myPositionAvgPrice + myTpMove;
		myStopLossLine[myIndex] = myPositionAvgPrice - mySlMove;
		const myOpenPnl = (close[myIndex] - myPositionAvgPrice) * myTradeQty;
		myOpenProfit[myIndex] = myOpenPnl;
	}
	else if (myPositionSize < 0) {
		myEntryPrice[myIndex] = myPositionAvgPrice;
		myTakeProfitLine[myIndex] = myPositionAvgPrice - myTpMove;
		myStopLossLine[myIndex] = myPositionAvgPrice + mySlMove;
		const myOpenPnl = (myPositionAvgPrice - close[myIndex]) * myTradeQty;
		myOpenProfit[myIndex] = myOpenPnl;
	}
	else {
		myEntryPrice[myIndex] = null;
		myTakeProfitLine[myIndex] = null;
		myStopLossLine[myIndex] = null;
		myOpenProfit[myIndex] = 0;
	}

	myNetProfit[myIndex] = myRunningNetProfit;
	myClosedTrades[myIndex] = myRunningClosedTrades;
	myWinTrades[myIndex] = myRunningWinTrades;
}

// --- Signals (always registered, usable in scanners/alerts) ---
register_signal(myLongCondition, 'Buy Signal');
register_signal(myShortCondition, 'Short Signal');

// --- Background coloring for RSI zones ---
const myCandleColors = for_every(myLongCondition, myShortCondition, (_myLong, _myShort) => {
	if (_myLong) return 'rgba(0,255,0,0.12)';
	if (_myShort) return 'rgba(255,0,0,0.12)';
	return null;
});
color_candles(myCandleColors);

// --- Lines ---
paint(myShowTpSlLines ? myTakeProfitLine : series_of(null), { name: 'TakeProfit', color: 'green', thickness: 2, style: 'line' });
paint(myShowTpSlLines ? myStopLossLine : series_of(null), { name: 'StopLoss', color: 'red', thickness: 2, style: 'line' });
paint(myShowTpSlLines ? myEntryPrice : series_of(null), { name: 'EntryPrice', color: 'blue', thickness: 2, style: 'line' });

// --- Buy/Short labels ---
const myBuyLabels = for_every(myLongCondition, _myLong => (_myLong && myShowSignals) ? constants.icons.triangle_up : null);
const mySellLabels = for_every(myShortCondition, _myShort => (_myShort && myShowSignals) ? constants.icons.triangle_down : null);
paint(myBuyLabels, { name: 'BuySignal', style: 'labels_below', color: 'green' });
paint(mySellLabels, { name: 'ShortSignal', style: 'labels_above', color: 'red' });

// --- PnL summary overlay (approximation of Pine table) ---
const myLastIndex = close.length - 1;
const myTotalPnl = myNetProfit[myLastIndex] + myOpenProfit[myLastIndex];
const myWinRate = myClosedTrades[myLastIndex] > 0 ? (myWinTrades[myLastIndex] / myClosedTrades[myLastIndex] * 100) : 0;
const myPositionText = myPositionSize > 0 ? 'BUY OPEN' : (myPositionSize < 0 ? 'SHORT OPEN' : 'NO TRADE');

const myTableRows = [
	{ cells: [{ text: 'Total PnL' }, { text: '$' + myTotalPnl.toFixed(2), color: myTotalPnl >= 0 ? 'green' : 'red' }] },
	{ cells: [{ text: 'Net Profit' }, { text: '$' + myNetProfit[myLastIndex].toFixed(2), color: myNetProfit[myLastIndex] >= 0 ? 'green' : 'red' }] },
	{ cells: [{ text: 'Open PnL' }, { text: '$' + myOpenProfit[myLastIndex].toFixed(2), color: myOpenProfit[myLastIndex] >= 0 ? 'green' : 'red' }] },
	{ cells: [{ text: 'Closed Trades' }, { text: String(myClosedTrades[myLastIndex]) }] },
	{ cells: [{ text: 'Win Rate' }, { text: myWinRate.toFixed(2) + '%' }] },
	{ cells: [{ text: 'Current RSI' }, { text: myRsiValue[myLastIndex] !== null ? myRsiValue[myLastIndex].toFixed(2) : 'n/a' }] },
	{ cells: [{ text: 'Position' }, { text: myPositionText }] },
	{ cells: [{ text: 'Lot Size' }, { text: String(myLotSize) }] }
];

paint_overlay('RsiPnlTable', { position: 'top_right' }, {
	rows: myShowTable ? myTableRows : []
});