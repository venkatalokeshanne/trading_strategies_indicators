describe_indicator('Bollinger Squeeze Breakout Plus Volume', 'price');

// ── INPUTS ─────────────────────────────────────────────
const bbTab = input.tab('Bollinger Bands');
const myBbLen = bbTab.number('BB Length', 20, { min: 1, max: 500 });
const myBbMult = bbTab.number('BB StdDev Multiplier', 2.0, { min: 0.1, max: 10, step: 0.1 });

const squeezeTab = input.tab('Squeeze');
const mySqueezeLen = squeezeTab.number('Squeeze Lookback', 50, { min: 1, max: 500 });
const mySqueezePct = squeezeTab.number('Squeeze Threshold', 0.8, { min: 0.01, max: 5, step: 0.05 });

const volumeTab = input.tab('Volume');
const myVolLen = volumeTab.number('Volume MA Length', 20, { min: 1, max: 500 });

const riskTab = input.tab('Risk');
const myAtrLen = riskTab.number('ATR Length', 14, { min: 1, max: 500 });
const mySlMult = riskTab.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myTpMult = riskTab.number('Target ATR Multiplier', 3.0, { min: 0.1, max: 10, step: 0.1 });

// ── BOLLINGER BANDS ─────────────────────────────────────
const myBbMid = sma(close, myBbLen);
const myBbDev = mult(stdev(close, myBbLen), myBbMult);
const myBbUpper = add(myBbMid, myBbDev);
const myBbLower = sub(myBbMid, myBbDev);
const myBbWidth = div(sub(myBbUpper, myBbLower), myBbMid);
const myAvgWidth = sma(myBbWidth, mySqueezeLen);
const myInSqueeze = for_every(myBbWidth, myAvgWidth, (_w, _avg) => _w < (_avg * mySqueezePct));

// previous bar squeeze state (ta.bb[1] equivalent)
const myWasSqueezed = shift(myInSqueeze, 1);

// ── VOLUME & VOLATILITY ─────────────────────────────────
const myVolMa = sma(volume, myVolLen);
const myVolPass = for_every(volume, myVolMa, (_v, _vma) => _v > _vma);
const myAtrVal = atr(high, low, close, myAtrLen);

// crossover / crossunder helpers (close vs band)
const myCloseAboveUpper = for_every(close, myBbUpper, (_c, _u) => _c > _u);
const myCloseBelowLower = for_every(close, myBbLower, (_c, _l) => _c < _l);

// ── SIMULATE POSITION STATE (strategy.position_size == 0) ──
// We emulate Pine's single-position strategy engine: only one
// position (long or short) can be open at a time; it is closed
// when price hits its ATR-based stop or target (checked using
// the bar's high/low, worst-case stop-first assumption).
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);
let myPositionState = 0; // 0 = flat, 1 = long, -1 = short
let myStopLevel = null;
let myTargetLevel = null;

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	// manage existing position exits first (using this bar's range)
	if (myPositionState === 1) {
		if (low[myIndex] <= myStopLevel || high[myIndex] >= myTargetLevel) {
			myPositionState = 0;
			myStopLevel = null;
			myTargetLevel = null;
		}
	}
	else if (myPositionState === -1) {
		if (high[myIndex] >= myStopLevel || low[myIndex] <= myTargetLevel) {
			myPositionState = 0;
			myStopLevel = null;
			myTargetLevel = null;
		}
	}

	const myCrossoverUp = myCloseAboveUpper[myIndex] && !myCloseAboveUpper[myIndex - 1];
	const myCrossunderDown = myCloseBelowLower[myIndex] && !myCloseBelowLower[myIndex - 1];

	const myLong = myWasSqueezed[myIndex] && myCrossoverUp && myVolPass[myIndex] && myPositionState === 0;
	const myShort = myWasSqueezed[myIndex] && myCrossunderDown && myVolPass[myIndex] && myPositionState === 0;

	myLongCondition[myIndex] = myLong;
	myShortCondition[myIndex] = myShort;

	if (myLong) {
		myPositionState = 1;
		myStopLevel = close[myIndex] - myAtrVal[myIndex] * mySlMult;
		myTargetLevel = close[myIndex] + myAtrVal[myIndex] * myTpMult;
	}
	else if (myShort) {
		myPositionState = -1;
		myStopLevel = close[myIndex] + myAtrVal[myIndex] * mySlMult;
		myTargetLevel = close[myIndex] - myAtrVal[myIndex] * myTpMult;
	}
}

// ── VISUALS ──────────────────────────────────────────────
const myUpperPainted = paint(myBbUpper, { name: 'Upper Band', color: 'gray', thickness: 1 });
const myLowerPainted = paint(myBbLower, { name: 'Lower Band', color: 'gray', thickness: 1 });
paint(myBbMid, { name: 'Basis', color: 'silver', style: 'dotted', thickness: 1 });
fill(myUpperPainted, myLowerPainted, 'gold', 0.08);

const myLongMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Squeeze Breakout Long Marker', style: 'labels_below', color: 'green', thickness: 3 });
paint(myShortMarks, { name: 'Squeeze Breakout Short Marker', style: 'labels_above', color: 'red', thickness: 3 });

// ── SIGNALS (for scanners, alerts, strategy tester) ──────
// Renamed signals so they don't collide with the painted line
// names above (names must be unique across all outputs,
// including both paint() and register_signal() calls).
register_signal(myLongCondition, 'Squeeze Breakout Long Signal');
register_signal(myShortCondition, 'Squeeze Breakout Short Signal');
register_signal(myInSqueeze, 'In Squeeze Signal');