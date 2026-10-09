describe_indicator('MTF Daily Bias Dashboard', 'overlay');

// NOTE: Pine's `request.security(..., lookahead_on)` combined with
// `close[1]`/`close[2]` effectively uses the LAST CONFIRMED (closed) bar
// of the higher timeframe, mapped forward onto every lower timeframe bar
// until the next HTF bar closes. We reproduce this by fetching each
// timeframe's history, shifting series by 1 bar to get "confirmed" values,
// computing bias on that higher-timeframe series, then landing those
// values onto the current chart using a "less-or-equal" timestamp match
// with constant interpolation (no forward-looking repainting).

const myDailyTF = input.text('Daily timeframe', 'D');
const myFourHourTF = input.text('4-hour timeframe', '240');
const myFifteenMinTF = input.text('15-minute timeframe', '15');
const myEmaPeriod = input.number('EMA period', 20, { min: 1, max: 500 });

// Fetches history and computes a bias series for a given timeframe.
async function myComputeBiasForTimeframe(_timeframe) {
	const myData = await request.history(current.ticker, _timeframe);
	assert(!myData.error, `Error fetching data for timeframe ${_timeframe}: ${myData.error}`);

	const myEma = ema(myData.close, myEmaPeriod);

	// "confirmed" values = previous completed bar (shift by 1)
	const myConfirmedClose = shift(myData.close, 1);
	const myPreviousClose = shift(myData.close, 2);
	const myConfirmedEma = shift(myEma, 1);

	const myBias = for_every(myConfirmedClose, myPreviousClose, myConfirmedEma, (_cClose, _pClose, _cEma) => {
		if (_cClose == null || _pClose == null || _cEma == null) return 0;
		if (_cClose > _cEma && _cClose > _pClose) return 1;
		if (_cClose < _cEma && _cClose < _pClose) return -1;
		return 0;
	});

	return { time: myData.time, bias: myBias };
}

const [myDailyData, myFourHourData, myFifteenMinData] = await Promise.all([
	myComputeBiasForTimeframe(myDailyTF),
	myComputeBiasForTimeframe(myFourHourTF),
	myComputeBiasForTimeframe(myFifteenMinTF)
]);

// Land each timeframe's bias onto the current chart's timestamps,
// using "le" (last known closed bar at or before current time)
// and constant interpolation to avoid any lookahead/repainting.
const myDailyLanded = interpolate_sparse_series(
	land_points_onto_series(myDailyData.time, myDailyData.bias, time, 'le'),
	'constant'
);
const myFourHourLanded = interpolate_sparse_series(
	land_points_onto_series(myFourHourData.time, myFourHourData.bias, time, 'le'),
	'constant'
);
const myFifteenMinLanded = interpolate_sparse_series(
	land_points_onto_series(myFifteenMinData.time, myFifteenMinData.bias, time, 'le'),
	'constant'
);

// Register signals for use in scanners, alerts and strategies.
register_signal(for_every(myDailyLanded, _b => _b == 1), 'Daily Bullish Bias');
register_signal(for_every(myDailyLanded, _b => _b == -1), 'Daily Bearish Bias');
register_signal(for_every(myDailyLanded, _b => _b == 0), 'Daily Neutral Bias');

register_signal(for_every(myFourHourLanded, _b => _b == 1), 'FourHour Bullish Bias');
register_signal(for_every(myFourHourLanded, _b => _b == -1), 'FourHour Bearish Bias');
register_signal(for_every(myFourHourLanded, _b => _b == 0), 'FourHour Neutral Bias');

register_signal(for_every(myFifteenMinLanded, _b => _b == 1), 'FifteenMin Bullish Bias');
register_signal(for_every(myFifteenMinLanded, _b => _b == -1), 'FifteenMin Bearish Bias');
register_signal(for_every(myFifteenMinLanded, _b => _b == 0), 'FifteenMin Neutral Bias');

// Table position input.
const myTablePosition = input.select('Table position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left']);

// Helpers to format the dashboard.
function myBiasText(_bias) {
	if (_bias == 1) return 'Bullish';
	if (_bias == -1) return 'Bearish';
	return 'Neutral';
}

function myBiasColor(_bias) {
	if (_bias == 1) return 'rgba(8,153,129,0.75)';
	if (_bias == -1) return 'rgba(242,54,69,0.75)';
	return 'rgba(128,128,128,0.6)';
}

function myTimeframeLabel(_timeframe) {
	if (_timeframe == 'D') return '1D';
	if (_timeframe == '240') return '4H';
	if (_timeframe == '15') return '15m';
	return _timeframe;
}

const myLastDailyBias = myDailyLanded[myDailyLanded.length - 1];
const myLastFourHourBias = myFourHourLanded[myFourHourLanded.length - 1];
const myLastFifteenMinBias = myFifteenMinLanded[myFifteenMinLanded.length - 1];

paint_overlay('MTFBiasDashboard', { position: myTablePosition }, {
	rows: [
		{
			cells: [
				{ text: 'Timeframe', color: '#ffffff', background_color: 'rgba(0,0,0,0.8)' },
				{ text: 'Bias', color: '#ffffff', background_color: 'rgba(0,0,0,0.8)' }
			]
		},
		{
			cells: [
				{ text: myTimeframeLabel(myDailyTF), color: '#ffffff', background_color: 'rgba(0,0,0,0.2)' },
				{ text: myBiasText(myLastDailyBias), color: '#ffffff', background_color: myBiasColor(myLastDailyBias) }
			]
		},
		{
			cells: [
				{ text: myTimeframeLabel(myFourHourTF), color: '#ffffff', background_color: 'rgba(0,0,0,0.2)' },
				{ text: myBiasText(myLastFourHourBias), color: '#ffffff', background_color: myBiasColor(myLastFourHourBias) }
			]
		},
		{
			cells: [
				{ text: myTimeframeLabel(myFifteenMinTF), color: '#ffffff', background_color: 'rgba(0,0,0,0.2)' },
				{ text: myBiasText(myLastFifteenMinBias), color: '#ffffff', background_color: myBiasColor(myLastFifteenMinBias) }
			]
		}
	]
});

// Overlay plot of the bias values (optional visual reference), forced
// onto its own scale since bias is -1/0/1, not a price value.
paint(myDailyLanded, { name: 'DailyBias', color: '#089981', style: 'line', forceUsePriceAxis: false, hidden: true });