describe_indicator('BOT GOAT EMA Cross Strategy', 'price');

// ---------------- INPUTS ----------------
const myTrendTab = input.tab('Trend');
const myEmaFastLen = myTrendTab.number('Fast EMA', 21, { min: 1, max: 500 });
const myEmaSlowLen = myTrendTab.number('Slow EMA', 55, { min: 1, max: 500 });

const myFiltersTab = input.tab('Filters');
const myOnly15m = myFiltersTab.boolean('Only trade on the 15-minute chart', true);
const myTradeWeekdaysOnly = myFiltersTab.boolean('Trade weekdays only (Mon-Fri)', true);

const myRiskTab = input.tab('Risk ($)');
const mySlDollars = myRiskTab.number('Stop Loss ($)', 1.0, { min: 0, max: 1000, step: 0.1 });
const myTrailLagDollars = myRiskTab.number('Trailing activation lag ($)', 0.60, { min: 0, max: 1000, step: 0.1 });
const myTrailFollowDollars = myRiskTab.number('Trailing follow distance ($)', 0.10, { min: 0, max: 1000, step: 0.1 });

const myDisplayTab = input.tab('Display');
const myShowArrows = myDisplayTab.boolean('Show entry arrows', true);
const myShowLines = myDisplayTab.boolean('Show Entry SL Trail lines', true);

// ---------------- CALCULATIONS ----------------
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

// Cross detection, replicating ta.crossover / ta.crossunder
const myEmaCrossUp = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myEmaFast[_i - 1] <= myEmaSlow[_i - 1] && _fast > _slow;
});
const myEmaCrossDown = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myEmaFast[_i - 1] >= myEmaSlow[_i - 1] && _fast < _slow;
});

// Weekday / timeframe filters
// NOTE: Pine's dayofweek uses exchange time; we approximate using time_of(),
// which also uses exchange timezone, so this should match in practice.
const myTfOk = !myOnly15m || current.resolution === '15';

const myLength = close.length;
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myDow = time_of(time[myIndex]).dayOfWeek; // 1 Mon ... 7 Sun
	const myIsWeekday = myDow !== 6 && myDow !== 7;
	const myTradeOk = myTfOk && (!myTradeWeekdaysOnly || myIsWeekday);
	myLongSignal[myIndex] = myEmaCrossUp[myIndex] && myTradeOk;
	myShortSignal[myIndex] = myEmaCrossDown[myIndex] && myTradeOk;
}

// ---------------- POSITION / LEVEL SIMULATION ----------------
// Simulates strategy.position_size, entry/SL/trailing stop reconstruction
// following the Pine script logic exactly (full-equity, flip on signal,
// SL in dollars, trailing arms at trailLagDollars and follows trailFollowDollars behind).
const myEntryLine = series_of(null);
const mySlLine = series_of(null);
const myTrailLine = series_of(null);

let myPositionSize = 0; // >0 long, <0 short, 0 flat
let myEntryPx = null;
let mySlPx = null;
let myTrailPx = null;
let myTrailLive = false;

for (let myIndex = 0; myIndex < myLength; myIndex += 1) {
	const myPrevPositionSize = myPositionSize;

	// Entries: flip on opposite signal, full equity, pyramiding = 0
	if (myLongSignal[myIndex] && myPositionSize <= 0) {
		myPositionSize = 1;
	}
	else if (myShortSignal[myIndex] && myPositionSize >= 0) {
		myPositionSize = -1;
	}

	// Exits by SL/trailing are checked against prior bar's levels
	if (myPrevPositionSize > 0 && mySlPx !== null && low[myIndex] <= mySlPx) {
		myPositionSize = 0;
	}
	else if (myPrevPositionSize > 0 && myTrailLive && myTrailPx !== null && low[myIndex] <= myTrailPx) {
		myPositionSize = 0;
	}
	else if (myPrevPositionSize < 0 && mySlPx !== null && high[myIndex] >= mySlPx) {
		myPositionSize = 0;
	}
	else if (myPrevPositionSize < 0 && myTrailLive && myTrailPx !== null && high[myIndex] >= myTrailPx) {
		myPositionSize = 0;
	}

	const myInLong = myPositionSize > 0;
	const myInShort = myPositionSize < 0;
	const myFlat = myPositionSize === 0;

	const myNewLong = myInLong && myPrevPositionSize <= 0;
	const myNewShort = myInShort && myPrevPositionSize >= 0;

	if (myNewLong) {
		myEntryPx = close[myIndex];
		mySlPx = myEntryPx - mySlDollars;
		myTrailPx = null;
		myTrailLive = false;
	}

	if (myNewShort) {
		myEntryPx = close[myIndex];
		mySlPx = myEntryPx + mySlDollars;
		myTrailPx = null;
		myTrailLive = false;
	}

	if (myInLong) {
		if (high[myIndex] - myEntryPx >= myTrailLagDollars) {
			myTrailLive = true;
		}
		if (myTrailLive) {
			const myCandidate = high[myIndex] - myTrailFollowDollars;
			myTrailPx = myTrailPx === null ? myCandidate : Math.max(myTrailPx, myCandidate);
		}
	}
	else if (myInShort) {
		if (myEntryPx - low[myIndex] >= myTrailLagDollars) {
			myTrailLive = true;
		}
		if (myTrailLive) {
			const myCandidate = low[myIndex] + myTrailFollowDollars;
			myTrailPx = myTrailPx === null ? myCandidate : Math.min(myTrailPx, myCandidate);
		}
	}

	if (myFlat) {
		myEntryPx = null;
		mySlPx = null;
		myTrailPx = null;
		myTrailLive = false;
	}

	myEntryLine[myIndex] = myShowLines ? myEntryPx : null;
	mySlLine[myIndex] = myShowLines ? mySlPx : null;
	myTrailLine[myIndex] = myShowLines ? myTrailPx : null;
}

// ---------------- PLOTS ----------------
paint(myEmaFast, { name: 'FastEMA', color: '#00e0e0', thickness: 2 });
paint(myEmaSlow, { name: 'SlowEMA', color: '#ff9900', thickness: 2 });

paint(myEntryLine, { name: 'Entry', color: 'gray', thickness: 2, style: 'line' });
paint(mySlLine, { name: 'StopLoss', color: 'red', thickness: 2, style: 'line' });
paint(myTrailLine, { name: 'TrailingStop', color: '#ff9900', thickness: 2, style: 'line' });

const myLongArrow = for_every(myLongSignal, _s => (myShowArrows && _s) ? constants.icons.triangle_up : null);
const myShortArrow = for_every(myShortSignal, _s => (myShowArrows && _s) ? constants.icons.triangle_down : null);

paint(myLongArrow, { name: 'LongArrow', style: 'labels_below', color: '#00ff80' });
paint(myShortArrow, { name: 'ShortArrow', style: 'labels_above', color: '#ff00ff' });

// ---------------- SIGNALS FOR SCANNER / ALERTS / STRATEGY ----------------
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');