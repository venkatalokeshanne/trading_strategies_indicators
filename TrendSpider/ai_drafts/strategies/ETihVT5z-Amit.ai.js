// EXPERIMENTAL CONVERSION — this is a best-effort translation of the
// Pine Script strategy logic into TrendSpider Custom JS. Some Pine
// constructs (strategy orders/exits, true "lookahead_on" security
// re-sampling, explicit "America/New_York" timezone binding) have no
// exact equivalent in this engine, so approximations were made (see
// comments below and the flagged notes). Treat this as a signal-only
// reproduction of the BUY/SELL/CHoCH logic, not a full strategy backtest.

describe_indicator('MNQ Inverse CHoCH Session Toggle', 'price');

const myUseSessionFilter = input.boolean('Use US Session Filter', true);
const mySwing = input.number('Swing Length', 2, { min: 1, max: 20 });
const mySlPoints = input.number('Stop Loss Points', 15, { min: 0.1, max: 1000 });
const myTpPoints = input.number('Take Profit Points', 15, { min: 0.1, max: 1000 });

// --- 5 minute EMA trend (approximation of request.security + [1] offset) ---
const my5mData = await request.history(current.ticker, '5');
assert(!my5mData.error, 'Error fetching 5m data: ' + my5mData.error);

const myEma20_5mRaw = ema(my5mData.close, 20);
const myEma50_5mRaw = ema(my5mData.close, 50);

// Pine uses ta.ema(...)[1] with lookahead_on, meaning "previous closed
// 5m bar value, available immediately on the current (lower timeframe) bar".
// We approximate this by shifting the 5m EMA by 1 bar, then landing it
// onto the current chart using the "le" (last available <= timestamp) method.
const myEma20_5mShifted = shift(myEma20_5mRaw, 1);
const myEma50_5mShifted = shift(myEma50_5mRaw, 1);

const myEma20Landed = land_points_onto_series(my5mData.time, myEma20_5mShifted, time, 'le');
const myEma50Landed = land_points_onto_series(my5mData.time, myEma50_5mShifted, time, 'le');

const myEma20_5m = interpolate_sparse_series(myEma20Landed, 'constant');
const myEma50_5m = interpolate_sparse_series(myEma50Landed, 'constant');

// --- 1 minute pivots ---
const myPivotHighSeries = pivot_high(high, mySwing, mySwing);
const myPivotLowSeries = pivot_low(low, mySwing, mySwing);

// --- Session filter (uses exchange timezone via time_of, approximating America/New_York) ---
const myAllowedSession = time.map(_t => {
	if (!myUseSessionFilter) return true;
	const myParsed = time_of(_t);
	const myMinutesOfDay = myParsed.hours * 60 + myParsed.minutes;
	const myMorning = myMinutesOfDay >= (9 * 60 + 30) && myMinutesOfDay <= (12 * 60);
	const myAfternoon = myMinutesOfDay >= (13 * 60 + 30) && myMinutesOfDay <= (16 * 60);
	return myMorning || myAfternoon;
});

// --- Stateful market structure / CHoCH / inverse CHoCH loop ---
const myBuySignal = series_of(false);
const mySellSignal = series_of(false);

let myLastSwingHigh = null;
let myLastSwingLow = null;
let myStructure = 0;

for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	if (myPivotHighSeries[myIndex] !== null && myPivotHighSeries[myIndex] !== undefined) {
		myLastSwingHigh = myPivotHighSeries[myIndex];
	}
	if (myPivotLowSeries[myIndex] !== null && myPivotLowSeries[myIndex] !== undefined) {
		myLastSwingLow = myPivotLowSeries[myIndex];
	}

	const myBreakHigh = myLastSwingHigh !== null && close[myIndex] > myLastSwingHigh;
	const myBreakLow = myLastSwingLow !== null && close[myIndex] < myLastSwingLow;

	if (myStructure === 0) {
		if (myBreakHigh) {
			myStructure = 1;
		}
		else if (myBreakLow) {
			myStructure = -1;
		}
	}

	const myBullishCHoCH = myBreakHigh && myStructure === -1;
	const myBearishCHoCH = myBreakLow && myStructure === 1;

	if (myBullishCHoCH) {
		myStructure = 1;
	}
	if (myBearishCHoCH) {
		myStructure = -1;
	}

	const myTrendBull = myEma20_5m[myIndex] > myEma50_5m[myIndex];
	const myTrendBear = myEma20_5m[myIndex] < myEma50_5m[myIndex];

	myBuySignal[myIndex] = myBearishCHoCH && myTrendBull && myAllowedSession[myIndex];
	mySellSignal[myIndex] = myBullishCHoCH && myTrendBear && myAllowedSession[myIndex];
}

// --- Register signals for scanners/alerts/strategy tester ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');

// Note: SL/TP (15/15 points) are strategy-management constructs, not
// expressible as paintable series here; they are informational only.
// myTpPoints / mySlPoints are exposed as inputs for downstream use in
// a Strategy Tester visual script, where entries/exits can reference them.

// --- Painting ---
paint(myEma20_5m, { name: 'EMA20 5m', color: '#4DA3FF', thickness: 1 });
paint(myEma50_5m, { name: 'EMA50 5m', color: '#EF5350', thickness: 1 });

const myBuyMarks = for_every(myBuySignal, close, (_buy, _c) => _buy ? _c : null);
const mySellMarks = for_every(mySellSignal, close, (_sell, _c) => _sell ? _c : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#EF5350' });