describe_indicator('PE Ratio Quarter Vs Median', 'lower');

// NOTE: This is a best-effort conversion of the Pine Script indicator.
// The "MarketCap / NetIncome" method required a shares-outstanding
// fundamental metric. The previous attempt used "total_shares_outstanding"
// which is not a valid metric in this platform's fundamentals API, and
// there is no documented substitute metric for shares outstanding or
// market cap. Because of that, the MarketCap/NetIncome method has been
// removed; the indicator now always computes P/E using EPS TTM only.
const myPeSourceTab = input.tab('P/E Settings');
const myLength = myPeSourceTab.number('Lookback Period for Median', 250, { min: 30, max: 2000 });
const myShowMedian = myPeSourceTab.boolean('Show Median Line', true);

const myShadingTab = input.tab('Shading');
const myShowBelowMedianSignal = myShadingTab.boolean('Enable Below Median Signal', true);

// Fetch quarterly fundamentals. The API only allows up to 49 quarters,
// so we request the maximum allowed (49 quarters, ~12 years) in order
// to build a trailing-twelve-month (TTM) EPS series, similarly to
// Pine's request.financial(..., "TTM") behavior.
const myQuartersNeeded = 49;
const myFundamentalData = await request.fundamental(
	current.ticker,
	['eps_basic'],
	myQuartersNeeded
);
assert(!myFundamentalData.error, `Error fetching fundamentals: "${myFundamentalData.error}"`);

const myEpsQuarterly = myFundamentalData.eps_basic || [];

// Records come back "most recent first". Build TTM (sum of last 4 quarters)
// series for EPS, aligned to each report date.
function myBuildTtmSeries(_quarterlyRecords) {
	const myResult = [];
	for (let myIndex = 0; myIndex < _quarterlyRecords.length; myIndex += 1) {
		if (myIndex + 3 < _quarterlyRecords.length) {
			const mySum =
				_quarterlyRecords[myIndex].value +
				_quarterlyRecords[myIndex + 1].value +
				_quarterlyRecords[myIndex + 2].value +
				_quarterlyRecords[myIndex + 3].value;
			myResult.push({ reportdate: _quarterlyRecords[myIndex].reportdate, value: mySum });
		}
	}
	// re-sort ascending by date for landing onto chart series
	return myResult.sort((_a, _b) => _a.reportdate - _b.reportdate);
}

const myEpsTtmSorted = myBuildTtmSeries(myEpsQuarterly);
const myEpsTtmTimestamps = myEpsTtmSorted.map(_record => _record.reportdate);
const myEpsTtmValues = myEpsTtmSorted.map(_record => _record.value);

// Land EPS TTM onto the chart's time series ("le" = use the most recent
// known report as of each candle, same intent as Pine's
// request.financial lookahead_off behavior).
const myEpsTtmLanded = interpolate_sparse_series(
	land_points_onto_series(myEpsTtmTimestamps, myEpsTtmValues, time, 'le'),
	'constant'
);

// === Current P/E (EPS TTM method) ===
const myPeRatio = for_every(close, myEpsTtmLanded, (_close, _eps) => {
	if (_eps === null || _eps === undefined || _eps === 0) return null;
	return _close / _eps;
});

// === Median (rolling, trailing window) ===
function myMedianOfValues(_values) {
	const myValid = _values.filter(_v => _v !== null && _v !== undefined && !isNaN(_v));
	if (myValid.length === 0) return null;
	const mySorted = [...myValid].sort((_a, _b) => _a - _b);
	const myMid = Math.floor(mySorted.length / 2);
	return mySorted.length % 2 !== 0 ? mySorted[myMid] : (mySorted[myMid - 1] + mySorted[myMid]) / 2;
}
const myPeMedian = sliding_window_function(myPeRatio, myLength, myMedianOfValues);

const myPeColor = for_every(myPeRatio, myPeMedian, (_pe, _median) => {
	if (_pe === null || _median === null) return 'gray';
	return _pe > _median ? '#ef5350' : '#26a69a';
});

// === Plotting ===
paint(myPeRatio, { name: 'PriceToEarningsRatio', style: 'line', color: myPeColor, thickness: 1 });
paint(myShowMedian ? myPeMedian : series_of(null), { name: 'MedianPE', style: 'line', color: 'black', thickness: 2 });

// === Below/Above median signals, for scanners/alerts/strategies ===
const myBelowMedianSignal = for_every(myPeRatio, myPeMedian, (_pe, _median) => {
	if (!myShowBelowMedianSignal) return false;
	return _pe !== null && _median !== null && _pe < _median;
});
register_signal(myBelowMedianSignal, 'PE Below Median');

const myAboveMedianSignal = for_every(myPeRatio, myPeMedian, (_pe, _median) => {
	if (!myShowBelowMedianSignal) return false;
	return _pe !== null && _median !== null && _pe > _median;
});
register_signal(myAboveMedianSignal, 'PE Above Median');