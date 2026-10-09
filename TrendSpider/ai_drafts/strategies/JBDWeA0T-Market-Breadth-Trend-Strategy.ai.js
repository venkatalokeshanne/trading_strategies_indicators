describe_indicator('Market Breadth Trend Strategy', 'price');

// Pine inputs mapped 1:1
const myEmaFastLen = input.number('Fast EMA', 50, { min: 1, max: 500 });
const myEmaSlowLen = input.number('Slow EMA', 200, { min: 1, max: 500 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrMult = input.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 20 });
const myRr = input.number('Risk Reward', 2.0, { min: 0.1, max: 20 });

// Trend
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);

const myTrendBull = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);
const myTrendBear = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f < _s);

// Simplified Breadth-Style Proxy: sma(close > emaSlow ? 100 : 0, 20)
const myBreadthRaw = for_every(close, myEmaSlow, (_c, _s) => _c > _s ? 100 : 0);
const myBreadthLine = sma(myBreadthRaw, 20);

const myStrongBreadth = for_every(myBreadthLine, _b => _b > 60);
const myWeakBreadth = for_every(myBreadthLine, _b => _b < 40);

// Entry conditions (raw, before position-size filtering)
const myLongConditionRaw = for_every(myTrendBull, myStrongBreadth, (_tb, _sb) => _tb && _sb);
const myShortConditionRaw = for_every(myTrendBear, myWeakBreadth, (_tb, _wb) => _tb && _wb);

const myAtrValue = atr(high, low, close, myAtrLen);

// Simulate strategy.position_size / position_avg_price behavior.
// Pine's strategy.entry() with a single-direction flip: a long entry can only
// happen if position_size <= 0, a short entry only if position_size >= 0.
// Once in a position, exits are evaluated via stop/limit (we approximate by
// checking high/low against the stop/target levels on each subsequent bar).
const myPositionState = series_of(0); // 1 = long, -1 = short, 0 = flat
const myEntryPrice = series_of(null);
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myExitLongSignal = series_of(false);
const myExitShortSignal = series_of(false);
const myLongStopSeries = series_of(null);
const myLongTargetSeries = series_of(null);
const myShortStopSeries = series_of(null);
const myShortTargetSeries = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevState = myIndex > 0 ? myPositionState[myIndex - 1] : 0;
	const myPrevEntryPrice = myIndex > 0 ? myEntryPrice[myIndex - 1] : null;

	let myState = myPrevState;
	let myCurrentEntryPrice = myPrevEntryPrice;

	// Check exits first (based on previous bar's position and levels), using
	// the current bar's high/low to approximate stop/limit execution.
	if (myPrevState === 1 && myPrevEntryPrice !== null) {
		const myStop = myPrevEntryPrice - myAtrValue[myIndex] * myAtrMult;
		const myTarget = myPrevEntryPrice + myAtrValue[myIndex] * myAtrMult * myRr;
		if (low[myIndex] <= myStop || high[myIndex] >= myTarget) {
			myExitLongSignal[myIndex] = true;
			myState = 0;
			myCurrentEntryPrice = null;
		}
	}
	else if (myPrevState === -1 && myPrevEntryPrice !== null) {
		const myStop = myPrevEntryPrice + myAtrValue[myIndex] * myAtrMult;
		const myTarget = myPrevEntryPrice - myAtrValue[myIndex] * myAtrMult * myRr;
		if (high[myIndex] >= myStop || low[myIndex] <= myTarget) {
			myExitShortSignal[myIndex] = true;
			myState = 0;
			myCurrentEntryPrice = null;
		}
	}

	// Entries, gated by position_size condition like Pine
	if (myLongConditionRaw[myIndex] && myState <= 0) {
		myLongEntrySignal[myIndex] = true;
		myState = 1;
		myCurrentEntryPrice = close[myIndex];
	}
	else if (myShortConditionRaw[myIndex] && myState >= 0) {
		myShortEntrySignal[myIndex] = true;
		myState = -1;
		myCurrentEntryPrice = close[myIndex];
	}

	myPositionState[myIndex] = myState;
	myEntryPrice[myIndex] = myCurrentEntryPrice;

	if (myState === 1 && myCurrentEntryPrice !== null) {
		myLongStopSeries[myIndex] = myCurrentEntryPrice - myAtrValue[myIndex] * myAtrMult;
		myLongTargetSeries[myIndex] = myCurrentEntryPrice + myAtrValue[myIndex] * myAtrMult * myRr;
	}
	if (myState === -1 && myCurrentEntryPrice !== null) {
		myShortStopSeries[myIndex] = myCurrentEntryPrice + myAtrValue[myIndex] * myAtrMult;
		myShortTargetSeries[myIndex] = myCurrentEntryPrice - myAtrValue[myIndex] * myAtrMult * myRr;
	}
}

// Visuals (matching Pine's plot of Fast/Slow EMA)
paint(myEmaFast, { name: 'Fast EMA', color: 'orange', thickness: 2 });
paint(myEmaSlow, { name: 'Slow EMA', color: 'blue', thickness: 2 });

// Risk management reference levels
paint(myLongStopSeries, { name: 'Long Stop', color: 'red', style: 'dotted' });
paint(myLongTargetSeries, { name: 'Long Target', color: 'green', style: 'dotted' });
paint(myShortStopSeries, { name: 'Short Stop', color: 'red', style: 'dotted' });
paint(myShortTargetSeries, { name: 'Short Target', color: 'green', style: 'dotted' });

// Signals mapped for Scanner, Alerts and Strategy Tester
register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myExitLongSignal, 'Exit Long');
register_signal(myExitShortSignal, 'Exit Short');
register_signal(myTrendBull, 'Trend Bullish');
register_signal(myTrendBear, 'Trend Bearish');
register_signal(myStrongBreadth, 'Strong Breadth');
register_signal(myWeakBreadth, 'Weak Breadth');