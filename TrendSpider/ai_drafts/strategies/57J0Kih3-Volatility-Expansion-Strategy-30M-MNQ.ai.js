describe_indicator('Volatility Expansion Strategy MNQ V7', 'price');

// NOTE: This is a best-effort translation of the Pine Script strategy
// into TrendSpider's indicator model. TrendSpider custom indicators
// cannot place real orders or track strategy.position_size natively,
// so position state (flat / long / short) is simulated manually with
// a loop that mirrors the Pine script's bar-by-bar state machine.
// Session filtering is approximated using time_of() (NY exchange time
// assumed via current.session), checking for Mon-Fri 09:30-16:00.

const myTab = input.tab('Settings');
const myVolLength = myTab.number('Lookback Period', 20, { min: 1, max: 500 });
const myCompThreshold = myTab.number('Compression Threshold', 0.95, { min: 0.01, max: 5, step: 0.01 });
const myExpTrigger = myTab.number('Expansion Trigger', 1.02, { min: 0.01, max: 5, step: 0.01 });
const myAtrMult = myTab.number('Risk Mult (ATR)', 1.5, { min: 0.01, max: 20, step: 0.1 });
const myRrRatio = myTab.number('Reward to Risk', 2.0, { min: 0.1, max: 20, step: 0.1 });
const myUseSession = myTab.boolean('Restrict to Session', false);

// --- Core calculations (vectorized, outside loops) ---
const myAtrValue = atr(high, low, close, myVolLength);
const myAvgAtr = sma(myAtrValue, myVolLength * 2);
const myVolRatio = for_every(myAtrValue, myAvgAtr, (_a, _avg) => _a / (_avg || 1));

const myIsCompressed = for_every(myVolRatio, _r => _r < myCompThreshold);
const myIsExpanding = for_every(myVolRatio, _r => _r > myExpTrigger);

// --- Session filter (approximation of Pine's time(..., session, "America/New_York")) ---
const myIsInSession = time.map(_t => {
	if (!myUseSession) return true;
	const myInfo = time_of(_t);
	// Pine session days "23456" = Mon..Fri (ISO dayOfWeek 1..5)
	const myIsWeekday = myInfo.dayOfWeek >= 1 && myInfo.dayOfWeek <= 5;
	const myMinutesOfDay = myInfo.hours * 60 + myInfo.minutes;
	const myStart = 9 * 60 + 30;
	const myEnd = 16 * 60;
	return myIsWeekday && myMinutesOfDay >= myStart && myMinutesOfDay < myEnd;
});

// --- Stateful simulation of breakout levels, position and signals ---
const myBreakoutHigh = series_of(null);
const myBreakoutLow = series_of(null);
const myLongSignal = series_of(false);
const myShortSignal = series_of(false);
const myExitSignal = series_of(false);
const myPositionState = series_of(0); // 0 flat, 1 long, -1 short

let myCurBreakoutHigh = null;
let myCurBreakoutLow = null;
let myCurPosition = 0;
let myEntryRisk = null;
let myEntryPrice = null;
let myStopPrice = null;
let myTargetPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myIsCompressed[myIndex]) {
		myCurBreakoutHigh = high[myIndex];
		myCurBreakoutLow = low[myIndex];
	}

	// Exit check first (based on previous bar's position)
	let myExitedThisBar = false;
	if (myCurPosition === 1) {
		if (low[myIndex] <= myStopPrice || high[myIndex] >= myTargetPrice) {
			myCurPosition = 0;
			myExitedThisBar = true;
		}
	}
	else if (myCurPosition === -1) {
		if (high[myIndex] >= myStopPrice || low[myIndex] <= myTargetPrice) {
			myCurPosition = 0;
			myExitedThisBar = true;
		}
	}

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;
	const myCrossoverHigh = myPrevClose !== null && myCurBreakoutHigh !== null &&
		myPrevClose <= myCurBreakoutHigh && close[myIndex] > myCurBreakoutHigh;
	const myCrossunderLow = myPrevClose !== null && myCurBreakoutLow !== null &&
		myPrevClose >= myCurBreakoutLow && close[myIndex] < myCurBreakoutLow;

	const myLong = myIsInSession[myIndex] && myIsExpanding[myIndex] && myCrossoverHigh && myCurPosition === 0;
	const myShort = myIsInSession[myIndex] && myIsExpanding[myIndex] && myCrossunderLow && myCurPosition === 0;

	if (myLong) {
		myEntryRisk = Math.max(myAtrValue[myIndex] * myAtrMult, 0);
		myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice - myEntryRisk;
		myTargetPrice = myEntryPrice + myEntryRisk * myRrRatio;
		myCurPosition = 1;
		myCurBreakoutHigh = null;
	}
	else if (myShort) {
		myEntryRisk = Math.max(myAtrValue[myIndex] * myAtrMult, 0);
		myEntryPrice = close[myIndex];
		myStopPrice = myEntryPrice + myEntryRisk;
		myTargetPrice = myEntryPrice - myEntryRisk * myRrRatio;
		myCurPosition = -1;
		myCurBreakoutLow = null;
	}

	myBreakoutHigh[myIndex] = myCurBreakoutHigh;
	myBreakoutLow[myIndex] = myCurBreakoutLow;
	myLongSignal[myIndex] = myLong;
	myShortSignal[myIndex] = myShort;
	myExitSignal[myIndex] = myExitedThisBar;
	myPositionState[myIndex] = myCurPosition;
}

// --- Visuals ---
paint(myBreakoutHigh, { name: 'BreakHigh', color: '#2ca599', thickness: 2, style: 'line' });
paint(myBreakoutLow, { name: 'BreakLow', color: '#b03a5b', thickness: 2, style: 'line' });

color_candles(for_every(myIsCompressed, _c => _c ? 'rgba(128,128,128,0.3)' : null));

// --- Signals for scanner / alerts / strategy tester ---
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myExitSignal, 'Exit');
register_signal(myIsCompressed, 'Volatility Compressed');
register_signal(myIsExpanding, 'Volatility Expanding');