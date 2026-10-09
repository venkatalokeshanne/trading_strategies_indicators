describe_indicator('PE Ratio Quarter Vs Median', 'lower');

const myLengthTab = input.tab('PE Settings');
const myLength = myLengthTab.number('Lookback Period for Median', 40, { min: 10, max: 41 });
const myShowMedian = myLengthTab.boolean('Show Median Line', true);

const myShadingTab = input.tab('Shading');
const myShowBg = myShadingTab.boolean('Shade When PE Below Median', true);

// Fetch quarterly fundamentals. We request enough quarters to cover
// the lookback window plus 4 extra quarters needed to build a TTM
// net income figure (sum of last 4 quarterly net income values).
// NOTE: request.fundamental() only supports between 1 and 49 quarters,
// so we clamp the requested amount to that hard limit.
// NOTE: "shares_outstanding" is not a valid metric name in our
// fundamentals API (it threw "unknown_metric"). We use "market_cap"
// instead, which lets us compute PE as market_cap / net_income_ttm,
// without needing shares outstanding or close price at all.
const myQuartersNeeded = Math.min(49, myLength + 8);
const myFundamentalData = await request.fundamental(
	current.ticker,
	['market_cap', 'net_income'],
	myQuartersNeeded
);
assert(!myFundamentalData.error, "Error fetching fundamentals: " + myFundamentalData.error);

const myMarketCapRecords = myFundamentalData.market_cap || [];
const myNetIncomeRecords = myFundamentalData.net_income || [];

// Records come most-recent-first; reverse to chronological order.
const myMarketCapChrono = [...myMarketCapRecords].reverse();
const myNetIncomeChrono = [...myNetIncomeRecords].reverse();

// Build TTM net income (sum of trailing 4 quarters) for each quarterly point,
// matched by index position on the net income chronological array.
const myNetIncomeTtm = myNetIncomeChrono.map((_rec, _idx) => {
	if (_idx < 3) return null;
	const mySum = myNetIncomeChrono[_idx].value + myNetIncomeChrono[_idx - 1].value +
		myNetIncomeChrono[_idx - 2].value + myNetIncomeChrono[_idx - 3].value;
	return mySum;
});

const myNetIncomeTimestamps = myNetIncomeChrono.map(_rec => _rec.reportdate);
const myMarketCapTimestamps = myMarketCapChrono.map(_rec => _rec.reportdate);
const myMarketCapValues = myMarketCapChrono.map(_rec => _rec.value);

// Land market cap and TTM net income onto the chart's time series.
const myMarketCapLanded = interpolate_sparse_series(
	land_points_onto_series(myMarketCapTimestamps, myMarketCapValues, time, 'le'),
	'constant'
);
const myNetIncomeTtmLanded = interpolate_sparse_series(
	land_points_onto_series(myNetIncomeTimestamps, myNetIncomeTtm, time, 'le'),
	'constant'
);

// pe_ratio = market_cap / net_income_ttm
const myPeRatio = for_every(myMarketCapLanded, myNetIncomeTtmLanded, (_marketCap, _netIncome) => {
	if (_marketCap == null || _netIncome == null || _netIncome === 0) return null;
	return _marketCap / _netIncome;
});

// Median over trailing window, matching ta.median(pe_ratio, length)
const myPeMedian = sliding_window_function(myPeRatio, myLength, _values => {
	const myValid = _values.filter(_v => _v != null && !isNaN(_v));
	if (myValid.length === 0) return null;
	const mySorted = [...myValid].sort((_a, _b) => _a - _b);
	const myMid = Math.floor(mySorted.length / 2);
	return mySorted.length % 2 === 0 ? (mySorted[myMid - 1] + mySorted[myMid]) / 2 : mySorted[myMid];
});

const myPeColor = for_every(myPeRatio, myPeMedian, (_pe, _median) => {
	if (_pe == null || _median == null) return 'gray';
	return _pe > _median ? '#ef5350' : '#26a69a';
});

paint(myPeRatio, { name: 'PeRatio', style: 'line', color: myPeColor, thickness: 1 });
paint(myShowMedian ? myPeMedian : constants.empty_series, { name: 'MedianPe', style: 'line', color: 'black', thickness: 2 });

// Approximate "shade below median" using candle coloring on the main chart,
// since bgcolor-style full panel shading is not available in this API.
const myBelowMedianColor = for_every(myPeRatio, myPeMedian, (_pe, _median) => {
	if (!myShowBg) return null;
	if (_pe == null || _median == null) return null;
	return _pe < _median ? 'rgba(7,194,13,0.25)' : null;
});
color_candles(myBelowMedianColor);

// Register signals usable in scanners, alerts and strategies
const mySignalBelowMedian = for_every(myPeRatio, myPeMedian, (_pe, _median) => _pe != null && _median != null && _pe < _median);
const mySignalAboveMedian = for_every(myPeRatio, myPeMedian, (_pe, _median) => _pe != null && _median != null && _pe > _median);
register_signal(mySignalBelowMedian, "PE Below Median");
register_signal(mySignalAboveMedian, "PE Above Median");