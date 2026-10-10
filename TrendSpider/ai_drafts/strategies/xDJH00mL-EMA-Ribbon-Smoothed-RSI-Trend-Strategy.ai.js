// ===================================================================
// This is a best-effort translation of a Pine Script v6 strategy into
// TrendSpider Custom JS. Trade boxes are approximated with painted
// lines (TrendSpider has no "box" drawing primitive). The on-chart
// "info table" from Pine becomes a paint_overlay(). Order fills are
// simulated bar-by-bar using High/Low vs SL/TP (TrendSpider cannot
// execute a real backtest inside an indicator script).
// ===================================================================
describe_indicator('EMA Ribbon plus Smoothed RSI Trend', 'price');

const myTrendTab = input.tab('Trend Filter');
const myEmaFastLen = myTrendTab.number('EMA Fast', 10, { min: 1, max: 500 });
const myEmaSlowLen = myTrendTab.number('EMA Slow', 20, { min: 1, max: 500 });
const mySmaFastLen = myTrendTab.number('SMA Fast (ribbon)', 20, { min: 1, max: 500 });
const mySmaSlowLen = myTrendTab.number('SMA Slow (ribbon)', 50, { min: 1, max: 500 });

const myRsiTab = input.tab('RSI Trigger');
const myRsiLen = myRsiTab.number('RSI Length', 21, { min: 1, max: 500 });
const myRsiSmoothLen = myRsiTab.number('RSI Smoothing Length', 50, { min: 1, max: 500 });
const myBuyLevel = myRsiTab.number('Buy Level', 51, { min: 0, max: 100 });
const mySellLevel = myRsiTab.number('Sell Level', 49, { min: 0, max: 100 });
const myRequireCross = myRsiTab.boolean('Only trigger on cross', true);

const myRiskTab = input.tab('Stop Loss / Take Profit');
const mySwingLookback = myRiskTab.number('Swing Lookback (bars)', 20, { min: 1, max: 500 });
const mySlBufferTicks = myRiskTab.number('SL Buffer (ticks)', 5, { min: 0, max: 1000 });
const myMinSlTicks = myRiskTab.number('Minimum SL Distance (ticks)', 20, { min: 0, max: 1000 });
const myRR = myRiskTab.number('Risk Reward Ratio', 2, { min: 0.1, max: 50 });

const myBoxTab = input.tab('Trade Boxes');
const myShowBoxes = myBoxTab.boolean('Draw entry/SL/TP lines', true);

// ---- Core indicators ----
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const mySmaFast = sma(close, mySmaFastLen);
const mySmaSlow = sma(close, mySmaSlowLen);

const myRsiRaw = rsi(close, myRsiLen);
const myRsiSmooth = sma(myRsiRaw, myRsiSmoothLen);

// "tick" (mintick) is not exposed in Custom JS API; approximated using
// current.decimals as a proxy for the minimum price increment.
const myTick = Math.pow(10, -current.decimals);

const myTrendUp = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);

// crossover / crossunder of rsiSmooth vs levels, computed manually
const myCrossedUpBuy = series_of(false);
const myCrossedDownSell = series_of(false);
for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	myCrossedUpBuy[myIndex] = myRsiSmooth[myIndex] > myBuyLevel && myRsiSmooth[myIndex - 1] <= myBuyLevel;
	myCrossedDownSell[myIndex] = myRsiSmooth[myIndex] < mySellLevel && myRsiSmooth[myIndex - 1] >= mySellLevel;
}

const mySwingLow = lowest(low, mySwingLookback);
const mySwingHigh = highest(high, mySwingLookback);

// ---- Signals (barstate.isconfirmed is treated as "every historical bar") ----
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myRsiTrigger = myRequireCross ? myCrossedUpBuy[myIndex] : myRsiSmooth[myIndex] > myBuyLevel;
	const myRsiTriggerShort = myRequireCross ? myCrossedDownSell[myIndex] : myRsiSmooth[myIndex] < mySellLevel;
	myLongSignal[myIndex] = myTrendUp[myIndex] && myRsiTrigger;
	myShortSignal[myIndex] = myTrendUp[myIndex] && myRsiTriggerShort;
}

// ---- Trade simulation (approximate fills using High/Low touches) ----
const mySlSeries = series_of(null);
const myTpSeries = series_of(null);

let myPositionSize = 0;
let myActiveSL = null;
let myActiveTP = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// check exits first
	if (myPositionSize > 0) {
		if (low[myIndex] <= myActiveSL || high[myIndex] >= myActiveTP) {
			myPositionSize = 0;
			myActiveSL = null;
			myActiveTP = null;
		}
	}
	else if (myPositionSize < 0) {
		if (high[myIndex] >= myActiveSL || low[myIndex] <= myActiveTP) {
			myPositionSize = 0;
			myActiveSL = null;
			myActiveTP = null;
		}
	}

	// check entries (only when flat)
	if (myPositionSize === 0 && myLongSignal[myIndex]) {
		const mySlRaw = mySwingLow[myIndex] - mySlBufferTicks * myTick;
		const myDistRaw = close[myIndex] - mySlRaw;
		const myDist = Math.max(myDistRaw, myMinSlTicks * myTick);
		myActiveSL = close[myIndex] - myDist;
		myActiveTP = close[myIndex] + myDist * myRR;
		myPositionSize = 1;
	}
	else if (myPositionSize === 0 && myShortSignal[myIndex]) {
		const mySlRaw = mySwingHigh[myIndex] + mySlBufferTicks * myTick;
		const myDistRaw = mySlRaw - close[myIndex];
		const myDist = Math.max(myDistRaw, myMinSlTicks * myTick);
		myActiveSL = close[myIndex] + myDist;
		myActiveTP = close[myIndex] - myDist * myRR;
		myPositionSize = -1;
	}

	mySlSeries[myIndex] = myPositionSize !== 0 ? myActiveSL : null;
	myTpSeries[myIndex] = myPositionSize !== 0 ? myActiveTP : null;
}

// ---- Painting ----
paint(myEmaFast, { name: 'EMAFast', color: '#ffffff', thickness: 2 });
paint(myEmaSlow, { name: 'EMASlow', color: '#f2c94c', thickness: 2 });
paint(mySmaFast, { name: 'SMAFast', color: '#f2994a', thickness: 1 });
paint(mySmaSlow, { name: 'SMASlow', color: '#eb9f6e', thickness: 1 });

const mySlLine = paint(myShowBoxes ? mySlSeries : constants.empty_series, { name: 'StopLoss', color: '#eb5757', style: 'ladder', thickness: 1 });
const myTpLine = paint(myShowBoxes ? myTpSeries : constants.empty_series, { name: 'TakeProfit', color: '#27ae60', style: 'ladder', thickness: 1 });
fill(mySlLine, myTpLine, '#27ae60', 0.08);

// ---- Signals for scanners / alerts / strategy tester ----
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(for_every(myLongSignal, myShortSignal, (_l, _s) => !_l && !_s ? false : true), 'Any Entry');

// ---- Info overlay (replacement for Pine's table.new) ----
const myLastTrendUp = myTrendUp[myTrendUp.length - 1];
const myLastRsiSmooth = myRsiSmooth[myRsiSmooth.length - 1];

paint_overlay('InfoPanel', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: myLastTrendUp ? 'Trend UP (tradeable)' : 'Trend flat/down (no trades)', color: myLastTrendUp ? '#2ecc71' : '#95a5a6' }] },
		{ cells: [{ text: 'RSI Smoothed: ' + (myLastRsiSmooth === null ? 'n/a' : myLastRsiSmooth.toFixed(2)), color: myLastRsiSmooth > myBuyLevel ? '#2ecc71' : (myLastRsiSmooth < mySellLevel ? '#e74c3c' : '#95a5a6') }] }
	]
});