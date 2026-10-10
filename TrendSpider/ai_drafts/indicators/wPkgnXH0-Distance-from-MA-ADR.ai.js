describe_indicator('Distance from MA and ADR Percent', 'price');

// ===== Calculation Inputs =====
const myCalcTab = input.tab('Calculation');
const myMaLen = myCalcTab.number('MA Length', 50, { min: 1 });
const myMaType = myCalcTab.select('MA Type', 'SMA', ['SMA', 'EMA', 'WMA', 'VWMA']);
const myAtrLen = myCalcTab.number('ATR Length', 14, { min: 1 });
const myAdrLen = myCalcTab.number('ADR Percent Length', 20, { min: 1 });
// shortened title (previously too long, caused "input(): name is too lengthy")
const myExtThresh = myCalcTab.number('Ext Threshold ATR Mult', 5, { min: 0, step: 0.25 });

// ===== ADR Percent Inputs =====
const myAdrTab = input.tab('ADR Percent');
// Note: ADR% in Pine is pinned to a chosen timeframe (default Daily).
// This port keeps it on the Daily timeframe only, since arbitrary
// timeframe selection together with "lookahead_off" security semantics
// cannot be fully replicated with request.history() for intraday TFs
// other than Daily in a non-repainting way.
const myAdrClosedOnly = myAdrTab.boolean('Use completed bars only', true);

// ===== Display Toggles =====
const myDisplayTab = input.tab('Display');
const myShowAtrMult = myDisplayTab.boolean('Show ATR Multiple From MA', true);
const myShowPctGain = myDisplayTab.boolean('Show Percent Gain From MA', true);
const myShowAtrPct = myDisplayTab.boolean('Show ATR Percent', true);
const myShowAdrPct = myDisplayTab.boolean('Show ADR Percent', true);
const myTblPosRow = myDisplayTab.row();
const myTblPos = myTblPosRow.select('Table Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);
const myColorRow1 = myDisplayTab.row();
const myTxtColor = myColorRow1.color('Label Color', 'orange');
const myValColor = myColorRow1.color('Value Color', 'red');
const myColorRow2 = myDisplayTab.row();
const myExtColor = myColorRow2.color('Extended Value Color', 'yellow');
const myBgColor = myColorRow2.color('Background Color', 'rgba(0,0,0,0.8)');

// ===== Helper: compute MA by type =====
function myComputeMA(_type, _length) {
	if (_type === 'EMA') return ema(close, _length);
	if (_type === 'WMA') return wma(close, _length);
	if (_type === 'VWMA') return vwma(close, _length);
	return sma(close, _length);
}

// ===== Calculations =====
const myMa = myComputeMA(myMaType, myMaLen);
const myAtrVal = atr(high, low, close, myAtrLen);

// Percentage distance from the MA
const myPctGainFromMA = for_every(close, myMa, (_c, _m) => (_m == null || _m === 0) ? null : (_c - _m) / _m * 100);

// ATR expressed as a percentage of price
const myAtrPct = for_every(myAtrVal, close, (_a, _c) => (_a == null || _c === 0) ? null : _a / _c * 100);

// ATR multiple from MA: how many ATRs price sits above/below the MA
const myAtrMultFromMA = for_every(close, myMa, myAtrVal, (_c, _m, _a) => (_m == null || _a == null || _a === 0) ? null : (_c - _m) / _a);

// ===== ADR Percent: fetch Daily data and compute =====
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching Daily data: "${myDailyData.error}"`);

const myHLRatio = div(myDailyData.high, myDailyData.low);
const myAdrRawDaily = sub(mult(sma(myHLRatio, myAdrLen), 100), 100);

// "Use completed bars only" means using the previous completed daily bar's
// value (adrRaw[1] in Pine) instead of the still-forming one.
const myAdrSeriesDaily = myAdrClosedOnly ? shift(myAdrRawDaily, 1) : myAdrRawDaily;

// Land Daily ADR% values onto the current chart's time series without
// looking into the future (using 'le', matching barmerge.lookahead_off).
const myAdrLanded = land_points_onto_series(myDailyData.time, myAdrSeriesDaily, time, 'le');
const myAdrPct = interpolate_sparse_series(myAdrLanded, 'constant');

// isExtended: three-valued logic handled explicitly, na treated as false
const myIsExtended = for_every(myAtrMultFromMA, _v => _v == null ? false : Math.abs(_v) >= myExtThresh);

// ===== Signals for scanners/alerts/strategies =====
register_signal(myIsExtended, 'Extended From MA');
register_signal(for_every(myAtrMultFromMA, _v => _v != null && _v > 0), 'Above MA');
register_signal(for_every(myAtrMultFromMA, _v => _v != null && _v < 0), 'Below MA');

// ===== Table (overlay) =====
function myFormatValue(_v, _suffix) {
	if (_v == null || isNaN(_v)) return 'n/a';
	return _v.toFixed(2) + _suffix;
}

const myLastIndex = close.length - 1;
const myLastAtrMult = myAtrMultFromMA[myLastIndex];
const myLastPctGain = myPctGainFromMA[myLastIndex];
const myLastAtrPct = myAtrPct[myLastIndex];
const myLastAdrPct = myAdrPct[myLastIndex];
const myLastExtended = myIsExtended[myLastIndex];
const myMultValueColor = myLastExtended ? myExtColor : myValColor;

const myTableRows = [];

// Rows are always created with constant structure; when a toggle is off,
// the row's text cells are emptied instead of removing the row, to keep
// paint_overlay() output structurally constant across all parameter sets.
myTableRows.push({
	cells: [
		{ text: myShowAtrMult ? 'ATR Multiple From MA' : '', color: myTxtColor },
		{ text: myShowAtrMult ? myFormatValue(myLastAtrMult, 'x') : '', color: myMultValueColor }
	]
});
myTableRows.push({
	cells: [
		{ text: myShowPctGain ? 'Percent Gain From MA' : '', color: myTxtColor },
		{ text: myShowPctGain ? myFormatValue(myLastPctGain, '%') : '', color: myValColor }
	]
});
myTableRows.push({
	cells: [
		{ text: myShowAtrPct ? 'ATR Percent' : '', color: myTxtColor },
		{ text: myShowAtrPct ? myFormatValue(myLastAtrPct, '%') : '', color: myValColor }
	]
});
myTableRows.push({
	cells: [
		{ text: myShowAdrPct ? 'ADR Percent' : '', color: myTxtColor },
		{ text: myShowAdrPct ? myFormatValue(myLastAdrPct, '%') : '', color: myValColor }
	]
});

paint_overlay('DistanceFromMATable', { position: myTblPos, background_color: myBgColor }, {
	rows: myTableRows
});

// Plot the MA line on the price axis, since this is an overlay indicator
// and the MA is the central reference level being measured against.
paint(myMa, { name: 'MA', color: 'silver', thickness: 1 });