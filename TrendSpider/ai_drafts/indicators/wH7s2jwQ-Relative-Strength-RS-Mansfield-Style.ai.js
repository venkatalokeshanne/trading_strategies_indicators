describe_indicator('Relative Strength (RS)', 'lower');

// ---------- Inputs ----------
const myBenchSymbol = input.symbol('Comparative Symbol', 'SP:SPX');
const myPeriod = input.number('Period', 50, { min: 1, max: 2000 });
const myShowMA = input.boolean('Show Moving Average', false);
const myMaPeriod = input.number('Moving Average Period', 10, { min: 1, max: 2000 });
const myTimeframe = input.select('Timeframe', 'Chart', ['Chart', ...constants.time_frames]);
const myRow = input.row();
const myUpperThresh = myRow.number('Upper Threshold', 10.0, { min: -1000, max: 1000, step: 1.0 });
const myLowerThresh = myRow.number('Lower Threshold', -10.0, { min: -1000, max: 1000, step: 1.0 });
const myShowThresh = input.boolean('Show Threshold Lines', true);

// Resolution to use: "Chart" means "use the chart's own time frame".
const myResolution = myTimeframe === 'Chart' ? current.resolution : myTimeframe;

// Helper to turn any error value (string, object, undefined, Error) into a
// readable string, since request.history() errors (and thrown values from
// the platform itself) are not always plain strings.
function myStringifyError(_err) {
	if (_err === null || _err === undefined) return 'Unknown error';
	if (typeof _err === 'string') return _err;
	if (_err instanceof Error) return _err.message;
	if (typeof _err === 'object') {
		// Try to pull a meaningful message out of common error shapes.
		if (_err.message) return String(_err.message);
		if (_err.error) return myStringifyError(_err.error);
		try {
			return JSON.stringify(_err);
		}
		catch (_e) {
			return String(_err);
		}
	}
	return String(_err);
}

// ---------- Data (MTF-aware) ----------
// request.history() can itself throw (not just resolve with { error }),
// for example when the comparative symbol is invalid. We wrap both calls
// so that whatever gets thrown is turned into a readable assertion message
// instead of surfacing as "[object Object]".
let myAssetData;
let myBenchData;

try {
	[myAssetData, myBenchData] = await Promise.all([
		request.history(current.ticker, myResolution),
		request.history(myBenchSymbol, myResolution)
	]);
}
catch (myFetchError) {
	throw `Error fetching history data: "${myStringifyError(myFetchError)}". Check the Comparative Symbol and Timeframe inputs`;
}

assert(!myAssetData.error, `Error fetching asset data: "${myStringifyError(myAssetData.error)}"`);
assert(!myBenchData.error, `Error fetching benchmark data: "${myStringifyError(myBenchData.error)}". Check the Comparative Symbol input`);
assert(myAssetData.time && myAssetData.time.length > 0, 'No asset data returned');
assert(myBenchData.time && myBenchData.time.length > 0, 'No benchmark data returned. Check the Comparative Symbol input');

// Land benchmark close onto asset's own time series (same resolution,
// so timestamps should align candle-for-candle; "le" matches the most
// recent benchmark point available at or before each asset time stamp).
const myBenchOnAsset = interpolate_sparse_series(
	land_points_onto_series(myBenchData.time, myBenchData.close, myAssetData.time, 'le'),
	'constant'
);

// ---------- Normalized RS (Mansfield-style with x100 scaling) ----------
const myRatio = div(myAssetData.close, myBenchOnAsset);
const myBaseline = sma(myRatio, myPeriod);
const myRsRaw = mult(sub(div(myRatio, myBaseline), 1), 100);

// ---------- Optional smoothing ----------
const mySignalRaw = sma(myRsRaw, myMaPeriod);

// Land computed series (which live on myAssetData.time, possibly a
// different timeframe than the chart) back onto the chart's own time axis.
const myRs = interpolate_sparse_series(
	land_points_onto_series(myAssetData.time, myRsRaw, time, 'le'),
	'constant'
);
const mySignal = interpolate_sparse_series(
	land_points_onto_series(myAssetData.time, mySignalRaw, time, 'le'),
	'constant'
);

// ---------- Plots ----------
paint(myRs, { name: 'RS', color: '#2962FF', thickness: 2 });
paint(myShowMA ? mySignal : constants.empty_series, { name: 'SignalMA', color: 'gray', thickness: 1 });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted', thickness: 1 });
paint(myShowThresh ? horizontal_line(myUpperThresh) : constants.empty_series, { name: 'UpperThreshold', color: 'green', style: 'dotted', thickness: 1 });
paint(myShowThresh ? horizontal_line(myLowerThresh) : constants.empty_series, { name: 'LowerThreshold', color: 'red', style: 'dotted', thickness: 1 });

// ---------- Signals (crossover / crossunder) ----------
const myCrossAboveZero = for_every(myRs, (_rs, _prev, _idx) => {
	if (_idx === 0) return false;
	return myRs[_idx - 1] <= 0 && _rs > 0;
});
const myCrossBelowZero = for_every(myRs, (_rs, _prev, _idx) => {
	if (_idx === 0) return false;
	return myRs[_idx - 1] >= 0 && _rs < 0;
});
const myCrossAboveUpper = for_every(myRs, (_rs, _prev, _idx) => {
	if (_idx === 0) return false;
	return myRs[_idx - 1] <= myUpperThresh && _rs > myUpperThresh;
});
const myCrossBelowLower = for_every(myRs, (_rs, _prev, _idx) => {
	if (_idx === 0) return false;
	return myRs[_idx - 1] >= myLowerThresh && _rs < myLowerThresh;
});

register_signal(myCrossAboveZero, 'RS Crossed Above Zero');
register_signal(myCrossBelowZero, 'RS Crossed Below Zero');
register_signal(myCrossAboveUpper, 'RS Crossed Above Upper Threshold');
register_signal(myCrossBelowLower, 'RS Crossed Below Lower Threshold');