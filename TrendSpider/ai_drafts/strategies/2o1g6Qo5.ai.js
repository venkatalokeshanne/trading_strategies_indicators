describe_indicator('MACD Trend Enhanced Strategy', 'price');

// --- Inputs ---
const myFastLength = input.number('MACD Fast Length', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow Length', 26, { min: 1, max: 400 });
const mySignalSmoothing = input.number('Signal Smoothing', 9, { min: 1, max: 200 });

const myStopLossPerc = input.number('Initial Stop Loss (%)', 2.0, { min: 0.1, max: 100 }) / 100;
const myBeTriggerPerc = input.number('Breakeven Trigger (%)', 1.5, { min: 0.1, max: 100 }) / 100;
const myTrailOffsetPerc = input.number('Trailing Stop Offset (%)', 1.0, { min: 0.1, max: 100 }) / 100;

const mySrc = close;

// --- MACD calculation (matches Pine ta.macd) ---
const myFastMA = ema(mySrc, myFastLength);
const mySlowMA = ema(mySrc, mySlowLength);
const myMacdLine = sub(myFastMA, mySlowMA);
const mySignalLine = ema(myMacdLine, mySignalSmoothing);

// --- Crossover / Crossunder detection ---
const myGoldCross = series_of(false);
const myDeathCross = series_of(false);

for (let myIndex = 1; myIndex < close.length; myIndex += 1) {
	const myPrevDiff = myMacdLine[myIndex - 1] - mySignalLine[myIndex - 1];
	const myCurrDiff = myMacdLine[myIndex] - mySignalLine[myIndex];

	myGoldCross[myIndex] = myPrevDiff <= 0 && myCurrDiff > 0;
	myDeathCross[myIndex] = myPrevDiff >= 0 && myCurrDiff < 0;
}

// --- Strategy state simulation (position, entry price, breakeven, trailing stop) ---
const myHighest5 = highest(high, 5);

const myEntrySignal = series_of(false);
const myExitSignal = series_of(false);
const myEntryLine = series_of(null);
const myExitReasonSL = series_of(false);
const myExitReasonTrend = series_of(false);

let myPositionOpen = false;
let myEntryPrice = 0;
let myReachedBe = false;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	// Entry: gold cross while flat
	if (myGoldCross[myIndex] && !myPositionOpen) {
		myPositionOpen = true;
		myEntryPrice = close[myIndex];
		myReachedBe = false;
		myEntrySignal[myIndex] = true;
	}

	if (myPositionOpen) {
		const myInitialSl = myEntryPrice * (1 - myStopLossPerc);

		if (high[myIndex] >= myEntryPrice * (1 + myBeTriggerPerc)) {
			myReachedBe = true;
		}

		const myCurrentSl = myReachedBe ? myEntryPrice : myInitialSl;
		const myTrailingSl = (myHighest5[myIndex] != null ? myHighest5[myIndex] : high[myIndex]) * (1 - myTrailOffsetPerc);
		const myFinalSl = Math.max(myCurrentSl, myTrailingSl);

		const myStopHit = low[myIndex] <= myFinalSl;
		const myTrendExit = myDeathCross[myIndex];

		if (myStopHit || myTrendExit) {
			myExitSignal[myIndex] = true;
			myExitReasonSL[myIndex] = myStopHit;
			myExitReasonTrend[myIndex] = !myStopHit && myTrendExit;
			myPositionOpen = false;
			myReachedBe = false;
		}

		myEntryLine[myIndex] = myEntryPrice;
	}
}

// --- Shapes for entries and exits ---
const myGoldCrossMarks = for_every(myGoldCross, _g => _g ? constants.icons.triangle_up : null);
const myDeathCrossMarks = for_every(myDeathCross, _d => _d ? constants.icons.triangle_down : null);

paint(myGoldCrossMarks, { style: 'labels_below', color: 'green', name: 'Gold Cross Entry' });
paint(myDeathCrossMarks, { style: 'labels_above', color: 'red', name: 'Death Cross Exit' });

// Entry line, drawn as a broken line like Pine's plot.style_linebr
paint(myEntryLine, { style: 'line', color: 'gray', name: 'Entry Line' });

// --- Register signals for scanners, alerts and strategy tester ---
register_signal(myEntrySignal, 'Long Entry Signal');
register_signal(myExitSignal, 'Exit Signal');
register_signal(myExitReasonSL, 'Exit By Stop Loss');
register_signal(myExitReasonTrend, 'Exit By Trend Reversal');
register_signal(myGoldCross, 'MACD Gold Cross');
register_signal(myDeathCross, 'MACD Death Cross');