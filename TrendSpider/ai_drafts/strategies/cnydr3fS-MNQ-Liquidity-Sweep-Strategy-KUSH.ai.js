describe_indicator('MNQ Liquidity Sweep Strategy', 'price');

// Lookback length for the highest high / lowest low window
const myLookback = input.number('Lookback', 20, { min: 1, max: 200 });

// Replicates ta.highest(high, lookback) and ta.lowest(low, lookback)
const myHighestHigh = highest(high, myLookback);
const myLowestLow = lowest(low, myLookback);

// Pine's [1] means "previous bar value", which is shift(series, 1)
const myHighestHighPrev = shift(myHighestHigh, 1);
const myLowestLowPrev = shift(myLowestLow, 1);
const myHighPrev = shift(high, 1);
const myLowPrev = shift(low, 1);

// shortCondition = high > highestHigh[1] and close < low[1]
const myShortCondition = for_every(high, myHighestHighPrev, close, myLowPrev, (_h, _hhPrev, _c, _lPrev) => {
	return _h > _hhPrev && _c < _lPrev;
});

// longCondition = low < lowestLow[1] and close > high[1]
const myLongCondition = for_every(low, myLowestLowPrev, close, myHighPrev, (_l, _llPrev, _c, _hPrev) => {
	return _l < _llPrev && _c > _hPrev;
});

// Markers for visual confirmation on the chart
const myLongMarks = for_every(myLongCondition, low, (_cond, _l) => _cond ? _l : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myLongMarks, { name: 'Long', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'Short', style: 'labels_above', color: '#EF5350', thickness: 3 });

// Signals usable in Scanners, Alerts and the Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');