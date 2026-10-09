// ============================================================================
// VASA Market Structure (ported from TradingView Pine Script)
// Confirmed swing highs/lows (non-repainting pivots), BOS/CHoCH labels on
// closed breaks, and prior day/week high-low levels.
// ============================================================================
describe_indicator('VASA Market Structure', 'price');

const myStructureTab = input.tab('Structure');
const myLb = myStructureTab.number('Swing Left Bars', 8, { min: 1, max: 100 });
const myRb = myStructureTab.number('Swing Right Bars', 8, { min: 1, max: 100 });
const myShowBOS = myStructureTab.boolean('Label BOS / CHoCH', true);
const myShowSwings = myStructureTab.boolean('Mark Confirmed Swings', true);

const myLevelsTab = input.tab('Prior Levels');
const myShowPD = myLevelsTab.boolean('Prior Day High/Low', true);
const myShowPW = myLevelsTab.boolean('Prior Week High/Low', true);

const myStyleTab = input.tab('Style');
const myColUp = myStyleTab.row();
const myColorUp = 'green';
const myColorDn = 'red';
const myColorLevels = 'gray';

// ---------- Confirmed swings (pivot high/low) ----------
const myPivotHighs = pivot_high(high, myLb, myRb);
const myPivotLows = pivot_low(low, myLb, myRb);

const myCandleCount = close.length;
const myLastSwingHigh = series_of(null);
const myLastSwingLow = series_of(null);
const myDirSeries = series_of(0);
const myBosUpSeries = series_of(false);
const myBosDnSeries = series_of(false);
const myLabelTextSeries = series_of(null);

let myCurHigh = null;
let myCurLow = null;
let myCurDir = 0;

// Sequential state machine (mirrors Pine's bar-by-bar var state), can't be
// expressed with the vectorized built-ins because dir depends on history.
for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
	if (myPivotHighs[myIndex] !== null) {
		myCurHigh = myPivotHighs[myIndex];
	}
	if (myPivotLows[myIndex] !== null) {
		myCurLow = myPivotLows[myIndex];
	}

	myLastSwingHigh[myIndex] = myCurHigh;
	myLastSwingLow[myIndex] = myCurLow;

	const myPrevClose = myIndex > 0 ? close[myIndex - 1] : null;

	const myBosUp = myCurHigh !== null && close[myIndex] > myCurHigh && myPrevClose !== null && myPrevClose <= myCurHigh;
	const myBosDn = myCurLow !== null && close[myIndex] < myCurLow && myPrevClose !== null && myPrevClose >= myCurLow;

	if (myBosUp) {
		myLabelTextSeries[myIndex] = myCurDir === -1 ? 'CHoCH Up' : 'BOS Up';
		myCurDir = 1;
	}
	else if (myBosDn) {
		myLabelTextSeries[myIndex] = myCurDir === 1 ? 'CHoCH Down' : 'BOS Down';
		myCurDir = -1;
	}

	myBosUpSeries[myIndex] = myBosUp;
	myBosDnSeries[myIndex] = myBosDn;
	myDirSeries[myIndex] = myCurDir;
}

// ---------- Prior day / week high-low (non-repainting) ----------
const [myDailyData, myWeeklyData] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'W')
]);

assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

// shift by 1 to only use the previous (fully closed) higher timeframe bar
const myPrevDayHigh = shift(myDailyData.high, 1);
const myPrevDayLow = shift(myDailyData.low, 1);
const myPrevWeekHigh = shift(myWeeklyData.high, 1);
const myPrevWeekLow = shift(myWeeklyData.low, 1);

const myPDHLanded = land_points_onto_series(myDailyData.time, myPrevDayHigh, time, 'le');
const myPDLLanded = land_points_onto_series(myDailyData.time, myPrevDayLow, time, 'le');
const myPWHLanded = land_points_onto_series(myWeeklyData.time, myPrevWeekHigh, time, 'le');
const myPWLLanded = land_points_onto_series(myWeeklyData.time, myPrevWeekLow, time, 'le');

const myPDHFinal = myShowPD ? interpolate_sparse_series(myPDHLanded, 'constant') : constants.empty_series;
const myPDLFinal = myShowPD ? interpolate_sparse_series(myPDLLanded, 'constant') : constants.empty_series;
const myPWHFinal = myShowPW ? interpolate_sparse_series(myPWHLanded, 'constant') : constants.empty_series;
const myPWLFinal = myShowPW ? interpolate_sparse_series(myPWLLanded, 'constant') : constants.empty_series;

paint(myPDHFinal, { name: 'PriorDayHigh', color: myColorLevels, style: 'ladder' });
paint(myPDLFinal, { name: 'PriorDayLow', color: myColorLevels, style: 'ladder' });
paint(myPWHFinal, { name: 'PriorWeekHigh', color: myColorLevels, style: 'ladder', thickness: 2 });
paint(myPWLFinal, { name: 'PriorWeekLow', color: myColorLevels, style: 'ladder', thickness: 2 });

// ---------- Confirmed swing markers ----------
const mySwingHighMarks = myShowSwings ? myPivotHighs.map(_v => _v !== null ? constants.icons.diamond : null) : constants.empty_series;
const mySwingLowMarks = myShowSwings ? myPivotLows.map(_v => _v !== null ? constants.icons.diamond : null) : constants.empty_series;

paint(mySwingHighMarks, { name: 'SwingHigh', style: 'labels_above', color: myColorDn });
paint(mySwingLowMarks, { name: 'SwingLow', style: 'labels_below', color: myColorUp });

// ---------- BOS / CHoCH labels ----------
// Hidden close line used purely to anchor the BOS/CHoCH text labels.
const myAnchorLine = paint(close, { name: 'StructureAnchor', hidden: true });

if (myShowBOS) {
	for (let myIndex = 0; myIndex < myCandleCount; myIndex += 1) {
		if (myLabelTextSeries[myIndex] !== null) {
			const myIsUp = myBosUpSeries[myIndex];
			paint_label_at_line(myAnchorLine, myIndex, myLabelTextSeries[myIndex], {
				color: myIsUp ? myColorUp : myColorDn,
				background_color: myIsUp ? myColorUp : myColorDn,
				vertical_align: myIsUp ? 'bottom' : 'top'
			});
		}
	}
}

// ---------- Signals ----------
register_signal(myBosUpSeries, 'Bullish BOS or CHoCH');
register_signal(myBosDnSeries, 'Bearish BOS or CHoCH');