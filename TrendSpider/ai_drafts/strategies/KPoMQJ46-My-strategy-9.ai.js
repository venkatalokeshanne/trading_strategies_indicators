describe_indicator('SMA Crossover with MTF High Low', 'price');

// SMA lengths for the crossover strategy signals
const myFastLength = input.number('Fast SMA Length', 14, { min: 1, max: 500 });
const mySlowLength = input.number('Slow SMA Length', 28, { min: 1, max: 500 });

const myFastSMA = sma(close, myFastLength);
const mySlowSMA = sma(close, mySlowLength);

// Crossover / crossunder detection (equivalent to ta.crossover / ta.crossunder)
const myLongCondition = for_every(myFastSMA, mySlowSMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastSMA[_index - 1];
	const myPrevSlow = mySlowSMA[_index - 1];
	if (myPrevFast === null || myPrevSlow === null || _fast === null || _slow === null) return false;
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondition = for_every(myFastSMA, mySlowSMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastSMA[_index - 1];
	const myPrevSlow = mySlowSMA[_index - 1];
	if (myPrevFast === null || myPrevSlow === null || _fast === null || _slow === null) return false;
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

// Register these as scanner/alert/strategy-usable signals
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// Paint the SMAs on the price chart
paint(myFastSMA, { name: 'Fast SMA', color: '#26A69A', thickness: 1 });
paint(mySlowSMA, { name: 'Slow SMA', color: '#EF5350', thickness: 1 });

// Mark long/short signal bars on the chart
const myLongMarks = for_every(myLongCondition, close, (_cond, _c) => _cond ? _c : null);
const myShortMarks = for_every(myShortCondition, close, (_cond, _c) => _cond ? _c : null);

paint(myLongMarks, { name: 'Long Signal', color: '#26A69A', style: 'labels_below' });
paint(myShortMarks, { name: 'Short Signal', color: '#EF5350', style: 'labels_above' });

// Multi-timeframe High/Low levels. These are fetched via request.history
// and landed onto the current chart's time series using "constant"
// interpolation to avoid repainting/look-ahead issues.
const [myDailyData, myHourlyData, my30MinData, my15MinData] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '30'),
	request.history(current.ticker, '15')
]);

assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);
assert(!myHourlyData.error, 'Error fetching Hourly data: ' + myHourlyData.error);
assert(!my30MinData.error, 'Error fetching 30min data: ' + my30MinData.error);
assert(!my15MinData.error, 'Error fetching 15min data: ' + my15MinData.error);

function myLandSeries(_data, _series) {
	const myLanded = land_points_onto_series(_data.time, _series, time, 'le');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myDailyHigh = myLandSeries(myDailyData, myDailyData.high);
const myDailyLow = myLandSeries(myDailyData, myDailyData.low);
const myHourlyHigh = myLandSeries(myHourlyData, myHourlyData.high);
const myHourlyLow = myLandSeries(myHourlyData, myHourlyData.low);
const my30MinHigh = myLandSeries(my30MinData, my30MinData.high);
const my30MinLow = myLandSeries(my30MinData, my30MinData.low);
const my15MinHigh = myLandSeries(my15MinData, my15MinData.high);
const my15MinLow = myLandSeries(my15MinData, my15MinData.low);

paint(myDailyHigh, { name: 'Daily High', color: 'orange', thickness: 2 });
paint(myDailyLow, { name: 'Daily Low', color: 'orange', thickness: 2 });

paint(myHourlyHigh, { name: 'Hourly High', color: 'blue', thickness: 2 });
paint(myHourlyLow, { name: 'Hourly Low', color: 'blue', thickness: 2 });

paint(my30MinHigh, { name: 'ThirtyMin High', color: 'green', thickness: 2 });
paint(my30MinLow, { name: 'ThirtyMin Low', color: 'green', thickness: 2 });

paint(my15MinHigh, { name: 'FifteenMin High', color: 'red', thickness: 2 });
paint(my15MinLow, { name: 'FifteenMin Low', color: 'red', thickness: 2 });