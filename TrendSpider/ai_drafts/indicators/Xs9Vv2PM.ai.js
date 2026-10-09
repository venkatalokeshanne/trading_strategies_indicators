describe_indicator('Dashboard Tendance Multi UT 2 EMA', 'price');

// ==========================================
// INPUTS
// ==========================================
const emaTab = input.tab('EMA Settings');
const myLenFast = emaTab.number('Fast EMA Length', 20, { min: 1, max: 500 });
const myLenSlow = emaTab.number('Slow EMA Length', 50, { min: 1, max: 500 });
const myShowEma = emaTab.boolean('Show EMAs on chart', true);

const dashTab = input.tab('Dashboard Settings');
const myDashPosition = dashTab.select('Dashboard Position', 'top_right', [
	'top_right', 'bottom_right', 'top_left', 'bottom_left', 'top_center', 'bottom_center'
]);

// ==========================================
// CURRENT TIME FRAME EMAs
// ==========================================
const myEmaFastCurrent = ema(close, myLenFast);
const myEmaSlowCurrent = ema(close, myLenSlow);

paint(myShowEma ? myEmaFastCurrent : constants.empty_series, { name: 'EMA Fast', color: '#26a69a', thickness: 2 });
paint(myShowEma ? myEmaSlowCurrent : constants.empty_series, { name: 'EMA Slow', color: '#ef5350', thickness: 2 });

// ==========================================
// TREND LOGIC
// ==========================================
function myGetTrend(_price, _emaF, _emaS) {
	if (_price > _emaF && _emaF > _emaS) return 'BULLISH';
	if (_price < _emaF && _emaF < _emaS) return 'BEARISH';
	return 'NEUTRAL';
}

function myGetTrendColor(_trend) {
	if (_trend === 'BULLISH') return '#26a69a';
	if (_trend === 'BEARISH') return '#ef5350';
	return '#787b86';
}

// ==========================================
// MULTI TIME FRAME DATA
// ==========================================
const [myWeeklyData, myDailyData, myH4Data] = await Promise.all([
	request.history(current.ticker, 'W'),
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '240')
]);

assert(!myWeeklyData.error, 'Error fetching Weekly data: ' + myWeeklyData.error);
assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);
assert(!myH4Data.error, 'Error fetching H4 data: ' + myH4Data.error);

const myWeeklyEmaFast = ema(myWeeklyData.close, myLenFast);
const myWeeklyEmaSlow = ema(myWeeklyData.close, myLenSlow);
const myDailyEmaFast = ema(myDailyData.close, myLenFast);
const myDailyEmaSlow = ema(myDailyData.close, myLenSlow);
const myH4EmaFast = ema(myH4Data.close, myLenFast);
const myH4EmaSlow = ema(myH4Data.close, myLenSlow);

const myLastWeeklyIndex = myWeeklyData.close.length - 1;
const myLastDailyIndex = myDailyData.close.length - 1;
const myLastH4Index = myH4Data.close.length - 1;

const myTrendW = myGetTrend(
	myWeeklyData.close[myLastWeeklyIndex],
	myWeeklyEmaFast[myLastWeeklyIndex],
	myWeeklyEmaSlow[myLastWeeklyIndex]
);

const myTrendD = myGetTrend(
	myDailyData.close[myLastDailyIndex],
	myDailyEmaFast[myLastDailyIndex],
	myDailyEmaSlow[myLastDailyIndex]
);

const myTrendH4 = myGetTrend(
	myH4Data.close[myLastH4Index],
	myH4EmaFast[myLastH4Index],
	myH4EmaSlow[myLastH4Index]
);

// ==========================================
// DASHBOARD TABLE (OVERLAY)
// ==========================================
paint_overlay('MultiTimeFrameDashboard', { position: myDashPosition }, {
	rows: [{
		cells: [
			{ text: 'UT', background_color: '#1e222d', color: '#ffffff' },
			{ text: 'TENDANCE', background_color: '#1e222d', color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'Weekly', background_color: '#2a2e39', color: '#ffffff' },
			{ text: myTrendW, background_color: myGetTrendColor(myTrendW), color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'Daily', background_color: '#2a2e39', color: '#ffffff' },
			{ text: myTrendD, background_color: myGetTrendColor(myTrendD), color: '#ffffff' }
		]
	}, {
		cells: [
			{ text: 'H4', background_color: '#2a2e39', color: '#ffffff' },
			{ text: myTrendH4, background_color: myGetTrendColor(myTrendH4), color: '#ffffff' }
		]
	}]
});

// ==========================================
// SCANNER / ALERT / STRATEGY SIGNALS
// register_signal() requires a full series (one value per candle), not a
// single boolean. Since the trends above are computed only for the "latest"
// candle of each time frame, we broadcast that single boolean value across
// the entire series using series_of(), so every candle holds the same
// (current) trend state.
// ==========================================
register_signal(series_of(myTrendW === 'BULLISH'), 'Weekly Trend Bullish');
register_signal(series_of(myTrendW === 'BEARISH'), 'Weekly Trend Bearish');
register_signal(series_of(myTrendD === 'BULLISH'), 'Daily Trend Bullish');
register_signal(series_of(myTrendD === 'BEARISH'), 'Daily Trend Bearish');
register_signal(series_of(myTrendH4 === 'BULLISH'), 'H4 Trend Bullish');
register_signal(series_of(myTrendH4 === 'BEARISH'), 'H4 Trend Bearish');

register_signal(
	series_of(myTrendW === 'BULLISH' && myTrendD === 'BULLISH' && myTrendH4 === 'BULLISH'),
	'All Timeframes Bullish'
);

register_signal(
	series_of(myTrendW === 'BEARISH' && myTrendD === 'BEARISH' && myTrendH4 === 'BEARISH'),
	'All Timeframes Bearish'
);