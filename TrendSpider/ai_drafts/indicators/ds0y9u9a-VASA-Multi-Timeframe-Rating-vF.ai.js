// ============================================================================
// VASA Multi-Timeframe Rating - converted from TradingView Pine Script
// Reproduces: 3 timeframe EMA fast/slow trend + RSI momentum fused rating.
// NON-REPAINTING: we shift each HTF series by one additional bar before
// landing it onto the current chart, which mimics Pine's "_expr[1]" trick
// (use the last fully CLOSED higher timeframe value only).
// ============================================================================

describe_indicator('VASA Multi Timeframe Rating', 'price');

const myTabTimeframes = input.tab('Timeframes');
const myTimeframe1 = myTabTimeframes.select('Timeframe 1', '15', constants.time_frames);
const myTimeframe2 = myTabTimeframes.select('Timeframe 2', '60', constants.time_frames);
const myTimeframe3 = myTabTimeframes.select('Timeframe 3', '240', constants.time_frames);

const myTabSignals = input.tab('Signals');
const myEmaFastLength = myTabSignals.number('EMA fast', 21, { min: 1, max: 500 });
const myEmaSlowLength = myTabSignals.number('EMA slow', 50, { min: 1, max: 500 });
const myRsiLength = myTabSignals.number('RSI length', 14, { min: 1, max: 500 });

const myTabStyle = input.tab('Style');
const myBullColor = myTabStyle.color('Bull colour', '#15803d');
const myBearColor = myTabStyle.color('Bear colour', '#b91c1c');
const myTablePosition = myTabStyle.select('Table position', 'Top right', ['Top right', 'Top left', 'Bottom right', 'Bottom left']);

// fetch the three higher timeframes in parallel
const [myHistoryTf1, myHistoryTf2, myHistoryTf3] = await Promise.all([
	request.history(current.ticker, myTimeframe1),
	request.history(current.ticker, myTimeframe2),
	request.history(current.ticker, myTimeframe3)
]);

assert(!myHistoryTf1.error, 'Error fetching Timeframe 1 data: ' + myHistoryTf1.error);
assert(!myHistoryTf2.error, 'Error fetching Timeframe 2 data: ' + myHistoryTf2.error);
assert(!myHistoryTf3.error, 'Error fetching Timeframe 3 data: ' + myHistoryTf3.error);

// Computes { score, trendUp, momUp } landed onto the current chart's candles,
// using a one-bar shift to only ever use fully closed HTF bars (non-repainting).
function myComputeScoreForTimeframe(_historyData) {
	const myEmaFast = shift(ema(_historyData.close, myEmaFastLength), 1);
	const myEmaSlow = shift(ema(_historyData.close, myEmaSlowLength), 1);
	const myRsiValue = shift(rsi(_historyData.close, myRsiLength), 1);

	const myEmaFastLanded = interpolate_sparse_series(
		land_points_onto_series(_historyData.time, myEmaFast, time, 'ge'),
		'constant'
	);
	const myEmaSlowLanded = interpolate_sparse_series(
		land_points_onto_series(_historyData.time, myEmaSlow, time, 'ge'),
		'constant'
	);
	const myRsiLanded = interpolate_sparse_series(
		land_points_onto_series(_historyData.time, myRsiValue, time, 'ge'),
		'constant'
	);

	const myTrendUp = for_every(myEmaFastLanded, myEmaSlowLanded, (_ef, _es) => _ef > _es);
	const myMomUp = for_every(myRsiLanded, _r => _r > 50);
	const myScore = for_every(myTrendUp, myMomUp, (_tu, _mu) => (_tu ? 1 : -1) + (_mu ? 1 : -1));

	return { score: myScore, trendUp: myTrendUp, momUp: myMomUp };
}

const myResultTf1 = myComputeScoreForTimeframe(myHistoryTf1);
const myResultTf2 = myComputeScoreForTimeframe(myHistoryTf2);
const myResultTf3 = myComputeScoreForTimeframe(myHistoryTf3);

// ---------- register signals for scanning / alerts / strategy tester ----------
register_signal(myResultTf1.trendUp, 'Timeframe 1 Trend Up');
register_signal(myResultTf1.momUp, 'Timeframe 1 Momentum Up');
register_signal(myResultTf2.trendUp, 'Timeframe 2 Trend Up');
register_signal(myResultTf2.momUp, 'Timeframe 2 Momentum Up');
register_signal(myResultTf3.trendUp, 'Timeframe 3 Trend Up');
register_signal(myResultTf3.momUp, 'Timeframe 3 Momentum Up');

register_signal(for_every(myResultTf1.score, _s => _s >= 2), 'Timeframe 1 Bull Rating');
register_signal(for_every(myResultTf1.score, _s => _s <= -2), 'Timeframe 1 Bear Rating');
register_signal(for_every(myResultTf2.score, _s => _s >= 2), 'Timeframe 2 Bull Rating');
register_signal(for_every(myResultTf2.score, _s => _s <= -2), 'Timeframe 2 Bear Rating');
register_signal(for_every(myResultTf3.score, _s => _s >= 2), 'Timeframe 3 Bull Rating');
register_signal(for_every(myResultTf3.score, _s => _s <= -2), 'Timeframe 3 Bear Rating');

const myAllBullish = for_every(
	myResultTf1.score, myResultTf2.score, myResultTf3.score,
	(_s1, _s2, _s3) => _s1 >= 2 && _s2 >= 2 && _s3 >= 2
);
register_signal(myAllBullish, 'All Timeframes Bull');

const myAllBearish = for_every(
	myResultTf1.score, myResultTf2.score, myResultTf3.score,
	(_s1, _s2, _s3) => _s1 <= -2 && _s2 <= -2 && _s3 <= -2
);
register_signal(myAllBearish, 'All Timeframes Bear');

// ---------- rating helpers (match Pine f_lab / f_bg) ----------
function myLabelOfScore(_score) {
	if (_score >= 2) return 'Bull';
	if (_score === 1) return 'Lean bull';
	if (_score === 0) return 'Mixed';
	if (_score === -1) return 'Lean bear';
	return 'Bear';
}

function myBackgroundOfScore(_score) {
	if (_score > 0) return myBullColor;
	if (_score < 0) return myBearColor;
	return '#64748b';
}

function myPositionOf(_pos) {
	if (_pos === 'Top left') return 'top_left';
	if (_pos === 'Bottom right') return 'bottom_right';
	if (_pos === 'Bottom left') return 'bottom_left';
	return 'top_right';
}

// last index values, used only to build the "last bar" table
const myLastIndex = close.length - 1;

const myLastScore1 = myResultTf1.score[myLastIndex];
const myLastTrend1 = myResultTf1.trendUp[myLastIndex];
const myLastMom1 = myResultTf1.momUp[myLastIndex];

const myLastScore2 = myResultTf2.score[myLastIndex];
const myLastTrend2 = myResultTf2.trendUp[myLastIndex];
const myLastMom2 = myResultTf2.momUp[myLastIndex];

const myLastScore3 = myResultTf3.score[myLastIndex];
const myLastTrend3 = myResultTf3.trendUp[myLastIndex];
const myLastMom3 = myResultTf3.momUp[myLastIndex];

function myTableRow(_tfLabel, _trendUp, _momUp, _score) {
	return {
		cells: [
			{ text: _tfLabel, color: '#ffffff' },
			{ text: _trendUp ? 'Up' : 'Down', color: _trendUp ? myBullColor : myBearColor },
			{ text: _momUp ? 'Up' : 'Down', color: _momUp ? myBullColor : myBearColor },
			{ text: myLabelOfScore(_score), color: '#ffffff', background_color: myBackgroundOfScore(_score) }
		]
	};
}

paint_overlay('VASAMultiTimeframeRating', { position: myPositionOf(myTablePosition) }, {
	rows: [
		{
			cells: [
				{ text: 'TF', color: '#ffffff', background_color: '#16233b' },
				{ text: 'Trend', color: '#ffffff', background_color: '#16233b' },
				{ text: 'Mom', color: '#ffffff', background_color: '#16233b' },
				{ text: 'Rating', color: '#ffffff', background_color: '#16233b' }
			]
		},
		myTableRow(myTimeframe1, myLastTrend1, myLastMom1, myLastScore1),
		myTableRow(myTimeframe2, myLastTrend2, myLastMom2, myLastScore2),
		myTableRow(myTimeframe3, myLastTrend3, myLastMom3, myLastScore3)
	]
});