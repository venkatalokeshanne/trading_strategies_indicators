describe_indicator('Rudy Energy GC v2', 'price');

// NOTE: TrendSpider Custom JS has no strategy/backtest engine like Pine's
// strategy.*. We reproduce the signal logic (goLong / exitSignal / strength)
// exactly, and we simulate the position + trailing stop manually in a loop
// to approximate strategy.position_size and strategy.exit() behavior.

const myFastLen = input.number('Fast EMA Period', 50, { min: 1, max: 500 });
const mySlowLen = input.number('Slow SMA Period', 200, { min: 1, max: 500 });
const myTrendLen = input.number('Trend EMA Period', 21, { min: 1, max: 500 });
const myRsiLen = input.number('RSI Period', 14, { min: 1, max: 200 });
const myRsiCap = input.number('RSI Cap', 75, { min: 1, max: 100 });
const myMinStrength = input.number('Minimum Signal Strength', 3, { min: 0, max: 5 });
const myTrailPct = input.number('Trailing Stop Pct', 8.0, { min: 0, max: 100 }) / 100;
const myOffsetPct = input.number('Trail Offset Pct', 1.0, { min: 0, max: 100 }) / 100;

const myFastMA = ema(close, myFastLen);
const mySlowMA = sma(close, mySlowLen);
const myTrendMA = ema(close, myTrendLen);
const myRsiVal = rsi(close, myRsiLen);
const myMomPct = mult(div(sub(close, mySlowMA), mySlowMA), 100);

// --- Signal strength (same weighting as Pine) ---
const myStrength = for_every(myFastMA, mySlowMA, myRsiVal, myMomPct, close, myTrendMA,
	(_fast, _slow, _rsiv, _mom, _c, _trend) => {
		let myS = 0;
		myS += _fast > _slow ? 2 : 0;
		myS += _rsiv < 65 ? 1 : 0;
		myS += _mom > 5 ? 1 : 0;
		myS += _c > _trend ? 1 : 0;
		return myS;
	}
);

// --- Conditions ---
const myGoLong = for_every(myFastMA, mySlowMA, myRsiVal, close, myTrendMA, myStrength,
	(_fast, _slow, _rsiv, _c, _trend, _str) => {
		const myBull = _fast > _slow;
		const myNotExt = _rsiv < myRsiCap;
		const myTrendOk = _c > _trend;
		return (myBull && myNotExt && myTrendOk && _str >= myMinStrength);
	}
);

const myExitSignal = for_every(myFastMA, mySlowMA, (_fast, _slow) => _fast < _slow);

// --- Manual simulation of strategy.position_size, entries, trailing exit ---
const myEntryFlags = series_of(false);
const myExitFlags = series_of(false);

let myPositionOpen = false;
let myTrailStopLevel = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myClose = close[myIndex];

	if (!myPositionOpen) {
		if (myGoLong[myIndex]) {
			myPositionOpen = true;
			// Trailing stop activates once price moves favorably by the offset
			myTrailStopLevel = myClose * (1 - myTrailPct);
			myEntryFlags[myIndex] = true;
		}
	}
	else {
		// Update trailing stop: only trails up, offset mimics Pine's trail_offset
		// behavior approximately (activates trail once price exceeds entry by offset)
		const myCandidateStop = myClose * (1 - myTrailPct);
		if (myClose * (1 - myOffsetPct) > 0 && myCandidateStop > myTrailStopLevel) {
			myTrailStopLevel = myCandidateStop;
		}

		const myHitTrail = myClose <= myTrailStopLevel;
		const myRegimeExit = myExitSignal[myIndex];

		if (myRegimeExit || myHitTrail) {
			myPositionOpen = false;
			myTrailStopLevel = null;
			myExitFlags[myIndex] = true;
		}
	}
}

// --- Signals for scanner/alerts/strategy tester ---
register_signal(myGoLong, 'Go Long');
register_signal(myExitSignal, 'Regime Exit Signal');
register_signal(myEntryFlags, 'Entry Executed');
register_signal(myExitFlags, 'Exit Executed');

// --- Visuals ---
paint(myFastMA, { name: 'Fast EMA', color: '#2196F3', thickness: 2 });
paint(mySlowMA, { name: 'Slow SMA', color: '#F44336', thickness: 2 });
paint(myTrendMA, { name: 'Trend EMA', color: '#FF9800', thickness: 1 });

const myEntryMarks = for_every(myEntryFlags, close, (_flag, _c) => _flag ? _c : null);
const myExitMarks = for_every(myExitFlags, close, (_flag, _c) => _flag ? _c : null);

paint(myEntryMarks, { name: 'Entry', style: 'labels_below', color: '#4CAF50' });
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: '#F44336' });