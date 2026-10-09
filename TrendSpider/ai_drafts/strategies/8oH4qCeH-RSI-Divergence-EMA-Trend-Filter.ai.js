describe_indicator('RSI Divergence plus EMA Trend Filter', 'lower');

// ── INPUTS ─────────────────────────────────────────────
const rsiTab = input.tab('RSI');
const myRsiLength = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });

const divTab = input.tab('Divergence');
const myPivotLookback = divTab.number('Pivot Lookback', 5, { min: 2, max: 100 });

const trendTab = input.tab('Trend Filter');
const myEmaLength = trendTab.number('EMA Length', 200, { min: 1, max: 1000 });

const riskTab = input.tab('Risk');
const myAtrLength = riskTab.number('ATR Length', 14, { min: 1, max: 200 });
const myStopMultiplier = riskTab.number('SL ATR Multiplier', 1.5, { min: 0.1, max: 20 });
const myTakeProfitMultiplier = riskTab.number('TP ATR Multiplier', 3.0, { min: 0.1, max: 20 });

// ── INDICATORS ──────────────────────────────────────────
const myRsiValues = rsi(close, myRsiLength);
const myEmaValues = ema(close, myEmaLength);
const myAtrValues = atr(high, low, close, myAtrLength);

// ── PIVOT DETECTION ─────────────────────────────────────
// pivot_high/pivot_low use leftLength/rightLength like Pine's pivothigh/pivotlow
const myPivotHigh = pivot_high(high, myPivotLookback, myPivotLookback);
const myPivotLow = pivot_low(low, myPivotLookback, myPivotLookback);

// ── RSI AT PIVOTS (equivalent of ta.valuewhen) ───────────
// We walk the series once, tracking the current and previous pivot
// occurrence's RSI value and pivot price, mirroring valuewhen(cond, src, 0/1)
const myRsiAtHigh = series_of(null);
const myPrevRsiAtHigh = series_of(null);
const myPrevPivotHighPrice = series_of(null);

const myRsiAtLow = series_of(null);
const myPrevRsiAtLow = series_of(null);
const myPrevPivotLowPrice = series_of(null);

let myLastHighRsi = null;
let myLastHighPrice = null;
let myPrevHighRsi = null;
let myPrevHighPrice = null;

let myLastLowRsi = null;
let myLastLowPrice = null;
let myPrevLowRsi = null;
let myPrevLowPrice = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined) {
		myPrevHighRsi = myLastHighRsi;
		myPrevHighPrice = myLastHighPrice;
		myLastHighRsi = myRsiValues[myIndex];
		myLastHighPrice = myPivotHigh[myIndex];
	}

	if (myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined) {
		myPrevLowRsi = myLastLowRsi;
		myPrevLowPrice = myLastLowPrice;
		myLastLowRsi = myRsiValues[myIndex];
		myLastLowPrice = myPivotLow[myIndex];
	}

	myRsiAtHigh[myIndex] = myLastHighRsi;
	myPrevRsiAtHigh[myIndex] = myPrevHighRsi;
	myPrevPivotHighPrice[myIndex] = myPrevHighPrice;

	myRsiAtLow[myIndex] = myLastLowRsi;
	myPrevRsiAtLow[myIndex] = myPrevLowRsi;
	myPrevPivotLowPrice[myIndex] = myPrevLowPrice;
}

// ── DIVERGENCE DETECTION ────────────────────────────────
const myBearishDivergence = series_of(false);
const myBullishDivergence = series_of(false);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myHasPivotHigh = myPivotHigh[myIndex] !== null && myPivotHigh[myIndex] !== undefined;
	const myHasPivotLow = myPivotLow[myIndex] !== null && myPivotLow[myIndex] !== undefined;

	myBearishDivergence[myIndex] = Boolean(
		myHasPivotHigh &&
		myPrevPivotHighPrice[myIndex] !== null &&
		high[myIndex] > myPrevPivotHighPrice[myIndex] &&
		myRsiAtHigh[myIndex] !== null && myPrevRsiAtHigh[myIndex] !== null &&
		myRsiAtHigh[myIndex] < myPrevRsiAtHigh[myIndex]
	);

	myBullishDivergence[myIndex] = Boolean(
		myHasPivotLow &&
		myPrevPivotLowPrice[myIndex] !== null &&
		low[myIndex] < myPrevPivotLowPrice[myIndex] &&
		myRsiAtLow[myIndex] !== null && myPrevRsiAtLow[myIndex] !== null &&
		myRsiAtLow[myIndex] > myPrevRsiAtLow[myIndex]
	);
}

// ── TREND FILTER ────────────────────────────────────────
const myAboveEma = for_every(close, myEmaValues, (_close, _ema) => _close > _ema);
const myBelowEma = for_every(close, myEmaValues, (_close, _ema) => _close < _ema);

// ── ENTRY CONDITIONS ────────────────────────────────────
// Note: "strategy.position_size == 0" (no open position) cannot be reproduced
// here since this is an indicator, not a backtested strategy with position
// state. We reproduce the signal-generation logic only (divergence + trend
// filter + confirmed bar), without the "flat position" gating.
const myLongCondition = for_every(myBullishDivergence, myAboveEma, (_bull, _above) => _bull && _above);
const myShortCondition = for_every(myBearishDivergence, myBelowEma, (_bear, _below) => _bear && _below);

// Suggested stop/target levels, for reference only (not executed as trades)
const myLongStopLevel = series_of(null);
const myLongTargetLevel = series_of(null);
const myShortStopLevel = series_of(null);
const myShortTargetLevel = series_of(null);

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myLowShifted = myIndex - myPivotLookback >= 0 ? low[myIndex - myPivotLookback] : null;
	const myHighShifted = myIndex - myPivotLookback >= 0 ? high[myIndex - myPivotLookback] : null;

	if (myLongCondition[myIndex] && myLowShifted !== null) {
		myLongStopLevel[myIndex] = myLowShifted - myAtrValues[myIndex] * myStopMultiplier;
		myLongTargetLevel[myIndex] = close[myIndex] + myAtrValues[myIndex] * myTakeProfitMultiplier;
	}

	if (myShortCondition[myIndex] && myHighShifted !== null) {
		myShortStopLevel[myIndex] = myHighShifted + myAtrValues[myIndex] * myStopMultiplier;
		myShortTargetLevel[myIndex] = close[myIndex] - myAtrValues[myIndex] * myTakeProfitMultiplier;
	}
}

// ── VISUALS ─────────────────────────────────────────────
paint(myEmaValues, { name: 'EMA Trend Filter', color: '#2f6fed', thickness: 1, forceUsePriceAxis: true });

paint(myRsiValues, { name: 'RSI', color: '#9b59b6', thickness: 1 });
paint(horizontal_line(70), { name: 'Overbought', color: '#e74c3c', style: 'dotted' });
paint(horizontal_line(30), { name: 'Oversold', color: '#2ecc71', style: 'dotted' });
paint(horizontal_line(50), { name: 'Midline', color: '#95a5a6', style: 'dotted' });

const myBullMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const myBearMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myBullMarks, { name: 'Bull Divergence', style: 'labels_below', color: 'green', forceUsePriceAxis: true });
paint(myBearMarks, { name: 'Bear Divergence', style: 'labels_above', color: 'red', forceUsePriceAxis: true });

// ── SIGNALS (for scanners / alerts / strategy tester) ────
register_signal(myLongCondition, 'Bullish Divergence Long Entry');
register_signal(myShortCondition, 'Bearish Divergence Short Entry');