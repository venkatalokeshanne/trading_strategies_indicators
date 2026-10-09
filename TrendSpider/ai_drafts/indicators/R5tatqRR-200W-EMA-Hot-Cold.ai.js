describe_indicator('200W EMA Heat', 'lower', { decimals: 2 });

// ───────────────────────────── Inputs ─────────────────────────────
const myEmaLength = input.number('EMA Length', 200, { min: 10, max: 500 });
const myPctLookback = input.number('Percentile Lookback', 260, { min: 20, max: 1000 });
const myAvoidRepaint = input.boolean('Avoid Repaint', true);
const myColdColor = input.color('Cold color', '#2962FF');
const myNeutralColor = input.color('Neutral color', '#787B86');
const myHotColor = input.color('Hot color', '#FF1744');
const myTinycolor = library('tinycolor2');

// ───────────────────────────── Weekly calc ─────────────────────────────
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

const myEma200w = ema(myWeeklyData.close, myEmaLength);
const myPct = for_every(myWeeklyData.close, myEma200w, (_c, _e) => _e ? ((_c - _e) / _e) * 100 : null);

// ta.percentrank(pct, length): % of values in the trailing window (length+1 values,
// current included) that are strictly less than the current value.
const myRank = sliding_window_function(myPct, myPctLookback + 1, _values => {
	const myCurrent = _values[_values.length - 1];
	let myCountLess = 0;
	for (let myIndex = 0; myIndex < _values.length - 1; myIndex += 1) {
		if (_values[myIndex] < myCurrent) {
			myCountLess += 1;
		}
	}
	return (myCountLess / (_values.length - 1)) * 100;
});

// Avoid repaint: use last confirmed weekly bar (shift forward by 1 week of lag)
const myOffsetPct = myAvoidRepaint ? shift(myPct, 1) : myPct;
const myOffsetRank = myAvoidRepaint ? shift(myRank, 1) : myRank;

// Land weekly values onto the current chart (constant interpolation keeps it non-repainting)
const myPctLanded = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myOffsetPct, time, 'ge'),
	'constant'
);
const myRankLanded = interpolate_sparse_series(
	land_points_onto_series(myWeeklyData.time, myOffsetRank, time, 'ge'),
	'constant'
);

// ───────────────────────────── Color: diverging gradient by percentile rank ─────────────────────────────
const myBarColor = for_every(myRankLanded, _rank => {
	if (_rank === null) {
		return myNeutralColor;
	}
	if (_rank < 50) {
		return myTinycolor.mix(myColdColor, myNeutralColor, (_rank / 50) * 100).toHexString();
	}
	return myTinycolor.mix(myNeutralColor, myHotColor, ((_rank - 50) / 50) * 100).toHexString();
});

// ───────────────────────────── Plots ─────────────────────────────
paint(myPctLanded, { name: 'PctDistance', style: 'column', color: myBarColor });
paint(horizontal_line(0), { name: 'ZeroLine', style: 'dotted', color: 'gray' });

// ───────────────────────────── Signals ─────────────────────────────
const myOverheatedSignal = for_every(myRankLanded, _rank => _rank !== null && _rank >= 90);
const myDeeplyColdSignal = for_every(myRankLanded, _rank => _rank !== null && _rank <= 10);
register_signal(myOverheatedSignal, 'Overheated Top 10 Percent');
register_signal(myDeeplyColdSignal, 'Deeply Cold Bottom 10 Percent');