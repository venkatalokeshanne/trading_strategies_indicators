describe_indicator('EMA plus ADX Clean (4H 1D)', 'price');

// === INPUTS ===
const myEma10Len = input.number('EMA 10 Length', 10, { min: 1, max: 500 });
const myEma21Len = input.number('EMA 21 Length', 21, { min: 1, max: 500 });
const myEma55Len = input.number('EMA 55 Length', 55, { min: 1, max: 500 });
const myEma200Len = input.number('EMA 200 Length', 200, { min: 1, max: 1000 });

const myAdxLen = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAdxThreshold = input.number('ADX Threshold', 25, { min: 1, max: 100 });

// === MOVING AVERAGES ===
const myEma10 = ema(close, myEma10Len);
const myEma21 = ema(close, myEma21Len);
const myEma55 = ema(close, myEma55Len);
const myEma200 = ema(close, myEma200Len);

// === ADX (built-in function, equivalent to Pine's ta.dmi) ===
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;

// === TREND CONDITIONS ===
const myBullTrend = for_every(myEma10, myEma21, myEma55, myEma200, (_e10, _e21, _e55, _e200) =>
	_e10 > _e21 && _e21 > _e55 && _e55 > _e200
);

const myBearTrend = for_every(myEma10, myEma21, myEma55, myEma200, (_e10, _e21, _e55, _e200) =>
	_e10 < _e21 && _e21 < _e55 && _e55 < _e200
);

// === CROSSOVER / CROSSUNDER of EMA10 vs EMA21 ===
// crossover: previous e10 <= e21 and current e10 > e21
// crossunder: previous e10 >= e21 and current e10 < e21
const myCrossoverE10E21 = for_every(myEma10, myEma21, (_e10, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e10 > _e21 && myEma10[_idx - 1] <= myEma21[_idx - 1];
});

const myCrossunderE10E21 = for_every(myEma10, myEma21, (_e10, _e21, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e10 < _e21 && myEma10[_idx - 1] >= myEma21[_idx - 1];
});

// === ENTRY CONDITIONS ===
const myLongCondition = for_every(myCrossoverE10E21, myBullTrend, myAdx, (_cross, _bull, _adxValue) =>
	_cross && _bull && _adxValue > myAdxThreshold
);

const myShortCondition = for_every(myCrossunderE10E21, myBearTrend, myAdx, (_cross, _bear, _adxValue) =>
	_cross && _bear && _adxValue > myAdxThreshold
);

// === EXIT CONDITIONS (close long on crossunder, close short on crossover) ===
const myCloseLong = myCrossunderE10E21;
const myCloseShort = myCrossoverE10E21;

// === VISUALS: EMAs ===
paint(myEma10, { name: 'EMA10', color: '#f4d03f', thickness: 2 });
paint(myEma21, { name: 'EMA21', color: '#e67e22', thickness: 2 });
paint(myEma55, { name: 'EMA55', color: '#2e86de', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#ecf0f1', thickness: 3 });

// === VISUAL SIGNALS (shapes below/above bars) ===
const myBuyMarks = for_every(myLongCondition, _long => _long ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myShortCondition, _short => _short ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#2ecc71' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#e74c3c' });

// === SCANNER / ALERT / STRATEGY SIGNALS ===
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myCloseLong, 'Close Long');
register_signal(myCloseShort, 'Close Short');
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');