describe_indicator('Vishall EMA Trend DMI ADX Strategy', 'price');

// Visibility inputs
const topTab = input.tab('Settings');
const visGroup = topTab.group('Visibility');
const myShowEMA9 = visGroup.boolean('Show EMA 9', true);
const myShowEMA20 = visGroup.boolean('Show EMA 20', true);
const myShowEMA50 = visGroup.boolean('Show EMA 50', true);
const myShowEMA200 = visGroup.boolean('Show EMA 200', true);
const myShowSignals = visGroup.boolean('Show Buy Exit Signals', false);
const myShowBG = visGroup.boolean('Show Background Color', false);
const myEnableTrades = visGroup.boolean('Trade On Chart', true);

const emaGroup = topTab.group('EMA Lengths');
const emaRow1 = emaGroup.row();
const myEma9Len = emaRow1.number('EMA 9', 9, { min: 1, max: 500 });
const myEma20Len = emaRow1.number('EMA 20', 20, { min: 1, max: 500 });
const emaRow2 = emaGroup.row();
const myEma50Len = emaRow2.number('EMA 50', 50, { min: 1, max: 500 });
const myEma200Len = emaRow2.number('EMA 200', 200, { min: 1, max: 1000 });

const forceGroup = topTab.group('Force Slope');
const forceRow = forceGroup.row();
const myRocLen = forceRow.number('Force Length', 5, { min: 1, max: 100 });
const myMinSlope = forceRow.number('Min EMA20 Slope', 0.05, { min: -100, max: 100, step: 0.01 });

const dmiGroup = topTab.group('DMI ADX');
const dmiRow = dmiGroup.row();
const myDiLen = dmiRow.number('DI Length', 14, { min: 1, max: 100 });
const myAdxSmooth = dmiRow.number('ADX Smoothing', 14, { min: 1, max: 100 });
const myAdxMin = dmiRow.number('Min ADX', 20, { min: 0, max: 100, step: 0.5 });

// EMA calculations
const myEma9 = ema(close, myEma9Len);
const myEma20 = ema(close, myEma20Len);
const myEma50 = ema(close, myEma50Len);
const myEma200 = ema(close, myEma200Len);

// Force, acceleration, slope
const myForce = roc(close, myRocLen);
const myAccel = sub(myForce, shift(myForce, 1));
const mySlope = sub(myEma20, shift(myEma20, 1));
const mySlopePrev = shift(mySlope, 1);

// DMI / ADX. NOTE: the built-in indicators.adx() only accepts a single
// period for both DI and ADX smoothing, while the Pine script uses two
// separate lengths (diLen and adxSmooth). We approximate by using diLen
// for both, since the API doesn't expose a separate ADX smoothing length.
const myAdxObject = indicators.adx(myDiLen);
const myAdx = myAdxObject.adx;
const myDiPlus = myAdxObject.dmiPlus;
const myDiMinus = myAdxObject.dmiMinus;

// Trend filters
const myTrendBull = for_every(close, myEma9, myEma20, myEma50, myEma200, (_c, _e9, _e20, _e50, _e200) =>
	_c > _e9 && _e9 > _e20 && _e20 > _e50 && _e50 > _e200
);
const myTrendStrong = for_every(myAdx, myDiPlus, myDiMinus, (_adx, _dip, _dim) =>
	_adx > myAdxMin && _dip > _dim
);
const mySlopeUp = for_every(mySlope, mySlopePrev, (_s, _sp) => _s > myMinSlope && _sp > 0);
const myForceUp = for_every(myForce, _f => _f > 0);
const myAccelUp = for_every(myAccel, _a => _a > 0);

const myRawLong = for_every(
	myTrendBull, myTrendStrong, mySlopeUp, myForceUp, myAccelUp,
	(_tb, _ts, _su, _fu, _au) => _tb && _ts && _su && _fu && _au
);
const myRawExit = for_every(
	close, myEma9, myEma20, myDiPlus, myDiMinus, myAdx, myForce,
	(_c, _e9, _e20, _dip, _dim, _adx, _f) =>
		_c < _e9 || _e9 < _e20 || _dip < _dim || _adx < myAdxMin || _f < 0
);

// Sequential position state tracking (strategy.position_size equivalent).
// This is a plain state machine over already-computed series, not an
// indicator computation, so a loop is acceptable here.
const myBuySignal = series_of(null);
const myExitSignal = series_of(null);
const myInPosition = series_of(false);

let myPositionOpen = false;
for (let myIndex = 0; myIndex < close.length; myIndex += 1) {
	const myLongCond = myEnableTrades && myRawLong[myIndex] && !myPositionOpen;
	const myExitCond = myEnableTrades && myRawExit[myIndex] && myPositionOpen;

	if (myLongCond) {
		myPositionOpen = true;
		myBuySignal[myIndex] = true;
	}
	if (myExitCond) {
		myPositionOpen = false;
		myExitSignal[myIndex] = true;
	}
	myInPosition[myIndex] = myPositionOpen;
}

// EMA plots (same number of paint calls always; use null series when hidden)
paint(myShowEMA9 ? myEma9 : constants.empty_series, { name: 'EMA9', color: '#f1c40f', thickness: 2 });
paint(myShowEMA20 ? myEma20 : constants.empty_series, { name: 'EMA20', color: '#e67e22', thickness: 2 });
paint(myShowEMA50 ? myEma50 : constants.empty_series, { name: 'EMA50', color: '#3498db', thickness: 2 });
paint(myShowEMA200 ? myEma200 : constants.empty_series, { name: 'EMA200', color: '#9b59b6', thickness: 2 });

// Buy / Exit markers
const myBuyMarks = myShowSignals ? for_every(myBuySignal, low, (_b, _l) => _b ? _l : null) : constants.empty_series;
const myExitMarks = myShowSignals ? for_every(myExitSignal, high, (_e, _h) => _e ? _h : null) : constants.empty_series;

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green', thickness: 3 });
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: 'red', thickness: 3 });

// Background color: approximated as a line on the price axis colored by
// trend state, since this engine has no bgcolor() equivalent for custom
// scripts. Painted only as colored dots at zero-width using candle coloring.
const myBGColor = for_every(myTrendBull, myTrendStrong, (_tb, _ts) => {
	if (!myShowBG) return null;
	if (_tb && _ts) return 'rgba(0,200,0,0.10)';
	return 'rgba(200,0,0,0.07)';
});
color_candles(myBGColor);

// Signals for scanner, alerts and strategy tester
register_signal(myBuySignal, 'Buy Entry Signal');
register_signal(myExitSignal, 'Exit Signal');
register_signal(myInPosition, 'In Position');