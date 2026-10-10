describe_indicator('Backpulse Optimized (EMA Cross + ATR Trail)', 'price');

// NOTE: This is an INDICATOR port of a Pine Script STRATEGY.
// TrendSpider Custom JS indicators cannot place real orders, manage equity,
// or simulate commissions/slippage. This script reproduces the Pine
// signal logic (crossover conditions, trailing stop math, TP/SL levels)
// and exposes entries/exits as register_signal() outputs usable in
// scanners/alerts/backtests, plus the plotted lines. Intrabar stop/limit
// fills are approximated using each bar's high/low (Pine's strategy
// engine does similar bar-magnifier-less approximation by default).

const myTrendTab = input.tab('Trend Engine');
const myFastLen = myTrendTab.number('Fast EMA Length', 14, { min: 5, max: 100 });
const mySlowLen = myTrendTab.number('Slow EMA Length', 44, { min: 20, max: 200 });

const myVolTab = input.tab('Volatility & Trailing Stop');
const myAtrPeriod = myVolTab.number('ATR Length', 14, { min: 5, max: 50 });
const myAtrMult = myVolTab.number('ATR Multiplier', 2.5, { min: 0.5, max: 6.0, step: 0.25 });

const myRiskTab = input.tab('Risk & Money Management');
const myTpPercent = myRiskTab.number('Take Profit Percent', 6.0, { min: 1.0, max: 25.0, step: 0.5 });
const mySlPercent = myRiskTab.number('Hard Stop Loss Percent', 3.0, { min: 0.5, max: 10.0, step: 0.5 });
const myUseTrailing = myRiskTab.boolean('Enable Dynamic Trailing Stop', true);
const myTradeDir = myRiskTab.select('Trade Direction', 'Both', ['Both', 'Long Only', 'Short Only']);

const myDateTab = input.tab('Backtest Timeframe Filter');
const myStartYear = myDateTab.number('Start Year', 2023, { min: 2015, max: 2030 });

const myMoment = library('moment-timezone');
const myTimezone = current.session.timezone;
const myStartTimestamp = myMoment.tz(`${myStartYear}-01-01 00:00`, myTimezone).unix();

const myFastEma = ema(close, myFastLen);
const mySlowEma = ema(close, mySlowLen);
const myAtr = atr(high, low, close, myAtrPeriod);

const myCanLong = myTradeDir === 'Both' || myTradeDir === 'Long Only';
const myCanShort = myTradeDir === 'Both' || myTradeDir === 'Short Only';

// output series
const myLongTrailStopOut = series_of(null);
const myShortTrailStopOut = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongExitSignal = series_of(false);
const myShortExitSignal = series_of(false);
const myPositionState = series_of(0); // 1 long, -1 short, 0 flat

let myPositionSize = 0;
let myPositionAvgPrice = null;
let myLongTrailStop = null;
let myShortTrailStop = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myInDateRange = time[myIndex] >= myStartTimestamp;

	const myLongCond = fastCross(myIndex, true) && close[myIndex] > mySlowEma[myIndex] && myInDateRange;
	const myShortCond = fastCross(myIndex, false) && close[myIndex] < mySlowEma[myIndex] && myInDateRange;

	// recompute trailing stops (Pine order of operations)
	if (myLongCond) {
		myLongTrailStop = close[myIndex] - (myAtr[myIndex] * myAtrMult);
	}
	else if (myPositionSize > 0 && myUseTrailing) {
		const myBaseline = close[myIndex] - (myAtr[myIndex] * myAtrMult);
		myLongTrailStop = Math.max(myLongTrailStop === null ? myBaseline : myLongTrailStop, myBaseline);
	}
	else {
		myLongTrailStop = null;
	}

	if (myShortCond) {
		myShortTrailStop = close[myIndex] + (myAtr[myIndex] * myAtrMult);
	}
	else if (myPositionSize < 0 && myUseTrailing) {
		const myBaseline = close[myIndex] + (myAtr[myIndex] * myAtrMult);
		myShortTrailStop = Math.min(myShortTrailStop === null ? myBaseline : myShortTrailStop, myBaseline);
	}
	else {
		myShortTrailStop = null;
	}

	// exits checked first against current bar high/low (approximation)
	let myExitedLong = false;
	let myExitedShort = false;

	if (myPositionSize > 0) {
		const myStopLevel = myUseTrailing ? myLongTrailStop : myPositionAvgPrice * (1 - mySlPercent / 100);
		const myLimitLevel = myPositionAvgPrice * (1 + myTpPercent / 100);
		if ((myStopLevel !== null && low[myIndex] <= myStopLevel) || high[myIndex] >= myLimitLevel) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myLongTrailStop = null;
			myExitedLong = true;
		}
	}

	if (myPositionSize < 0) {
		const myStopLevel = myUseTrailing ? myShortTrailStop : myPositionAvgPrice * (1 + mySlPercent / 100);
		const myLimitLevel = myPositionAvgPrice * (1 - myTpPercent / 100);
		if ((myStopLevel !== null && high[myIndex] >= myStopLevel) || low[myIndex] <= myLimitLevel) {
			myPositionSize = 0;
			myPositionAvgPrice = null;
			myShortTrailStop = null;
			myExitedShort = true;
		}
	}

	// entries (only if flat, matching single-position Pine strategy behavior)
	let myEnteredLong = false;
	let myEnteredShort = false;

	if (myLongCond && myCanLong && myPositionSize === 0) {
		myPositionSize = 1;
		myPositionAvgPrice = close[myIndex];
		myEnteredLong = true;
	}
	else if (myShortCond && myCanShort && myPositionSize === 0) {
		myPositionSize = -1;
		myPositionAvgPrice = close[myIndex];
		myEnteredShort = true;
	}

	myLongTrailStopOut[myIndex] = (myUseTrailing && myPositionSize > 0) ? myLongTrailStop : null;
	myShortTrailStopOut[myIndex] = (myUseTrailing && myPositionSize < 0) ? myShortTrailStop : null;
	myLongEntrySignal[myIndex] = myEnteredLong;
	myShortEntrySignal[myIndex] = myEnteredShort;
	myLongExitSignal[myIndex] = myExitedLong;
	myShortExitSignal[myIndex] = myExitedShort;
	myPositionState[myIndex] = myPositionSize;
}

// helper for crossover/crossunder, computed via plain array access (no indicator calls in loop)
function fastCross(myIndex, myIsOver) {
	const myPrevFast = myFastEma[myIndex - 1];
	const myPrevSlow = mySlowEma[myIndex - 1];
	const myCurFast = myFastEma[myIndex];
	const myCurSlow = mySlowEma[myIndex];
	if (myPrevFast === null || myPrevSlow === null || myCurFast === null || myCurSlow === null) return false;
	return myIsOver
		? (myPrevFast <= myPrevSlow && myCurFast > myCurSlow)
		: (myPrevFast >= myPrevSlow && myCurFast < myCurSlow);
}

paint(myFastEma, { name: 'Fast EMA', color: '#6366f1', thickness: 2 });
paint(mySlowEma, { name: 'Slow EMA', color: '#f59e0b', thickness: 2 });
paint(myLongTrailStopOut, { name: 'Long Trail Stop', color: '#10b981', thickness: 2, style: 'ladder' });
paint(myShortTrailStopOut, { name: 'Short Trail Stop', color: '#ef4444', thickness: 2, style: 'ladder' });

color_candles(for_every(myPositionState, _p => _p > 0 ? '#10b98130' : (_p < 0 ? '#ef444430' : null)));

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongExitSignal, 'Long Exit');
register_signal(myShortExitSignal, 'Short Exit');