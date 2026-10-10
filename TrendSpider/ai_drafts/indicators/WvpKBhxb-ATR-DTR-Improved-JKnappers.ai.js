describe_indicator('ATR DTR Improved JKnappers', 'lower');

// ─────────────────────────────────────────────
// Assumptions made while porting this from Pine:
// - "atr[1]" (previous COMPLETED higher timeframe ATR) is reproduced by
//   shifting the fetched higher timeframe ATR series by 1 bar and then
//   landing it onto the current chart using the start of each higher
//   timeframe period (land_points_onto_series with method "le"). This
//   assigns the ATR of the PREVIOUS completed period to every candle that
//   belongs to the current (still forming) period, matching Pine logic.
// - "dtr" (current developing High - Low of the chosen higher timeframe)
//   is reproduced by grouping the chart candles into higher timeframe
//   periods (using bar_at) and computing a running High/Low that resets
//   whenever a new period starts. This mirrors Pine's live "high - low"
//   on the higher timeframe exactly for intraday charts.
// - Pine's table is reproduced with paint_overlay(). Chart.js callbacks
//   are not used, since the custom JS engine forbids functions in overlay
//   definitions.
// ─────────────────────────────────────────────

const myAtrTimeFrame = input.select('ATR / DTR Timeframe', 'D', constants.time_frames);
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 500 });
// shortened title to satisfy input() name length limit
const myPercentColorThreshold = input.number('Color Threshold Pct', 100, { min: 1, max: 1000 });
const myNormalColor = input.color('Color under percentage', 'gray');
const myOverColor = input.color('Color over percentage', 'white');
const myBoxPlacement = input.select('Box Placement', 'bottom_right', [
	'bottom_right',
	'bottom_left',
	'top_right',
	'top_center',
	'bottom_center'
]);

// ─────────────────────────────────────────────
// Fetch higher timeframe data and compute ATR
// ─────────────────────────────────────────────
const myHigherTFData = await request.history(current.ticker, myAtrTimeFrame);
assert(!myHigherTFData.error, `Error fetching higher timeframe data: "${myHigherTFData.error}"`);

const myHigherTFAtr = atr(myHigherTFData.high, myHigherTFData.low, myHigherTFData.close, myAtrLength);

// shift by 1 bar so value at period k represents ATR of period k-1
// (the "previous completed" ATR, as seen during period k)
const myShiftedAtr = shift(myHigherTFAtr, 1);
const myAtrLanded = land_points_onto_series(myHigherTFData.time, myShiftedAtr, time, 'le');
const myAtrOnChart = interpolate_sparse_series(myAtrLanded, 'constant');

// ─────────────────────────────────────────────
// Compute current developing DTR (High - Low) of the
// selected higher timeframe, grouped by period on the current chart
// ─────────────────────────────────────────────
const myPeriodIdAtIndex = time.map(myTimestamp => bar_at(myTimestamp, myAtrTimeFrame).session);

const myRunningHigh = series_of(null);
const myRunningLow = series_of(null);
const myDtrOnChart = series_of(null);

for (let myCandleIndex = 0; myCandleIndex < close.length; myCandleIndex += 1) {
	const myNewPeriodStarted = myCandleIndex === 0 || myPeriodIdAtIndex[myCandleIndex] !== myPeriodIdAtIndex[myCandleIndex - 1];

	if (myNewPeriodStarted) {
		myRunningHigh[myCandleIndex] = high[myCandleIndex];
		myRunningLow[myCandleIndex] = low[myCandleIndex];
	}
	else {
		myRunningHigh[myCandleIndex] = Math.max(high[myCandleIndex], myRunningHigh[myCandleIndex - 1]);
		myRunningLow[myCandleIndex] = Math.min(low[myCandleIndex], myRunningLow[myCandleIndex - 1]);
	}

	myDtrOnChart[myCandleIndex] = myRunningHigh[myCandleIndex] - myRunningLow[myCandleIndex];
}

// ─────────────────────────────────────────────
// Percentage calculation
// ─────────────────────────────────────────────
const myAtrPercent = for_every(myAtrOnChart, myDtrOnChart, (_atrValue, _dtrValue) => {
	if (_atrValue > 0) {
		return (_dtrValue / _atrValue) * 100;
	}
	return null;
});

const myAtrRounded = for_every(myAtrOnChart, _atrValue => Math.round(_atrValue * 100) / 100);
const myDtrRounded = for_every(myDtrOnChart, _dtrValue => Math.round(_dtrValue * 100) / 100);
const myPercentRounded = for_every(myAtrPercent, _percentValue => _percentValue === null ? null : Math.round(_percentValue));

// ─────────────────────────────────────────────
// Table overlay (reproduces the Pine table)
// ─────────────────────────────────────────────
const myLastIndex = close.length - 1;
const myLastAtr = myAtrRounded[myLastIndex];
const myLastDtr = myDtrRounded[myLastIndex];
const myLastPercent = myPercentRounded[myLastIndex];
const myIsOverThreshold = (myAtrPercent[myLastIndex] !== null) && (myAtrPercent[myLastIndex] >= myPercentColorThreshold);
const myCurrentBgColor = myIsOverThreshold ? myOverColor : myNormalColor;

paint_overlay('AtrDtrTable', { position: myBoxPlacement }, {
	rows: [{
		cells: [
			{ text: `ATR(${myAtrLength}): ${myLastAtr}`, background_color: myCurrentBgColor, border_color: 'teal' },
			{ text: `DTR: ${myLastDtr}`, background_color: myCurrentBgColor, border_color: 'teal' },
			{ text: `${myLastPercent}%`, background_color: myCurrentBgColor, border_color: 'teal' }
		]
	}]
});

// ─────────────────────────────────────────────
// Signals for scanning, alerts and strategies
// ─────────────────────────────────────────────
const myOverThresholdSignal = for_every(myAtrPercent, _percentValue => _percentValue !== null && _percentValue >= myPercentColorThreshold);
register_signal(myOverThresholdSignal, 'DTR Percent Over Threshold');

const myUnderThresholdSignal = for_every(myAtrPercent, _percentValue => _percentValue !== null && _percentValue < myPercentColorThreshold);
register_signal(myUnderThresholdSignal, 'DTR Percent Under Threshold');