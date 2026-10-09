describe_indicator('VIX MACD Long Strategy Signals', 'lower');

// Inputs for MACD settings, mirroring the Pine Script inputs
const myFastLength = input.number('MACD Fast', 12, { min: 1, max: 200 });
const mySlowLength = input.number('MACD Slow', 26, { min: 1, max: 200 });
const mySignalLength = input.number('MACD Signal', 9, { min: 1, max: 200 });

// Fetch VIX data on the current chart's resolution, like request.security() in Pine.
// Different data vendors use different ticker symbols for VIX, so we try a few
// candidates in parallel (always at top level, bundled via Promise.all) and use
// the first one that resolves successfully.
// NOTE: using Promise.allSettled instead of Promise.all, because if one of the
// candidate tickers is invalid, request.history() can reject outright (instead of
// resolving to { error }), which made Promise.all reject the whole batch with
// an opaque "[object Object]" error. allSettled lets us inspect each outcome safely.
const myVixCandidates = ['VIX', 'VIX.X', '^VIX'];
const myVixSettled = await Promise.allSettled(
	myVixCandidates.map(_ticker => request.history(_ticker, current.resolution))
);

const myVixData = myVixSettled
	.filter(_settled => _settled.status === 'fulfilled')
	.map(_settled => _settled.value)
	.find(_result => _result && !_result.error && _result.close && _result.close.length > 0);

assert(
	!!myVixData,
	"Error fetching VIX data for all candidate tickers: " + myVixSettled.map(_settled => {
		if (_settled.status === 'rejected') return JSON.stringify(_settled.reason);
		if (_settled.value && _settled.value.error) return JSON.stringify(_settled.value.error);
		return "empty data";
	}).join(" | ")
);

// Compute MACD on the VIX close series
const myMacdLineRaw = sub(ema(myVixData.close, myFastLength), ema(myVixData.close, mySlowLength));
const mySignalLineRaw = ema(myMacdLineRaw, mySignalLength);

// Land the VIX-based MACD/Signal series onto the current chart's time series.
// 'constant' interpolation keeps this strategy backtestable (no forward-looking data).
const myMacdLandedSparse = land_points_onto_series(myVixData.time, myMacdLineRaw, time);
const mySignalLandedSparse = land_points_onto_series(myVixData.time, mySignalLineRaw, time);
const myMacdLine = interpolate_sparse_series(myMacdLandedSparse, 'constant');
const mySignalLine = interpolate_sparse_series(mySignalLandedSparse, 'constant');

// Crossunder: MACD crosses below Signal (long entry condition)
const myLongCondition = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevMacd = myMacdLine[_index - 1];
	const myPrevSignal = mySignalLine[_index - 1];
	if (myPrevMacd === null || myPrevSignal === null || _macd === null || _signal === null) return false;
	return (myPrevMacd >= myPrevSignal) && (_macd < _signal);
});

// Crossover: MACD crosses above Signal (exit condition)
const myExitCondition = for_every(myMacdLine, mySignalLine, (_macd, _signal, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevMacd = myMacdLine[_index - 1];
	const myPrevSignal = mySignalLine[_index - 1];
	if (myPrevMacd === null || myPrevSignal === null || _macd === null || _signal === null) return false;
	return (myPrevMacd <= myPrevSignal) && (_macd > _signal);
});

// Register signals for use in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, "VIX MACD Long Entry");
register_signal(myExitCondition, "VIX MACD Long Exit");

// Paint MACD and Signal lines for visual reference
const myMacdLinePainted = paint(myMacdLine, { name: 'VIX MACD', color: '#4DA3FF', thickness: 2 });
const mySignalLinePainted = paint(mySignalLine, { name: 'VIX Signal', color: '#EF5350', thickness: 2 });

// Mark entry/exit points on the MACD line
const myLongMarks = for_every(myLongCondition, myMacdLine, (_cond, _macd) => _cond ? _macd : null);
const myExitMarks = for_every(myExitCondition, myMacdLine, (_cond, _macd) => _cond ? _macd : null);

paint(myLongMarks, { name: 'Long Entry', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myExitMarks, { name: 'Long Exit', style: 'labels_above', color: '#EF5350', thickness: 3 });