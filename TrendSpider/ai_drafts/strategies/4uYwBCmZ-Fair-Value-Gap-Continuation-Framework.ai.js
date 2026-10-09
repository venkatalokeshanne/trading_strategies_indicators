describe_indicator('Fair Value Gap Continuation Framework', 'price');

// ── Inputs ──────────────────────────────────────────────────────────
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 10 });
const myRiskReward = input.number('Risk Reward', 2.0, { min: 0.1, max: 20 });
const myTrendLen = input.number('Trend EMA Length', 50, { min: 1, max: 500 });

// ── Trend filter and volatility ────────────────────────────────────
const myEmaTrend = ema(close, myTrendLen);
const myAtrValue = atr(high, low, close, myAtrLen);

// Pine's "high[2]" / "low[2]" are values 2 bars back
const myHighShift2 = shift(high, 2);
const myLowShift2 = shift(low, 2);

// Fair Value Gap raw conditions
const myBullFvgRaw = for_every(low, myHighShift2, (_l, _h2) => _l > _h2);
const myBearFvgRaw = for_every(high, myLowShift2, (_h, _l2) => _h < _l2);

// ── Stateful "var float" zones: carried forward until re-assigned ──
// This requires sequential bar-by-bar logic (cannot use indicator
// calls inside the loop, only plain array math), so we use a plain
// for loop over already-computed series.
const myBullTop = series_of(null);
const myBullBottom = series_of(null);
const myBearTop = series_of(null);
const myBearBottom = series_of(null);

const myBullRetest = series_of(false);
const myBearRetest = series_of(false);
const myLongCondition = series_of(false);
const myShortCondition = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myPrevBullTop = myIndex > 0 ? myBullTop[myIndex - 1] : null;
	const myPrevBullBottom = myIndex > 0 ? myBullBottom[myIndex - 1] : null;
	const myPrevBearTop = myIndex > 0 ? myBearTop[myIndex - 1] : null;
	const myPrevBearBottom = myIndex > 0 ? myBearBottom[myIndex - 1] : null;

	let myCurBullTop = myPrevBullTop;
	let myCurBullBottom = myPrevBullBottom;
	let myCurBearTop = myPrevBearTop;
	let myCurBearBottom = myPrevBearBottom;

	if (myBullFvgRaw[myIndex] && myIndex >= 2) {
		myCurBullTop = low[myIndex];
		myCurBullBottom = myHighShift2[myIndex];
	}

	if (myBearFvgRaw[myIndex] && myIndex >= 2) {
		myCurBearTop = myLowShift2[myIndex];
		myCurBearBottom = high[myIndex];
	}

	myBullTop[myIndex] = myCurBullTop;
	myBullBottom[myIndex] = myCurBullBottom;
	myBearTop[myIndex] = myCurBearTop;
	myBearBottom[myIndex] = myCurBearBottom;

	// Retest logic (uses the just-updated zone values, same bar)
	const myBullRetestValue = myCurBullTop !== null && myCurBullTop !== undefined &&
		low[myIndex] <= myCurBullTop && close[myIndex] > myCurBullTop;

	const myBearRetestValue = myCurBearBottom !== null && myCurBearBottom !== undefined &&
		high[myIndex] >= myCurBearBottom && close[myIndex] < myCurBearBottom;

	myBullRetest[myIndex] = myBullRetestValue;
	myBearRetest[myIndex] = myBearRetestValue;

	myLongCondition[myIndex] = myBullRetestValue && close[myIndex] > myEmaTrend[myIndex];
	myShortCondition[myIndex] = myBearRetestValue && close[myIndex] < myEmaTrend[myIndex];
}

// ── Suggested protective levels (reference only, not an executed
// strategy backtest - see notes below) ─────────────────────────────
const myLongStop = sub(close, mult(myAtrValue, myAtrMult));
const myLongTarget = add(close, mult(myAtrValue, myAtrMult, myRiskReward));
const myShortStop = add(close, mult(myAtrValue, myAtrMult));
const myShortTarget = sub(close, mult(myAtrValue, myAtrMult, myRiskReward));

// ── Visuals ─────────────────────────────────────────────────────────
paint(myEmaTrend, { name: 'TrendEMA', color: '#FF9800', thickness: 2 });
paint(myBullTop, { name: 'BullishFVG', color: '#26A69A', thickness: 2, style: 'line' });
paint(myBearBottom, { name: 'BearishFVG', color: '#EF5350', thickness: 2, style: 'line' });

// Reference-only risk levels, hidden by default via thin dotted lines
paint(myLongStop, { name: 'LongStopRef', color: '#B0BEC5', thickness: 1, style: 'dotted' });
paint(myLongTarget, { name: 'LongTargetRef', color: '#B0BEC5', thickness: 1, style: 'dotted' });
paint(myShortStop, { name: 'ShortStopRef', color: '#B0BEC5', thickness: 1, style: 'dotted' });
paint(myShortTarget, { name: 'ShortTargetRef', color: '#B0BEC5', thickness: 1, style: 'dotted' });

// ── Scanner / Alert / Strategy signals ──────────────────────────────
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myBullRetest, 'Bullish FVG Retest');
register_signal(myBearRetest, 'Bearish FVG Retest');