describe_indicator('MA Cross Plus RS Screener', 'lower', { decimals: 2 });

// === Inputs ===
const myPriceSource = input.select('Source', 'close', constants.price_source_options);
const myPrice = market[myPriceSource];
const myFastLen = input.number('Fast EMA Length', 10, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 40, { min: 1, max: 500 });
// shortened input titles to satisfy the platform's name length limit
const myComparativeTicker = input.symbol('RS Benchmark', 'NSE:NIFTYSMLCAP250');
const myRsLength = input.number('RS Period', 123, { min: 1, max: 2000 });
const myRsThreshold = input.number('RS Threshold', 0, { min: -100, max: 100 });
const mySensitivity = input.number('Sensitivity', 8, { min: 0.1, max: 100 });

// === Fetch comparative symbol data (same resolution as current chart) ===
const myCompHistory = await request.history(myComparativeTicker, current.resolution);
// request.history() can return an error which is itself an object (not a
// string), so stringifying it directly as "${myCompHistory.error}" rendered
// as "[object Object]". We use JSON.stringify() so the real error message
// (whatever its shape) is actually visible, and we throw instead of letting
// the rest of the script run on bad data.
if (myCompHistory.error) {
	throw `Error fetching comparative symbol data: ${JSON.stringify(myCompHistory.error)}`;
}
assert(Array.isArray(myCompHistory.time) && myCompHistory.time.length > 0, 'Comparative symbol returned no history data');

// Land the comparative close prices onto our chart's time axis.
// 'le' picks the most recent comparative bar at or before each of our candles,
// then we hold that value constant until the next landed point (no repainting).
const myCompLanded = land_points_onto_series(myCompHistory.time, myCompHistory.close, time, 'le');
const myComparativeClose = interpolate_sparse_series(myCompLanded, 'constant');

// === Calculations ===
const myFastMA = ema(myPrice, myFastLen);
const mySlowMA = ema(myPrice, mySlowLen);
const myMaCondition = for_every(myFastMA, mySlowMA, (_f, _s) => _f > _s);

// Replicates Pine's series[rsLength] lookback via shift()
const myBaseShifted = shift(myPrice, myRsLength);
const myCompShifted = shift(myComparativeClose, myRsLength);

// res = base/base[len] / (comp/comp[len]) - 1
const myRes = for_every(
	myPrice, myBaseShifted, myComparativeClose, myCompShifted,
	(_base, _baseShift, _comp, _compShift) => {
		if (!_baseShift || !_comp || !_compShift) {
			return null;
		}
		return ((_base / _baseShift) / (_comp / _compShift)) - 1;
	});

const myRsCondition = for_every(myRes, _r => _r !== null && _r > myRsThreshold);

// === Flag logic: 3 = bullish, 2 = hold, 1 = bearish ===
const myFlag = for_every(myMaCondition, myRsCondition, (_ma, _rs) => {
	const myBothTrue = _ma && _rs;
	const myEitherTrue = _ma !== _rs;
	if (myBothTrue) return 3;
	if (myEitherTrue) return 2;
	return 1;
});

const myBothTrueSignal = for_every(myFlag, _f => _f === 3);
const myHoldSignal = for_every(myFlag, _f => _f === 2);
const myBearishSignal = for_every(myFlag, _f => _f === 1);
register_signal(myBothTrueSignal, 'Bullish Flag');
register_signal(myHoldSignal, 'Hold Flag');
register_signal(myBearishSignal, 'Bearish Flag');

// === Composite score (tanh-scaled, -100 to +100) ===
const myMaSignalPct = for_every(myFastMA, mySlowMA, (_f, _s) => _s !== 0 ? ((_f - _s) / _s) * 100 : 0);
const myRsSignalPct = for_every(myRes, _r => _r !== null ? _r * 100 : 0);
const myRawComposite = for_every(myMaSignalPct, myRsSignalPct, (_ma, _rs) => (_ma + _rs) / 2);
const myCompositeScore = for_every(myRawComposite, _raw => {
	const myTanhInput = _raw / mySensitivity;
	const myExpTerm = Math.exp(2 * myTanhInput);
	const myTanhVal = (myExpTerm - 1) / (myExpTerm + 1);
	return 100 * myTanhVal;
});

// === Bars since last bearish flag ===
const myBarsSinceBearish = for_every(myFlag, (_f, _prev, _idx) => {
	if (_f === 1) {
		return 0;
	}
	return (_prev === null || _prev === undefined ? 0 : _prev) + 1;
});

const myFlagColor = for_every(myFlag, _f => _f === 3 ? '#26A69A' : (_f === 2 ? '#FF9800' : '#EF5350'));

paint(myCompositeScore, { name: 'CompositeScore', color: myFlagColor, thickness: 3 });
paint(horizontal_line(0), { name: 'ZeroLine', color: 'gray', style: 'dotted' });
paint(horizontal_line(100), { name: 'UpperBound', color: 'silver', style: 'dotted' });
paint(horizontal_line(-100), { name: 'LowerBound', color: 'silver', style: 'dotted' });

register_signal(myFlag, 'Flag Value');
register_signal(myBarsSinceBearish, 'Bars Since Bearish');

// === Summary overlay table (last values only) ===
const myLastFlag = myFlag[myFlag.length - 1];
const myLastScore = myCompositeScore[myCompositeScore.length - 1];
const myLastBarsSinceBearish = myBarsSinceBearish[myBarsSinceBearish.length - 1];
const myFlagLabel = myLastFlag === 3 ? 'BULLISH' : (myLastFlag === 2 ? 'HOLD' : 'BEARISH');
const myFlagColorText = myLastFlag === 3 ? '#26A69A' : (myLastFlag === 2 ? '#FF9800' : '#EF5350');

paint_overlay('SummaryTable', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Flag', color: 'white' }, { text: myFlagLabel, color: myFlagColorText }] },
		{ cells: [{ text: 'Score', color: 'white' }, { text: String(Math.round(myLastScore * 100) / 100), color: myFlagColorText }] },
		{ cells: [{ text: 'Bars/Bearish', color: 'white' }, { text: String(myLastBarsSinceBearish), color: 'white' }] }
	]
});