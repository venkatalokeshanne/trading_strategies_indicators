describe_indicator('Fast Scalper EMA Cross', 'price');

// EMA lengths matching the Pine script (fast=5, slow=13)
const myFastLength = input.number('Fast EMA Length', 5, { min: 1, max: 200 });
const mySlowLength = input.number('Slow EMA Length', 13, { min: 1, max: 200 });

const myFastEma = ema(close, myFastLength);
const mySlowEma = ema(close, mySlowLength);

paint(myFastEma, { name: 'Fast EMA', color: '#2962ff', thickness: 2 });
paint(mySlowEma, { name: 'Slow EMA', color: '#ef5350', thickness: 2 });

// Crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myLongCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastEma[_index - 1];
	const myPrevSlow = mySlowEma[_index - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastEma[_index - 1];
	const myPrevSlow = mySlowEma[_index - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

// Visual markers for long/short signals
const myLongMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#26a69a', thickness: 3 });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#ef5350', thickness: 3 });

// Register signals for scanners, alerts and strategy testing.
// Stop-loss and trailing exit logic from the Pine strategy.exit() calls
// cannot be expressed here since this platform's indicator scripting
// has no concept of broker-emulated position management (strategy module).
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');