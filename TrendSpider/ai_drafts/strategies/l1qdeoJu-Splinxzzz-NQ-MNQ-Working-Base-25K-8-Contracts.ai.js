// NOTE: this is a best-effort translation of a TradingView Pine Script
// strategy into TrendSpider Custom JS. TrendSpider scripts can not run a
// real order-management/backtesting engine (no strategy.entry/exit,
// no strategy.netprofit, no contract point value lookup), so the
// trade simulation and dollar P&L used here for the "daily loss kill
// switch" are approximated with a simple point-difference x qty model.
// Zones, signals and filters themselves are reproduced exactly as per
// the Pine math.
describe_indicator('Splinxzzz NQ-MNQ Base (Pine Conversion)', 'price');

const myPivotLen = input.number('Pivot Length', 3, { min: 2, max: 50 });
const myZonePad = input.number('Zone Pad', 1.5, { min: 0, max: 50, step: 0.25 });
const myRR = input.number('Risk Reward', 1.8, { min: 0.1, max: 10, step: 0.1 });
const myEmaLen = input.number('EMA Length', 20, { min: 1, max: 200 });
const myDispATR = input.number('Displacement ATR', 0.2, { min: 0, max: 5, step: 0.1 });
const myChopATR = input.number('Chop ATR', 1.2, { min: 0, max: 5, step: 0.1 });
const mySweepLookback = input.number('Sweep Lookback', 6, { min: 2, max: 50 });
const myMaxDailyLossUSD = input.number('Daily Loss Limit', 900, { min: 0, max: 100000, step: 25 });
const myQty = input.number('Quantity (points multiplier)', 8, { min: 1, max: 1000 });

// core indicators
const myAtr = atr(high, low, close, 14);
const myEma = ema(close, myEmaLen);
const myPivotHigh = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLow = pivot_low(low, myPivotLen, myPivotLen);

// sweep helpers
const myPrevLow = shift(lowest(low, mySweepLookback), 1);
const myPrevHigh = shift(highest(high, mySweepLookback), 1);

// chop filter
const myPriceRange = sub(highest(high, 20), lowest(low, 20));

// day marker, used to detect "new day" boundaries
const myDaySession = time.map(_t => bar_at(_t).session);

const myDemandTop = series_of(null);
const myDemandBot = series_of(null);
const mySupplyTop = series_of(null);
const mySupplyBot = series_of(null);
const myLongCond = series_of(false);
const myShortCond = series_of(false);
const myKillSwitch = series_of(false);

let myRunningDemandTop = null;
let myRunningDemandBot = null;
let myRunningSupplyTop = null;
let myRunningSupplyBot = null;

// simulated trade state (approximation of strategy engine)
let myPositionSize = 0;
let myEntryPrice = null;
let myStopPrice = null;
let myTpPrice = null;
let myNetProfit = 0;
let myDayStartProfit = null;
let myLastSession = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// update zones from pivot points (carried forward like Pine's "var float")
	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		myRunningDemandTop = myPivotLow[myIndex] + myZonePad;
		myRunningDemandBot = myPivotLow[myIndex] - myZonePad;
	}
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		myRunningSupplyTop = myPivotHigh[myIndex] + myZonePad;
		myRunningSupplyBot = myPivotHigh[myIndex] - myZonePad;
	}

	myDemandTop[myIndex] = myRunningDemandTop;
	myDemandBot[myIndex] = myRunningDemandBot;
	mySupplyTop[myIndex] = myRunningSupplyTop;
	mySupplyBot[myIndex] = myRunningSupplyBot;

	// new day handling
	const myIsNewDay = myLastSession !== null && myDaySession[myIndex] !== myLastSession;
	myLastSession = myDaySession[myIndex];

	if (myDayStartProfit === null) {
		myDayStartProfit = myNetProfit;
	}
	if (myIsNewDay) {
		myDayStartProfit = myNetProfit;
	}

	// check stop/limit of open simulated position using this bar's range
	if (myPositionSize > 0 && myStopPrice !== null) {
		if (low[myIndex] <= myStopPrice) {
			myNetProfit += (myStopPrice - myEntryPrice) * myQty;
			myPositionSize = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTpPrice = null;
		}
		else if (high[myIndex] >= myTpPrice) {
			myNetProfit += (myTpPrice - myEntryPrice) * myQty;
			myPositionSize = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTpPrice = null;
		}
	}
	else if (myPositionSize < 0 && myStopPrice !== null) {
		if (high[myIndex] >= myStopPrice) {
			myNetProfit += (myEntryPrice - myStopPrice) * myQty;
			myPositionSize = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTpPrice = null;
		}
		else if (low[myIndex] <= myTpPrice) {
			myNetProfit += (myEntryPrice - myTpPrice) * myQty;
			myPositionSize = 0;
			myEntryPrice = null;
			myStopPrice = null;
			myTpPrice = null;
		}
	}

	const myDailyPnL = myNetProfit - myDayStartProfit;
	const myKill = myDailyPnL <= -myMaxDailyLossUSD;
	myKillSwitch[myIndex] = myKill;

	// hard daily stop: close open position at this bar's close
	if (myKill && myPositionSize > 0) {
		myNetProfit += (close[myIndex] - myEntryPrice) * myQty;
		myPositionSize = 0;
		myEntryPrice = null;
		myStopPrice = null;
		myTpPrice = null;
	}
	if (myKill && myPositionSize < 0) {
		myNetProfit += (myEntryPrice - close[myIndex]) * myQty;
		myPositionSize = 0;
		myEntryPrice = null;
		myStopPrice = null;
		myTpPrice = null;
	}

	// sweeps / attempts
	const myBullSweep = low[myIndex] < myPrevLow[myIndex] && close[myIndex] > myPrevLow[myIndex];
	const myBearSweep = high[myIndex] > myPrevHigh[myIndex] && close[myIndex] < myPrevHigh[myIndex];
	const myBullAttempt = myIndex > 0 && low[myIndex] < low[myIndex - 1] && close[myIndex] > open[myIndex];
	const myBearAttempt = myIndex > 0 && high[myIndex] > high[myIndex - 1] && close[myIndex] < open[myIndex];

	// filters
	const myNotChop = myPriceRange[myIndex] > myAtr[myIndex] * myChopATR;
	const myBullDisp = close[myIndex] > open[myIndex] && (close[myIndex] - open[myIndex]) > myAtr[myIndex] * myDispATR;
	const myBearDisp = close[myIndex] < open[myIndex] && (open[myIndex] - close[myIndex]) > myAtr[myIndex] * myDispATR;
	const myBullBias = close[myIndex] > myEma[myIndex];
	const myBearBias = close[myIndex] < myEma[myIndex];

	// rejection
	const myBullReject = myRunningDemandTop !== null &&
		low[myIndex] <= myRunningDemandTop &&
		close[myIndex] > myRunningDemandTop;
	const myBearReject = myRunningSupplyBot !== null &&
		high[myIndex] >= myRunningSupplyBot &&
		close[myIndex] < myRunningSupplyBot;

	// entry conditions
	const myLong = !myKill &&
		myBullReject &&
		(myBullSweep || myBullAttempt) &&
		myBullDisp &&
		myBullBias &&
		myNotChop;

	const myShort = !myKill &&
		myBearReject &&
		(myBearSweep || myBearAttempt) &&
		myBearDisp &&
		myBearBias &&
		myNotChop;

	myLongCond[myIndex] = myLong;
	myShortCond[myIndex] = myShort;

	// simulated order placement
	if (myLong && myPositionSize <= 0) {
		const myStopLong = myRunningDemandBot;
		const myRiskLong = close[myIndex] - myStopLong;
		if (myRiskLong > 0) {
			// close an existing short first (flat/flip), realize its P&L
			if (myPositionSize < 0) {
				myNetProfit += (myEntryPrice - close[myIndex]) * myQty;
			}
			myPositionSize = 1;
			myEntryPrice = close[myIndex];
			myStopPrice = myStopLong;
			myTpPrice = close[myIndex] + myRiskLong * myRR;
		}
	}
	else if (myShort && myPositionSize >= 0) {
		const myStopShort = myRunningSupplyTop;
		const myRiskShort = myStopShort - close[myIndex];
		if (myRiskShort > 0) {
			if (myPositionSize > 0) {
				myNetProfit += (close[myIndex] - myEntryPrice) * myQty;
			}
			myPositionSize = -1;
			myEntryPrice = close[myIndex];
			myStopPrice = myStopShort;
			myTpPrice = close[myIndex] - myRiskShort * myRR;
		}
	}
}

// visuals
paint(myDemandTop, { name: 'Demand Top', color: '#2ca599', thickness: 2 });
paint(myDemandBot, { name: 'Demand Bottom', color: '#2ca599', thickness: 2 });
paint(mySupplyTop, { name: 'Supply Top', color: '#ee5451', thickness: 2 });
paint(mySupplyBot, { name: 'Supply Bottom', color: '#ee5451', thickness: 2 });

// Note: painted line/label names must be unique across the whole
// indicator (paint + register_signal share one namespace), so the
// labels below use "Mark" suffixes to avoid clashing with the
// register_signal names used further down.
const myLongMarks = for_every(myLongCond, _l => _l ? true : null);
const myShortMarks = for_every(myShortCond, _s => _s ? true : null);
paint(myLongMarks.map((_v, _i) => _v ? low[_i] : null), { name: 'Long Signal Mark', style: 'labels_below', color: '#2ca599' });
paint(myShortMarks.map((_v, _i) => _v ? high[_i] : null), { name: 'Short Signal Mark', style: 'labels_above', color: '#ee5451' });
paint(for_every(myKillSwitch, _k => _k ? true : null).map((_v, _i) => _v ? high[_i] : null), { name: 'Daily Loss Hit Mark', style: 'labels_above', color: 'red' });

// scanner/alert/strategy signals
register_signal(myLongCond, 'Long Signal');
register_signal(myShortCond, 'Short Signal');
register_signal(myKillSwitch, 'Daily Loss Hit');