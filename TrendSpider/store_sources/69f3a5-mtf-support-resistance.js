<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('MTF Support & Resistance');

// ============================================
// DEFAULT LINE STYLES
// These are default styles only.
// Users can customize each painted line directly
// from TrendSpider's generated series controls.
// ============================================
const monthlyColor = '#FF4444';
const weeklyColor = '#4488FF';
const dailyColor = '#44FF88';

const monthlyThickness = 3;
const weeklyThickness = 2;
const dailyThickness = 1;

const monthlyStyle = 'line';
const weeklyStyle = 'line';
const dailyStyle = 'line';

// ============================================
// USER INPUTS
// Functional inputs only.
// Styling is handled by TrendSpider's generated
// per-series controls.
// ============================================

// Maximum number of levels that can be painted.
// This constant defines the total number of paint() calls.
const MAX_LEVELS = 5;

// User can choose how many levels to display,
// but the script always paints MAX_LEVELS lines per R/S group.
const numLevels = input.number('Number of Levels', 1, { min: 1, max: MAX_LEVELS });

const pivotLookback = input.number('Pivot Lookback', 5, { min: 2, max: 20 });

const showMonthly = input.boolean('Show Monthly', true);
const showWeekly = input.boolean('Show Weekly', true);
const showDaily = input.boolean('Show Daily', true);

const showLabels = input.boolean('Show Labels', true);
const showTFTag = input.boolean('Show TF Tag', true);

// ============================================
// SAFETY CLAMPS
// ============================================
const myNumLevels = Math.max(1, Math.min(MAX_LEVELS, numLevels));
const myPivotLookback = Math.max(2, Math.min(20, pivotLookback));

// ============================================
// HELPER FUNCTION: DETECT PIVOTS
// ============================================
function detectPivots(_high, _low, _lookback) {
	const mySwingHighs = [];
	const mySwingLows = [];
	
	const myStartIndex = _lookback;
	const myEndIndex = _high.length - _lookback;
	
	for (let i = myStartIndex; i < myEndIndex; i++) {
		let isSwingHigh = true;
		for (let j = i - _lookback; j <= i + _lookback; j++) {
			if (j !== i && _high[j] >= _high[i]) {
				isSwingHigh = false;
				break;
			}
		}
		if (isSwingHigh) {
			mySwingHighs.push({ index: i, price: _high[i] });
		}
		
		let isSwingLow = true;
		for (let j = i - _lookback; j <= i + _lookback; j++) {
			if (j !== i && _low[j] <= _low[i]) {
				isSwingLow = false;
				break;
			}
		}
		if (isSwingLow) {
			mySwingLows.push({ index: i, price: _low[i] });
		}
	}
	
	return { highs: mySwingHighs, lows: mySwingLows };
}

// ============================================
// FETCH DATA AND DETECT PIVOTS
// ============================================
const monthlyData = await request.history(current.ticker, 'M');
assert(!monthlyData.error, 'Error fetching monthly data: ' + monthlyData.error);

const weeklyData = await request.history(current.ticker, 'W');
assert(!weeklyData.error, 'Error fetching weekly data: ' + weeklyData.error);

const dailyData = await request.history(current.ticker, 'D');
assert(!dailyData.error, 'Error fetching daily data: ' + dailyData.error);

const monthlyPivots = detectPivots(monthlyData.high, monthlyData.low, myPivotLookback);
const weeklyPivots = detectPivots(weeklyData.high, weeklyData.low, myPivotLookback);
const dailyPivots = detectPivots(dailyData.high, dailyData.low, myPivotLookback);

// ============================================
// PREPARE LEVELS TO PAINT
// ============================================
const myMonthlyHighLevels = monthlyPivots.highs.slice(-myNumLevels);
const myMonthlyLowLevels = monthlyPivots.lows.slice(-myNumLevels);

const myWeeklyHighLevels = weeklyPivots.highs.slice(-myNumLevels);
const myWeeklyLowLevels = weeklyPivots.lows.slice(-myNumLevels);

const myDailyHighLevels = dailyPivots.highs.slice(-myNumLevels);
const myDailyLowLevels = dailyPivots.lows.slice(-myNumLevels);

// ============================================
// HELPER: BUILD HORIZONTAL LEVEL SERIES
// ============================================
function createLevelSeries(_pivotArray, _sourceTime) {
	const mySeries = series_of(null);
	
	for (const myPivot of _pivotArray) {
		const myPivotTime = _sourceTime[myPivot.index];
		
		for (let i = 0; i < time.length; i++) {
			if (time[i] >= myPivotTime) {
				for (let j = i; j < time.length; j++) {
					mySeries[j] = myPivot.price;
				}
				break;
			}
		}
	}
	
	return mySeries;
}

// ============================================
// HELPER: LABEL TEXT
// ============================================
function generateLabelText(_price, _tfTag) {
	const myFormattedPrice = _price.toFixed(2);
	if (showTFTag) {
		return _tfTag + ' ' + myFormattedPrice;
	}
	return myFormattedPrice;
}

// ============================================
// PAINT LINES WITH CONSTANT PAINT() COUNT
// This ensures we always call paint() exactly:
// MAX_LEVELS * 2 (R + S) * 3 (timeframes) = 60 times.
// Inactive levels are painted as null series.
// ============================================

// Monthly levels
for (let i = 0; i < MAX_LEVELS; i++) {
	const myActive = showMonthly && i < myNumLevels;
	const myHighPivot = (myActive && myMonthlyHighLevels[i]) ? [myMonthlyHighLevels[i]] : [];
	const myLowPivot = (myActive && myMonthlyLowLevels[i]) ? [myMonthlyLowLevels[i]] : [];
	
	const myHighSeries = myHighPivot.length > 0 ? createLevelSeries(myHighPivot, monthlyData.time) : series_of(null);
	const myLowSeries = myLowPivot.length > 0 ? createLevelSeries(myLowPivot, monthlyData.time) : series_of(null);
	
	const myHighLineId = paint(myHighSeries, {
		name: 'Monthly R' + (i + 1),
		color: monthlyColor,
		thickness: monthlyThickness,
		style: monthlyStyle
	});
	
	const myLowLineId = paint(myLowSeries, {
		name: 'Monthly S' + (i + 1),
		color: monthlyColor,
		thickness: monthlyThickness,
		style: monthlyStyle
	});
	
	if (showLabels && myHighPivot.length > 0) {
		paint_label_at_line(myHighLineId, close.length - 1, generateLabelText(myHighPivot[0].price, 'M'), {
			color: monthlyColor,
			vertical_align: 'middle'
		});
	}
	
	if (showLabels && myLowPivot.length > 0) {
		paint_label_at_line(myLowLineId, close.length - 1, generateLabelText(myLowPivot[0].price, 'M'), {
			color: monthlyColor,
			vertical_align: 'middle'
		});
	}
}

// Weekly levels
for (let i = 0; i < MAX_LEVELS; i++) {
	const myActive = showWeekly && i < myNumLevels;
	const myHighPivot = (myActive && myWeeklyHighLevels[i]) ? [myWeeklyHighLevels[i]] : [];
	const myLowPivot = (myActive && myWeeklyLowLevels[i]) ? [myWeeklyLowLevels[i]] : [];
	
	const myHighSeries = myHighPivot.length > 0 ? createLevelSeries(myHighPivot, weeklyData.time) : series_of(null);
	const myLowSeries = myLowPivot.length > 0 ? createLevelSeries(myLowPivot, weeklyData.time) : series_of(null);
	
	const myHighLineId = paint(myHighSeries, {
		name: 'Weekly R' + (i + 1),
		color: weeklyColor,
		thickness: weeklyThickness,
		style: weeklyStyle
	});
	
	const myLowLineId = paint(myLowSeries, {
		name: 'Weekly S' + (i + 1),
		color: weeklyColor,
		thickness: weeklyThickness,
		style: weeklyStyle
	});
	
	if (showLabels && myHighPivot.length > 0) {
		paint_label_at_line(myHighLineId, close.length - 1, generateLabelText(myHighPivot[0].price, 'W'), {
			color: weeklyColor,
			vertical_align: 'middle'
		});
	}
	
	if (showLabels && myLowPivot.length > 0) {
		paint_label_at_line(myLowLineId, close.length - 1, generateLabelText(myLowPivot[0].price, 'W'), {
			color: weeklyColor,
			vertical_align: 'middle'
		});
	}
}

// Daily levels
for (let i = 0; i < MAX_LEVELS; i++) {
	const myActive = showDaily && i < myNumLevels;
	const myHighPivot = (myActive && myDailyHighLevels[i]) ? [myDailyHighLevels[i]] : [];
	const myLowPivot = (myActive && myDailyLowLevels[i]) ? [myDailyLowLevels[i]] : [];
	
	const myHighSeries = myHighPivot.length > 0 ? createLevelSeries(myHighPivot, dailyData.time) : series_of(null);
	const myLowSeries = myLowPivot.length > 0 ? createLevelSeries(myLowPivot, dailyData.time) : series_of(null);
	
	const myHighLineId = paint(myHighSeries, {
		name: 'Daily R' + (i + 1),
		color: dailyColor,
		thickness: dailyThickness,
		style: dailyStyle
	});
	
	const myLowLineId = paint(myLowSeries, {
		name: 'Daily S' + (i + 1),
		color: dailyColor,
		thickness: dailyThickness,
		style: dailyStyle
	});
	
	if (showLabels && myHighPivot.length > 0) {
		paint_label_at_line(myHighLineId, close.length - 1, generateLabelText(myHighPivot[0].price, 'D'), {
			color: dailyColor,
			vertical_align: 'middle'
		});
	}
	
	if (showLabels && myLowPivot.length > 0) {
		paint_label_at_line(myLowLineId, close.length - 1, generateLabelText(myLowPivot[0].price, 'D'), {
			color: dailyColor,
			vertical_align: 'middle'
		});
	}
}</code>