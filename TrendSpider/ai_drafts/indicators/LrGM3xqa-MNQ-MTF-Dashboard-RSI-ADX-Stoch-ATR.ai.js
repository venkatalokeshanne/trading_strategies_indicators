// This indicator fetches 5m/15m/1H/4H/1D data and recomputes
// RSI / ADX / Stochastic / ATR on each timeframe, mirroring the
// Pine Script "MNQ MTF Dashboard" logic as closely as the Custom JS
// API allows. The table is reproduced as an overlay, and bias signals
// are exposed via register_signal() for scanning/alerts/backtesting.
describe_indicator('MNQ MTF Dashboard RSIADXStochATR');

const myTablePosition = input.select('Table Position', 'top_right', ['top_right', 'top_left', 'bottom_right', 'bottom_left', 'middle_right']);
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myAdxLength = input.number('ADXDI Length', 14, { min: 1, max: 200 });
const myStochLength = input.number('Stoch Percent K Length', 14, { min: 1, max: 200 });
const myStochSmoothK = input.number('Stoch Percent K Smooth', 3, { min: 1, max: 50 });
const myStochSmoothD = input.number('Stoch Percent D Smooth', 3, { min: 1, max: 50 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 200 });

// Reproduces Pine's custom adx() function (DI-based ADX, using Wilder's RMA via wildma()).
function myComputeAdx(myHigh, myLow, myClose, myDiLen, myAdxLen) {
	const myUp = sub(myHigh, shift(myHigh, 1));
	const myDown = mult(sub(myLow, shift(myLow, 1)), -1);

	const myPlusDM = for_every(myUp, myDown, (_u, _d) => (_u > _d && _u > 0) ? _u : 0);
	const myMinusDM = for_every(myDown, myUp, (_d, _u) => (_d > _u && _d > 0) ? _d : 0);

	const myTrur = atr(myHigh, myLow, myClose, myDiLen);

	const myPlus = for_every(wildma(myPlusDM, myDiLen), myTrur, (_p, _t) => _t ? (100 * _p / _t) : 0);
	const myMinus = for_every(wildma(myMinusDM, myDiLen), myTrur, (_m, _t) => _t ? (100 * _m / _t) : 0);

	const mySum = add(myPlus, myMinus);
	const myDiffRatio = for_every(myPlus, myMinus, mySum, (_p, _m, _s) => Math.abs(_p - _m) / (_s === 0 ? 1 : _s));

	return mult(wildma(myDiffRatio, myAdxLen), 100);
}

// Reproduces getMetrics(): rsi, adx, %K, %D, atr for a given OHLC data set.
function myComputeMetrics(myData) {
	const myRsi = rsi(myData.close, myRsiLength);
	const myAdx = myComputeAdx(myData.high, myData.low, myData.close, myAdxLength, myAdxLength);
	const myK = sma(stochastic(myData.close, myData.high, myData.low, myStochLength), myStochSmoothK);
	const myD = sma(myK, myStochSmoothD);
	const myAtr = atr(myData.high, myData.low, myData.close, myAtrLength);
	return { rsi: myRsi, adx: myAdx, k: myK, d: myD, atr: myAtr, time: myData.time };
}

const [myData5, myData15, myData60, myData240, myDataD] = await Promise.all([
	request.history(current.ticker, '5'),
	request.history(current.ticker, '15'),
	request.history(current.ticker, '60'),
	request.history(current.ticker, '240'),
	request.history(current.ticker, 'D')
]);

assert(!myData5.error, 'Error fetching 5m data: ' + myData5.error);
assert(!myData15.error, 'Error fetching 15m data: ' + myData15.error);
assert(!myData60.error, 'Error fetching 1H data: ' + myData60.error);
assert(!myData240.error, 'Error fetching 4H data: ' + myData240.error);
assert(!myDataD.error, 'Error fetching 1D data: ' + myDataD.error);

const myMetrics5 = myComputeMetrics(myData5);
const myMetrics15 = myComputeMetrics(myData15);
const myMetrics60 = myComputeMetrics(myData60);
const myMetrics240 = myComputeMetrics(myData240);
const myMetricsD = myComputeMetrics(myDataD);

// Pine's f(x) formatter: round to 2 decimals, as string.
function myFormatNumber(myValue) {
	if (myValue === null || myValue === undefined || isNaN(myValue)) return 'NA';
	return (Math.round(myValue * 100) / 100).toString();
}

function myAdxColor(myValue) {
	if (myValue >= 25) return '#009688';
	if (myValue >= 20) return '#FF9800';
	return '#9E9E9E';
}

function myRsiColor(myValue) {
	return myValue >= 50 ? '#009688' : '#F44336';
}

function myStochColor(myK, myD) {
	if (myK > myD && myK >= 50) return '#009688';
	if (myK < myD && myK < 50) return '#F44336';
	return '#9E9E9E';
}

function myBiasText(myR, myK, myD) {
	if (myR >= 50 && myK >= myD) return 'Bull';
	if (myR < 50 && myK < myD) return 'Bear';
	return 'Mixed';
}

function myBiasColor(myR, myK, myD) {
	if (myR >= 50 && myK >= myD) return '#009688';
	if (myR < 50 && myK < myD) return '#F44336';
	return '#9E9E9E';
}

function myLastValue(mySeries) {
	return mySeries[mySeries.length - 1];
}

function myBuildRow(myLabel, myMetrics) {
	const myAdxVal = myLastValue(myMetrics.adx);
	const myRsiVal = myLastValue(myMetrics.rsi);
	const myKVal = myLastValue(myMetrics.k);
	const myDVal = myLastValue(myMetrics.d);
	const myAtrVal = myLastValue(myMetrics.atr);

	return {
		cells: [
			{ text: myLabel, color: '#FFFFFF' },
			{ text: myFormatNumber(myAdxVal), color: '#FFFFFF', background_color: myAdxColor(myAdxVal) },
			{ text: myFormatNumber(myRsiVal), color: '#FFFFFF', background_color: myRsiColor(myRsiVal) },
			{ text: myFormatNumber(myKVal) + '/' + myFormatNumber(myDVal), color: '#FFFFFF', background_color: myStochColor(myKVal, myDVal) },
			{ text: myFormatNumber(myAtrVal), color: '#FFFFFF' },
			{ text: myBiasText(myRsiVal, myKVal, myDVal), color: '#FFFFFF', background_color: myBiasColor(myRsiVal, myKVal, myDVal) }
		]
	};
}

const myHeaderRow = {
	cells: [
		{ text: 'TF', color: '#FFFFFF', background_color: '#78909C' },
		{ text: 'ADX', color: '#FFFFFF', background_color: '#78909C' },
		{ text: 'RSI', color: '#FFFFFF', background_color: '#78909C' },
		{ text: 'Stoch', color: '#FFFFFF', background_color: '#78909C' },
		{ text: 'ATR', color: '#FFFFFF', background_color: '#78909C' },
		{ text: 'Bias', color: '#FFFFFF', background_color: '#78909C' }
	]
};

paint_overlay('MTFDashboardTable', { position: myTablePosition }, {
	rows: [
		myHeaderRow,
		myBuildRow('5m', myMetrics5),
		myBuildRow('15m', myMetrics15),
		myBuildRow('1H', myMetrics60),
		myBuildRow('4H', myMetrics240),
		myBuildRow('1D', myMetricsD)
	]
});

// Land each timeframe's bias onto the current chart's time axis, so bias
// state can be used in scanners, alerts and the strategy tester.
function myBiasBoolSeries(myMetrics) {
	return for_every(myMetrics.rsi, myMetrics.k, myMetrics.d, (_r, _k, _d) => (_r >= 50 && _k >= _d) ? 1 : 0);
}

function myLandBias(myMetrics) {
	const myBiasSeries = myBiasBoolSeries(myMetrics);
	const myLanded = land_points_onto_series(myMetrics.time, myBiasSeries, time, 'ge');
	return interpolate_sparse_series(myLanded, 'constant');
}

const myBullSignal5 = myLandBias(myMetrics5);
const myBullSignal15 = myLandBias(myMetrics15);
const myBullSignal60 = myLandBias(myMetrics60);
const myBullSignal240 = myLandBias(myMetrics240);
const myBullSignalD = myLandBias(myMetricsD);

register_signal(for_every(myBullSignal5, _v => _v === 1), 'Bullish Bias 5m');
register_signal(for_every(myBullSignal15, _v => _v === 1), 'Bullish Bias 15m');
register_signal(for_every(myBullSignal60, _v => _v === 1), 'Bullish Bias 1H');
register_signal(for_every(myBullSignal240, _v => _v === 1), 'Bullish Bias 4H');
register_signal(for_every(myBullSignalD, _v => _v === 1), 'Bullish Bias 1D');