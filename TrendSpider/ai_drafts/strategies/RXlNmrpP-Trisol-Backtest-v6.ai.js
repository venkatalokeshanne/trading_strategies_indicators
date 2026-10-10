// NOTE: TrendSpider Custom JS API has no strategy engine (no
// strategy.entry/exit/order, no position sizing or P&L tracking).
// This script reproduces the Pine Script's INDICATOR logic (HMA,
// MACD, RSI, pivot low, target, entry condition) exactly using
// built-in functions, and then approximates the position/partial
// exit/re-entry state machine with a sequential simulation so the
// entry, partial-exit and re-entry events can be used as scanner
// and alert signals. There is no real backtest, equity curve or
// commission handling here.

describe_indicator('Triple Confirmation System Weekly', 'price');

const myTab1 = input.tab('HMA / MACD / RSI');
const myHmaRow = myTab1.row();
const myHmaLen1 = myHmaRow.number('HMA Length 1', 30, { min: 1, max: 500 });
const myHmaLen2 = myHmaRow.number('HMA Length 2', 44, { min: 1, max: 500 });

const myMacdRow = myTab1.row();
const myMacdFast = myMacdRow.number('MACD Fast', 21, { min: 1, max: 500 });
const myMacdSlow = myMacdRow.number('MACD Slow', 3, { min: 1, max: 500 });
const myMacdSig = myMacdRow.number('MACD Signal', 9, { min: 1, max: 500 });

const myRsiRow = myTab1.row();
const myRsiLen = myRsiRow.number('RSI Length', 9, { min: 1, max: 500 });
const myRsiMaLen = myRsiRow.number('RSI MA Length', 3, { min: 1, max: 500 });
const myRsiWmaLen = myRsiRow.number('RSI WMA Length', 21, { min: 1, max: 500 });

const myTab2 = input.tab('Stop / Target');
const mySwingRow = myTab2.row();
const mySwingLeft = mySwingRow.number('Swing Low Left Bars', 2, { min: 1, max: 100 });
const mySwingRight = mySwingRow.number('Swing Low Right Bars', 2, { min: 1, max: 100 });
const myTargetLookback = myTab2.number('Target HH Lookback', 26, { min: 1, max: 500 });

const myTab3 = input.tab('Partial Exit / Re-entry');
const myPartialRow = myTab3.row();
// Shortened input names below, since the platform rejects
// input() names which are too lengthy.
const myPartialPct = myPartialRow.number('Partial Exit Pct', 20, { min: 0, max: 100 });
const myPartialDailyUp = myPartialRow.number('Partial Trigger Up Pct', 3, { min: 0.1, max: 100 });
const myReentryRow = myTab3.row();
const myReentryPct = myReentryRow.number('Re entry Pct', 10, { min: 0, max: 100 });
const myReentryDailyDown = myReentryRow.number('Reentry Trigger Down Pct', 3, { min: 0.1, max: 100 });

// --- Weekly indicators (assumes this runs on a Weekly chart, as in the Pine script) ---
const myHma1 = hullma(close, myHmaLen1);
const myHma2 = hullma(close, myHmaLen2);

const myMacdFastEma = ema(close, myMacdFast);
const myMacdSlowEma = ema(close, myMacdSlow);
const myMacdLine = sub(myMacdFastEma, myMacdSlowEma);
const myMacdSigLine = ema(myMacdLine, myMacdSig);
const myMacdHist = sub(myMacdLine, myMacdSigLine);

const myRsi9 = rsi(close, myRsiLen);
const myRsiMa3 = sma(myRsi9, myRsiMaLen);
const myRsiWma21 = wma(myRsi9, myRsiWmaLen);

// --- Entry condition (all 3 confirmations) ---
const myUpperHma = max_of(myHma1, myHma2);
const myLowerHma = min_of(myHma1, myHma2);
const myPriceBetween = for_every(close, myLowerHma, myUpperHma, (_c, _l, _u) => _c >= _l && _c <= _u);
const myMacdBelowZero = for_every(myMacdHist, _h => _h < 0);

const myRsiCross1 = for_every(myRsi9, myRsiWma21, (_r, _w, _prev, _i) => {
	if (_i < 1) return false;
	return myRsi9[_i - 1] <= myRsiWma21[_i - 1] && _r > _w;
});

const myRsiCross2 = for_every(myRsiMa3, myRsiWma21, (_r, _w, _prev, _i) => {
	if (_i < 1) return false;
	return myRsiMa3[_i - 1] <= myRsiWma21[_i - 1] && _r > _w;
});

const myEntrySignal = for_every(myPriceBetween, myMacdBelowZero, myRsiCross1, myRsiCross2,
	(_pb, _mz, _c1, _c2) => _pb && _mz && _c1 && _c2);

// --- Stop: last confirmed weekly pivot low (forward-filled, no repaint) ---
const myPivLow = pivot_low(low, mySwingLeft, mySwingRight);
const myStopPrice = interpolate_sparse_series(myPivLow, 'constant');

// --- Target: highest high of last N weeks, excluding the current bar ---
const myTargetPrice = highest(shift(high, 1), myTargetLookback);

// --- Daily % change, approximated/landed onto the weekly series (constant forward fill) ---
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, 'Error fetching daily data: ' + myDailyData.error);

const myDailyChangePct = for_every(myDailyData.close, (_c, _prev, _i) => {
	if (_i < 1) return null;
	const myPrevClose = myDailyData.close[_i - 1];
	return myPrevClose ? 100 * (_c - myPrevClose) / myPrevClose : null;
});

const myDailyChangeLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyChangePct, time, 'le'),
	'constant'
);

// --- Sequential simulation of position / partial exit / re-entry state ---
// This replaces strategy.entry/exit/order, which do not exist in this API.
const myCandleCount = close.length;
const myEntryMarker = series_of(null);
const myPartialMarker = series_of(null);
const myReentryMarker = series_of(null);
const myStopLine = series_of(null);
const myTargetLine = series_of(null);

let myPositionOpen = false;
let myInitQty = null;
let myPartialDone = false;
let myReentryDone = false;

for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (!myPositionOpen) {
		myInitQty = null;
		myPartialDone = false;
		myReentryDone = false;
	}

	let myDidEnter = false;
	if (myEntrySignal[myIndex] && !myPositionOpen && myStopPrice[myIndex] != null && myTargetPrice[myIndex] != null) {
		myPositionOpen = true;
		myInitQty = 100;
		myDidEnter = true;
	}
	myEntryMarker[myIndex] = myDidEnter ? close[myIndex] : null;

	if (myPositionOpen && myInitQty == null) {
		myInitQty = 100;
	}

	let myDidPartial = false;
	const myDailyChange = myDailyChangeLanded[myIndex];
	if (myPositionOpen && !myPartialDone && myInitQty != null && myDailyChange != null && myDailyChange >= myPartialDailyUp) {
		myPartialDone = true;
		myReentryDone = false;
		myDidPartial = true;
	}
	myPartialMarker[myIndex] = myDidPartial ? close[myIndex] : null;

	let myDidReentry = false;
	if (myPositionOpen && myPartialDone && !myReentryDone && myInitQty != null && myDailyChange != null && myDailyChange <= -myReentryDailyDown) {
		myReentryDone = true;
		myDidReentry = true;
	}
	myReentryMarker[myIndex] = myDidReentry ? close[myIndex] : null;

	if (myPositionOpen && myStopPrice[myIndex] != null && myTargetPrice[myIndex] != null) {
		if (low[myIndex] <= myStopPrice[myIndex] || high[myIndex] >= myTargetPrice[myIndex]) {
			myPositionOpen = false;
		}
	}

	myStopLine[myIndex] = myPositionOpen ? myStopPrice[myIndex] : null;
	myTargetLine[myIndex] = myPositionOpen ? myTargetPrice[myIndex] : null;
}

// --- Painting ---
paint(myHma1, { name: 'HMA30', color: '#2962FF', thickness: 2 });
paint(myHma2, { name: 'HMA44', color: '#EF5350', thickness: 2 });

paint(myStopLine, { name: 'StopSwingLow', color: '#FF9800', style: 'ladder', thickness: 1 });
paint(myTargetLine, { name: 'TargetPrevHigh', color: '#009688', style: 'ladder', thickness: 1 });

// paint_label_at_line() does not support labels_above/labels_below
// lines, so the entry marker is also painted as a plain "line" style
// series (sparse, mostly null) purely to attach the ENTRY label to it.
// The labels_below marker below remains for the visual arrow-style marker.
const myEntryLinePainted = paint(myEntryMarker, { name: 'EntryLevel', style: 'line', color: '#4CAF50', thickness: 1 });
paint_label_at_line(myEntryLinePainted, myCandleCount - 1, 'ENTRY', { color: 'white', background_color: '#4CAF50' });

paint(myEntryMarker, { name: 'EntryMarker', style: 'labels_below', color: '#4CAF50' });
paint(myPartialMarker, { name: 'PartialSellMarker', style: 'labels_above', color: '#FF9800' });
paint(myReentryMarker, { name: 'ReentryBuyMarker', style: 'labels_below', color: '#2196F3' });

// --- Signals for Scanner / Alerts / Strategy Tester ---
register_signal(for_every(myEntryMarker, _v => _v != null), 'Entry Signal');
register_signal(for_every(myPartialMarker, _v => _v != null), 'Partial Sell Trigger');
register_signal(for_every(myReentryMarker, _v => _v != null), 'Re entry Buy Trigger');