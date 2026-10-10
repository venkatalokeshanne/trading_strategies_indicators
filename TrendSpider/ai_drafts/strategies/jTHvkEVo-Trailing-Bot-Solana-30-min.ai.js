// ============================================================
// Experiment: this is a best-effort translation of a TradingView
// Pine Script v6 strategy into a TrendSpider Custom JS indicator.
// TrendSpider has no backtesting engine inside indicators, so the
// position/SL/trailing-stop simulation below is reconstructed with
// a manual bar-by-bar loop that mimics the Pine logic as closely
// as possible. Results may diverge from the real Pine backtest,
// especially around intrabar fills (Pine uses high/low touches,
// this uses the same high/low logic here, bar-by-bar, no intrabar
// ordering assumptions beyond what Pine itself documents).
// ============================================================
describe_indicator('BOT GOAT EMA Cross Strategy', 'price');

const trendTab = input.tab('Trend');
const myFastLen = trendTab.number('Fast EMA', 21, { min: 1, max: 500 });
const mySlowLen = trendTab.number('Slow EMA', 55, { min: 1, max: 500 });

const filtersTab = input.tab('Filters');
// Shortened title to satisfy the platform's input name length limit.
const myOnly30m = filtersTab.boolean('Only 30 min chart', true);
// Shortened further to fix "input(): name is too lengthy" error.
const myWeekdaysOnly = filtersTab.boolean('Weekdays only', true);

const riskTab = input.tab('Risk');
const riskRow1 = riskTab.row();
const mySlDollars = riskRow1.number('Stop Loss', 1.0, { min: 0, max: 1000, step: 0.1 });
const riskRow2 = riskTab.row();
// Shortened names below to fix "input(): name is too lengthy" error.
const myTrailLagDollars = riskRow2.number('Trail Lag', 0.60, { min: 0, max: 1000, step: 0.1 });
const myTrailFollowDollars = riskRow2.number('Trail Dist', 0.10, { min: 0, max: 1000, step: 0.1 });

const displayTab = input.tab('Display');
const myShowArrows = displayTab.boolean('Show entry arrows', true);
const myShowLines = displayTab.boolean('Show Entry SL Trail lines', true);

// EMAs
const myEmaFast = ema(close, myFastLen);
const myEmaSlow = ema(close, mySlowLen);

// crossover / crossunder reconstruction
const myEmaCrossUp = series_of(false);
const myEmaCrossDown = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevDiff = myEmaFast[myIndex - 1] - myEmaSlow[myIndex - 1];
	const myCurrDiff = myEmaFast[myIndex] - myEmaSlow[myIndex];
	myEmaCrossUp[myIndex] = myPrevDiff <= 0 && myCurrDiff > 0;
	myEmaCrossDown[myIndex] = myPrevDiff >= 0 && myCurrDiff < 0;
}

// weekday / timeframe filters
// NOTE: dayOfWeek 1=Mon...7=Sun as per bar_at(); ISO style
const myTfOk = (!myOnly30m) || (current.resolution === '30');

const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myDow = time_of(time[myIndex]).dayOfWeek;
	const myIsWeekday = myDow !== 6 && myDow !== 7;
	const myTradeOk = myTfOk && ((!myWeekdaysOnly) || myIsWeekday);
	myLongSignal[myIndex] = myEmaCrossUp[myIndex] && myTradeOk;
	myShortSignal[myIndex] = myEmaCrossDown[myIndex] && myTradeOk;
}

// ---------------- POSITION / SL / TRAIL SIMULATION ----------------
// position: 0 flat, 1 long, -1 short
const myEntryLine = series_of(null);
const mySlLine = series_of(null);
const myTrailLine = series_of(null);

let myPosition = 0;
let myEntryPx = null;
let mySlPx = null;
let myTrailPx = null;
let myTrailLive = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myHigh = high[myIndex];
	const myLow = low[myIndex];
	const myClose = close[myIndex];

	// handle entries/flips (evaluated at signal bar, like strategy.entry on same bar)
	if (myLongSignal[myIndex] && myPosition !== 1) {
		myPosition = 1;
		myEntryPx = myClose;
		mySlPx = myEntryPx - mySlDollars;
		myTrailPx = null;
		myTrailLive = false;
	}
	else if (myShortSignal[myIndex] && myPosition !== -1) {
		myPosition = -1;
		myEntryPx = myClose;
		mySlPx = myEntryPx + mySlDollars;
		myTrailPx = null;
		myTrailLive = false;
	}

	// trailing reconstruction while in a position
	if (myPosition === 1) {
		if (myHigh - myEntryPx >= myTrailLagDollars) {
			myTrailLive = true;
		}
		if (myTrailLive) {
			const myCandidate = myHigh - myTrailFollowDollars;
			myTrailPx = myTrailPx === null ? myCandidate : Math.max(myTrailPx, myCandidate);
		}
		// check stop/trail hit via low touch -> flat
		const myStopLevel = myTrailLive && myTrailPx !== null ? Math.max(mySlPx, myTrailPx) : mySlPx;
		if (myLow <= myStopLevel) {
			myPosition = 0;
			myEntryPx = null;
			mySlPx = null;
			myTrailPx = null;
			myTrailLive = false;
		}
	}
	else if (myPosition === -1) {
		if (myEntryPx - myLow >= myTrailLagDollars) {
			myTrailLive = true;
		}
		if (myTrailLive) {
			const myCandidate = myLow + myTrailFollowDollars;
			myTrailPx = myTrailPx === null ? myCandidate : Math.min(myTrailPx, myCandidate);
		}
		const myStopLevel = myTrailLive && myTrailPx !== null ? Math.min(mySlPx, myTrailPx) : mySlPx;
		if (myHigh >= myStopLevel) {
			myPosition = 0;
			myEntryPx = null;
			mySlPx = null;
			myTrailPx = null;
			myTrailLive = false;
		}
	}

	myEntryLine[myIndex] = myPosition !== 0 ? myEntryPx : null;
	mySlLine[myIndex] = myPosition !== 0 ? mySlPx : null;
	myTrailLine[myIndex] = (myPosition !== 0 && myTrailLive) ? myTrailPx : null;
}

// ---------------- PAINT ----------------
paint(myEmaFast, { name: 'Fast EMA', color: '#00BCD4', thickness: 2 });
paint(myEmaSlow, { name: 'Slow EMA', color: '#FF9800', thickness: 2 });

paint(myShowLines ? myEntryLine : constants.empty_series, { name: 'Entry Line', color: '#9E9E9E', style: 'ladder', thickness: 2 });
paint(myShowLines ? mySlLine : constants.empty_series, { name: 'Stop Loss Line', color: '#E53935', style: 'ladder', thickness: 2 });
paint(myShowLines ? myTrailLine : constants.empty_series, { name: 'Trailing Stop Line', color: '#FB8C00', style: 'ladder', thickness: 2 });

const myLongArrowSeries = for_every(myLongSignal, low, (_signal, _low) => _signal ? _low : null);
const myShortArrowSeries = for_every(myShortSignal, high, (_signal, _high) => _signal ? _high : null);

paint(myShowArrows ? myLongArrowSeries : constants.empty_series, { name: 'Long Arrow', style: 'labels_below', color: '#00E676' });
paint(myShowArrows ? myShortArrowSeries : constants.empty_series, { name: 'Short Arrow', style: 'labels_above', color: '#E040FB' });

// ---------------- SIGNALS FOR SCANNER ALERTS STRATEGY ----------------
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(for_every(myLongSignal, myShortSignal, (_l, _s) => _l || _s), 'Any Entry Flip');