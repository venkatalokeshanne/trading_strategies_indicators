describe_indicator('Trend Persistence Analysis Framework', 'price');

// NOTE: TradingView's strategy.* engine (position sizing, equity,
// order fills) has no direct equivalent in TrendSpider Custom JS.
// This reproduces the Pine logic as closely as possible: trend
// detection, persistence counters, entry conditions, and a manual
// bar-by-bar simulation of position/stop/target to mirror
// strategy.position_avg_price based stops. Fills are approximated
// as "stop/target touched intrabar" using high/low, executed at the
// stop/target price (not necessarily matching Pine's exact fill model).

const myFastLen = input.number('Fast EMA', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA', 50, { min: 1, max: 500 });
const myMinTrendBars = input.number('Minimum Trend Duration', 10, { min: 1, max: 500 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrMult = input.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 20 });
const myRr = input.number('Risk Reward', 2.0, { min: 0.1, max: 20 });

const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);
const myAtrValue = atr(high, low, close, myAtrLen);

// Trend state
const myBullTrend = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f > _s);
const myBearTrend = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f < _s);

// Persistence counters (bars in a row trend has been true)
const myBullBars = for_every(myBullTrend, (_b, _prev) => _b ? (_prev || 0) + 1 : 0);
const myBearBars = for_every(myBearTrend, (_b, _prev) => _b ? (_prev || 0) + 1 : 0);

// Entry conditions
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	myLongCondition[myIndex] = myBullTrend[myIndex] && myBullBars[myIndex] >= myMinTrendBars;
	myShortCondition[myIndex] = myBearTrend[myIndex] && myBearBars[myIndex] >= myMinTrendBars;
}

// Manual simulation of position state, since strategy.* engine is
// not available in Custom JS. position: 0 = flat, 1 = long, -1 = short.
const myLongEntrySignal = series_of(false);
const myShortEntrySignal = series_of(false);
const myLongStopLine = series_of(null);
const myLongTargetLine = series_of(null);
const myShortStopLine = series_of(null);
const myShortTargetLine = series_of(null);

let myPosition = 0;
let myAvgPrice = null;
let myStop = null;
let myTarget = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myAtr = myAtrValue[myIndex];

	// check exits first (intrabar touch approximation)
	if (myPosition === 1 && myStop !== null) {
		if (low[myIndex] <= myStop || high[myIndex] >= myTarget) {
			myPosition = 0;
			myAvgPrice = null;
			myStop = null;
			myTarget = null;
		}
	}
	else if (myPosition === -1 && myStop !== null) {
		if (high[myIndex] >= myStop || low[myIndex] <= myTarget) {
			myPosition = 0;
			myAvgPrice = null;
			myStop = null;
			myTarget = null;
		}
	}

	// entries
	if (myLongCondition[myIndex] && myPosition <= 0) {
		myPosition = 1;
		myAvgPrice = close[myIndex];
		myStop = myAvgPrice - myAtr * myAtrMult;
		myTarget = myAvgPrice + myAtr * myAtrMult * myRr;
		myLongEntrySignal[myIndex] = true;
	}
	else if (myShortCondition[myIndex] && myPosition >= 0) {
		myPosition = -1;
		myAvgPrice = close[myIndex];
		myStop = myAvgPrice + myAtr * myAtrMult;
		myTarget = myAvgPrice - myAtr * myAtrMult * myRr;
		myShortEntrySignal[myIndex] = true;
	}

	if (myPosition === 1) {
		myLongStopLine[myIndex] = myStop;
		myLongTargetLine[myIndex] = myTarget;
	}
	else if (myPosition === -1) {
		myShortStopLine[myIndex] = myStop;
		myShortTargetLine[myIndex] = myTarget;
	}
}

paint(myFastEMA, { name: 'Fast EMA', color: 'orange', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: 'blue', thickness: 2 });

paint(myLongStopLine, { name: 'Long Stop', color: 'red', style: 'dotted' });
paint(myLongTargetLine, { name: 'Long Target', color: 'green', style: 'dotted' });
paint(myShortStopLine, { name: 'Short Stop', color: 'red', style: 'dotted' });
paint(myShortTargetLine, { name: 'Short Target', color: 'green', style: 'dotted' });

register_signal(myLongEntrySignal, 'Long Entry');
register_signal(myShortEntrySignal, 'Short Entry');
register_signal(myLongCondition, 'Long Condition');
register_signal(myShortCondition, 'Short Condition');