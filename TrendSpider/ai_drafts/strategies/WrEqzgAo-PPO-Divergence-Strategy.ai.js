describe_indicator('PPO Divergence', 'lower');

// --- Inputs ---
const myFastLen = input.number('Fast EMA Length', 12, { min: 1, max: 200 });
const mySlowLen = input.number('Slow EMA Length', 26, { min: 1, max: 400 });
const mySignalLen = input.number('Signal Length', 9, { min: 1, max: 200 });
const myPivotLen = input.number('Pivot Lookback', 5, { min: 2, max: 50 });

// Stop Loss / Take Profit % inputs are kept for reference only,
// since TrendSpider Custom JS indicators cannot place strategy
// orders (no strategy.entry/strategy.exit equivalent exists here).
const mySlPct = input.number('Stop Loss %', 2.0, { min: 0.1, max: 50 });
const myTpPct = input.number('Take Profit %', 4.0, { min: 0.1, max: 50 });

// --- PPO Calculation ---
const myFastEma = ema(close, myFastLen);
const mySlowEma = ema(close, mySlowLen);
const myPpo = mult(div(sub(myFastEma, mySlowEma), mySlowEma), 100);
const mySignal = ema(myPpo, mySignalLen);
const myHist = sub(myPpo, mySignal);

// --- Pivot Detection ---
const myPivotHighPrice = pivot_high(high, myPivotLen, myPivotLen);
const myPivotLowPrice = pivot_low(low, myPivotLen, myPivotLen);
const myPivotHighPpo = pivot_high(myPpo, myPivotLen, myPivotLen);
const myPivotLowPpo = pivot_low(myPpo, myPivotLen, myPivotLen);

// --- Track last two pivots for divergence (stateful loop, not an indicator call) ---
const myBullSignalSeries = series_of(false);
const myBearSignalSeries = series_of(false);

let myPrevPriceLow = null;
let myPrevPpoLow = null;
let myLastPriceLow = null;
let myLastPpoLow = null;
let myPrevPriceHigh = null;
let myPrevPpoHigh = null;
let myLastPriceHigh = null;
let myLastPpoHigh = null;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotLowPrice[myIndex] !== null) {
		myPrevPriceLow = myLastPriceLow;
		myPrevPpoLow = myLastPpoLow;
		myLastPriceLow = myPivotLowPrice[myIndex];
		myLastPpoLow = myPivotLowPpo[myIndex];
	}
	if (myPivotHighPrice[myIndex] !== null) {
		myPrevPriceHigh = myLastPriceHigh;
		myPrevPpoHigh = myLastPpoHigh;
		myLastPriceHigh = myPivotHighPrice[myIndex];
		myLastPpoHigh = myPivotHighPpo[myIndex];
	}

	const myBullDiv = myPrevPriceLow !== null && myPrevPpoLow !== null && myLastPriceLow !== null && myLastPpoLow !== null
		&& (myLastPriceLow < myPrevPriceLow) && (myLastPpoLow > myPrevPpoLow);

	const myBearDiv = myPrevPriceHigh !== null && myPrevPpoHigh !== null && myLastPriceHigh !== null && myLastPpoHigh !== null
		&& (myLastPriceHigh > myPrevPriceHigh) && (myLastPpoHigh < myPrevPpoHigh);

	myBullSignalSeries[myIndex] = myBullDiv && (myPivotLowPrice[myIndex] !== null);
	myBearSignalSeries[myIndex] = myBearDiv && (myPivotHighPrice[myIndex] !== null);
}

// --- Plot signals on chart ---
const myBullMarks = for_every(myBullSignalSeries, _b => _b ? constants.icons.triangle_up : null);
const myBearMarks = for_every(myBearSignalSeries, _b => _b ? constants.icons.triangle_down : null);

// Line/signal names must be alphanumeric only (no spaces or punctuation),
// and must be unique across paint()/register_signal()/paint_overlay() calls.
// Reusing "Bullish Divergence" / "Bearish Divergence" (with a space) for
// both a paint() call and a register_signal() call caused the engine to
// treat them as a name collision, which is why the error was raised.
paint(myBullMarks, { style: 'labels_below', color: 'green', name: 'BullishDivergenceMarker', forceUsePriceAxis: true });
paint(myBearMarks, { style: 'labels_above', color: 'red', name: 'BearishDivergenceMarker', forceUsePriceAxis: true });

// --- PPO Panel ---
paint(myPpo, { name: 'Ppo', color: '#3B82F6', thickness: 2, style: 'line' });
paint(mySignal, { name: 'Signal', color: '#F59E0B', thickness: 1, style: 'line' });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });

const myHistColor = for_every(myHist, _h => _h >= 0 ? 'teal' : 'red');
paint(myHist, { name: 'Hist', color: myHistColor, style: 'column' });

// --- Signals for scanners/alerts/backtests ---
register_signal(myBullSignalSeries, 'BullishDivergenceSignal');
register_signal(myBearSignalSeries, 'BearishDivergenceSignal');