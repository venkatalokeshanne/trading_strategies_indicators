describe_indicator('WMA Plus RSI Filtered Scalp', 'price');

// Inputs matching the original Pine script parameters
const myFastLen = input.number('Fast WMA', 9, { min: 1, max: 500 });
const mySlowLen = input.number('Slow WMA', 21, { min: 1, max: 500 });
const myRsiLen = input.number('RSI Period', 14, { min: 1, max: 500 });

const myFastWMA = wma(close, myFastLen);
const mySlowWMA = wma(close, mySlowLen);
const myRsiVal = rsi(close, myRsiLen);

// Crossover / crossunder of fast WMA vs slow WMA, replicating
// ta.crossover() and ta.crossunder() from Pine Script
const myCrossOver = for_every(myFastWMA, mySlowWMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastWMA[_i - 1] <= mySlowWMA[_i - 1] && _fast > _slow;
});

const myCrossUnder = for_every(myFastWMA, mySlowWMA, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myFastWMA[_i - 1] >= mySlowWMA[_i - 1] && _fast < _slow;
});

// Long condition: crossover + price above both WMAs + RSI > 50
const myLongCondition = for_every(myCrossOver, close, myFastWMA, mySlowWMA, myRsiVal,
	(_co, _c, _f, _s, _r) => _co && _c > _f && _c > _s && _r > 50
);

// Short condition: crossunder + price below both WMAs + RSI < 50
const myShortCondition = for_every(myCrossUnder, close, myFastWMA, mySlowWMA, myRsiVal,
	(_cu, _c, _f, _s, _r) => _cu && _c < _f && _c < _s && _r < 50
);

paint(myFastWMA, { name: 'Fast WMA', color: '#2962FF', thickness: 2 });
paint(mySlowWMA, { name: 'Slow WMA', color: '#FF9800', thickness: 2 });

const myLongMarks = for_every(myLongCondition, low, (_l, _lo) => _l ? _lo : null);
const myShortMarks = for_every(myShortCondition, high, (_s, _hi) => _s ? _hi : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#00C853' });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#D50000' });

// Signals for scanners, alerts and strategy backtesting
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');