// This indicator reproduces (as closely as the TrendSpider Custom JS API
// allows) a Pine Script which plots:
//   - Previous day High / Low / Mid as step lines
//   - 52 week ("Yearly") High / Low
//   - 13 week ("Quarterly") High / Low
//   - Combined labels on the last bar
// Pine's request.security(..., lookahead_on) peeks slightly into data that
// is not fully closed yet. TrendSpider's Custom JS API does not allow
// forward-looking computations (no lookahead), so this version lands the
// higher timeframe values using "le" (less-or-equal) landing + constant
// interpolation, which is the closest non-repainting equivalent. Values on
// most already-closed candles will match Pine exactly; the most recent,
// still-forming higher timeframe candle may show a value one bar later
// than Pine would.
describe_indicator('Yearly Quarterly Previous Day High Low Mid', 'price');

const myVisTab = input.tab('Visibility');
// Shortened input titles below (previous ones were too long for the engine)
const myHighLowCloseBase = myVisTab.select('52/13wk Base', 'Highs/Lows', ['Highs/Lows', 'Close']);
const myVisRow1 = myVisTab.row();
const myShowYH = myVisRow1.boolean('Show Yearly High', true);
const myShowYL = myVisRow1.boolean('Show Yearly Low', true);
const myVisRow2 = myVisTab.row();
const myShowQH = myVisRow2.boolean('Show Quarterly High', true);
const myShowQL = myVisRow2.boolean('Show Quarterly Low', true);

const myColorsTab = input.tab('Prev Day HL Colors');
const myPrevDayHighColor = myColorsTab.color('Prev Day High Col', 'blue');
const myPrevDayLowColor = myColorsTab.color('Prev Day Low Col', 'orange');
const myPrevDayMidColor = myColorsTab.color('Prev Day Mid Col', 'rgb(42, 44, 53)');

// === fetch additional data (daily and weekly) ===
const [myDailyData, myWeeklyData] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'W')
]);

assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

// === Previous Day High/Low/Mid ===
const myPrevDayHighRaw = shift(myDailyData.high, 1);
const myPrevDayLowRaw = shift(myDailyData.low, 1);
const myPrevDayMidRaw = div(add(myPrevDayHighRaw, myPrevDayLowRaw), 2);

const myPrevDayHighLanded = land_points_onto_series(myDailyData.time, myPrevDayHighRaw, time, 'le');
const myPrevDayLowLanded = land_points_onto_series(myDailyData.time, myPrevDayLowRaw, time, 'le');
const myPrevDayMidLanded = land_points_onto_series(myDailyData.time, myPrevDayMidRaw, time, 'le');

const myPrevDayHigh = interpolate_sparse_series(myPrevDayHighLanded, 'constant');
const myPrevDayLow = interpolate_sparse_series(myPrevDayLowLanded, 'constant');
const myPrevDayMid = interpolate_sparse_series(myPrevDayMidLanded, 'constant');

// === 52 week (Yearly) High/Low ===
const myWeeklyHH = highest(myWeeklyData.high, 52);
const myWeeklyLL = lowest(myWeeklyData.low, 52);
const myWeeklyHC = highest(myWeeklyData.close, 52);
const myWeeklyLC = lowest(myWeeklyData.close, 52);

const myHighPlotWeekly = myHighLowCloseBase == 'Highs/Lows' ? myWeeklyHH : myWeeklyHC;
const myLowPlotWeekly = myHighLowCloseBase == 'Highs/Lows' ? myWeeklyLL : myWeeklyLC;

// === 13 week (Quarterly) High/Low ===
const myQuarterlyHH = highest(myWeeklyData.high, 13);
const myQuarterlyLL = lowest(myWeeklyData.low, 13);
const myQuarterlyHC = highest(myWeeklyData.close, 13);
const myQuarterlyLC = lowest(myWeeklyData.close, 13);

const myQuarterlyHighPlotWeekly = myHighLowCloseBase == 'Highs/Lows' ? myQuarterlyHH : myQuarterlyHC;
const myQuarterlyLowPlotWeekly = myHighLowCloseBase == 'Highs/Lows' ? myQuarterlyLL : myQuarterlyLC;

// land weekly series onto the current chart
const myYearlyHighLanded = land_points_onto_series(myWeeklyData.time, myHighPlotWeekly, time, 'le');
const myYearlyLowLanded = land_points_onto_series(myWeeklyData.time, myLowPlotWeekly, time, 'le');
const myQuarterlyHighLanded = land_points_onto_series(myWeeklyData.time, myQuarterlyHighPlotWeekly, time, 'le');
const myQuarterlyLowLanded = land_points_onto_series(myWeeklyData.time, myQuarterlyLowPlotWeekly, time, 'le');

const myYearlyHigh = interpolate_sparse_series(myYearlyHighLanded, 'constant');
const myYearlyLow = interpolate_sparse_series(myYearlyLowLanded, 'constant');
const myQuarterlyHigh = interpolate_sparse_series(myQuarterlyHighLanded, 'constant');
const myQuarterlyLow = interpolate_sparse_series(myQuarterlyLowLanded, 'constant');

// === Paint lines (constant parameters/order, regardless of show toggles) ===
paint(myPrevDayHigh, { name: 'PrevDayHigh', color: myPrevDayHighColor, style: 'ladder', thickness: 1 });
paint(myPrevDayLow, { name: 'PrevDayLow', color: myPrevDayLowColor, style: 'ladder', thickness: 1 });
paint(myPrevDayMid, { name: 'PrevDayMid', color: myPrevDayMidColor, style: 'ladder', thickness: 1 });

const myYearlyHighPainted = paint(myShowYH ? myYearlyHigh : series_of(null), { name: 'YearlyHigh', color: 'orange', style: 'ladder', thickness: 1 });
const myYearlyLowPainted = paint(myShowYL ? myYearlyLow : series_of(null), { name: 'YearlyLow', color: 'orange', style: 'ladder', thickness: 1 });
const myQuarterlyHighPainted = paint(myShowQH ? myQuarterlyHigh : series_of(null), { name: 'QuarterlyHigh', color: 'purple', style: 'ladder', thickness: 1 });
const myQuarterlyLowPainted = paint(myShowQL ? myQuarterlyLow : series_of(null), { name: 'QuarterlyLow', color: 'purple', style: 'ladder', thickness: 1 });

// === Combined labels on the last bar ===
const myLastIndex = close.length - 1;
const myPriceRange = high[myLastIndex] - low[myLastIndex];
const myTolerance = myPriceRange * 0.01;

const myHighValY = myYearlyHigh[myLastIndex];
const myHighValQ = myQuarterlyHigh[myLastIndex];
const myLowValY = myYearlyLow[myLastIndex];
const myLowValQ = myQuarterlyLow[myLastIndex];

if (myShowYH || myShowQH) {
	const myMergedHigh = myShowYH && myShowQH && myHighValY != null && myHighValQ != null && Math.abs(myHighValY - myHighValQ) <= myTolerance;

	if (myMergedHigh) {
		paint_label_at_line(myYearlyHighPainted, myLastIndex, 'YH/QH', { color: 'white', background_color: 'orange' });
	}
	else {
		if (myShowYH) {
			paint_label_at_line(myYearlyHighPainted, myLastIndex, 'YH', { color: 'white', background_color: 'orange' });
		}
		if (myShowQH) {
			paint_label_at_line(myQuarterlyHighPainted, myLastIndex, 'QH', { color: 'white', background_color: 'purple' });
		}
	}
}

if (myShowYL || myShowQL) {
	const myMergedLow = myShowYL && myShowQL && myLowValY != null && myLowValQ != null && Math.abs(myLowValY - myLowValQ) <= myTolerance;

	if (myMergedLow) {
		paint_label_at_line(myYearlyLowPainted, myLastIndex, 'YL/QL', { color: 'white', background_color: 'orange' });
	}
	else {
		if (myShowYL) {
			paint_label_at_line(myYearlyLowPainted, myLastIndex, 'YL', { color: 'white', background_color: 'orange' });
		}
		if (myShowQL) {
			paint_label_at_line(myQuarterlyLowPainted, myLastIndex, 'QL', { color: 'white', background_color: 'purple' });
		}
	}
}

// === Scanning / Strategy signals ===
register_signal(for_every(close, myPrevDayHigh, (_c, _l) => _l != null && _c > _l), 'Close Above Previous Day High');
register_signal(for_every(close, myPrevDayLow, (_c, _l) => _l != null && _c < _l), 'Close Below Previous Day Low');
register_signal(for_every(close, myYearlyHigh, (_c, _l) => _l != null && _c > _l), 'Close Above Yearly High');
register_signal(for_every(close, myYearlyLow, (_c, _l) => _l != null && _c < _l), 'Close Below Yearly Low');
register_signal(for_every(close, myQuarterlyHigh, (_c, _l) => _l != null && _c > _l), 'Close Above Quarterly High');
register_signal(for_every(close, myQuarterlyLow, (_c, _l) => _l != null && _c < _l), 'Close Below Quarterly Low');