describe_indicator('Stochastic K D Cross Strategy Signals', 'lower');

// Pine Script's "stoch()" built-in computes the raw %K; TrendSpider's
// stochastic() function reproduces that same raw %K math, so we smooth
// it ourselves afterwards exactly like the Pine script does.
const myPeriodK = input.number('K', 13, { min: 1, max: 200 });
const myPeriodD = input.number('D', 3, { min: 1, max: 200 });
const mySmoothK = input.number('Smooth', 4, { min: 1, max: 200 });
const myTakeProfitTicks = input.number('Take Profit (in ticks)', 100, { min: 1, max: 100000 });

const myRawK = stochastic(close, high, low, myPeriodK);
const myK = sma(myRawK, mySmoothK);
const myD = sma(myK, myPeriodD);

// Crossover / Crossunder logic, replicated manually since there is no
// built-in crossover()/crossunder() function in this API.
const myPrevK = shift(myK, 1);
const myPrevD = shift(myD, 1);

const myCrossoverSeries = for_every(myK, myD, myPrevK, myPrevD, (_k, _d, _pk, _pd) => {
	if (_k == null || _d == null || _pk == null || _pd == null) return false;
	return _pk <= _pd && _k > _d;
});

const myCrossunderSeries = for_every(myK, myD, myPrevK, myPrevD, (_k, _d, _pk, _pd) => {
	if (_k == null || _d == null || _pk == null || _pd == null) return false;
	return _pk >= _pd && _k < _d;
});

const myGoLongSeries = for_every(myCrossoverSeries, myK, (_cross, _k) => _cross && _k < 80);
const myGoShortSeries = for_every(myCrossunderSeries, myK, (_cross, _k) => _cross && _k > 20);

// Register signals so these can be used in Scanners, Alerts and Strategy Tester.
register_signal(myGoLongSeries, 'Go Long');
register_signal(myGoShortSeries, 'Go Short');

// Visual markers for the long/short trigger candles.
const myLongMarkSeries = for_every(myGoLongSeries, low, (_go, _l) => _go ? _l : null);
const myShortMarkSeries = for_every(myGoShortSeries, high, (_go, _h) => _go ? _h : null);

paint(myK, { name: 'KLine', color: '#2962FF', thickness: 2 });
paint(myD, { name: 'DLine', color: '#FF9800', thickness: 2 });

const myUpperLevel = paint(horizontal_line(80), { name: 'UpperLevel', color: 'purple', style: 'dotted' });
const myLowerLevel = paint(horizontal_line(20), { name: 'LowerLevel', color: 'purple', style: 'dotted' });
fill(myUpperLevel, myLowerLevel, 'purple', 0.1);

paint(myLongMarkSeries, { name: 'GoLongMark', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarkSeries, { name: 'GoShortMark', style: 'labels_above', color: '#EF5350', thickness: 3 });