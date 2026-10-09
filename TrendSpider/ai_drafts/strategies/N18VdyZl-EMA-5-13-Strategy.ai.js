describe_indicator('EMA 5 13 Crossover Signals', 'price');

// Inputs matching the Pine script's fastLength/slowLength
const myFastLength = input.number('Fast EMA Length', 5, { min: 1, max: 500 });
const mySlowLength = input.number('Slow EMA Length', 13, { min: 1, max: 500 });

// EMA calculations (not plotted, same as Pine where plots are hidden)
const myEmaFast = ema(close, myFastLength);
const myEmaSlow = ema(close, mySlowLength);

// Crossover / Crossunder logic, replicating ta.crossover / ta.crossunder
// crossover: fast was <= slow on previous bar, and fast > slow on current bar
// crossunder: fast was >= slow on previous bar, and fast < slow on current bar
const myLongCondition = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	const myPrevFast = myEmaFast[_index - 1];
	const myPrevSlow = myEmaSlow[_index - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondition = for_every(myEmaFast, myEmaSlow, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	const myPrevFast = myEmaFast[_index - 1];
	const myPrevSlow = myEmaSlow[_index - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

// Register signals so they can be used in Scanners, Alerts, Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// Paint markers on candles to visualize the entries (does not affect signal logic)
const myLongMarks = for_every(myLongCondition, low, (_long, _low) => _long ? _low : null);
const myShortMarks = for_every(myShortCondition, high, (_short, _high) => _short ? _high : null);

paint(myLongMarks, { name: 'Long Entry Mark', style: 'labels_below', color: '#26A69A', thickness: 2 });
paint(myShortMarks, { name: 'Short Entry Mark', style: 'labels_above', color: '#EF5350', thickness: 2 });