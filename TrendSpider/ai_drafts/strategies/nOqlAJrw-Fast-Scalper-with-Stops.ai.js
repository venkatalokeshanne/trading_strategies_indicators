describe_indicator('Fast Scalper EMA Cross', 'price');

// EMA lengths matching the Pine script (fast=5, slow=13)
const myFastLength = input.number('Fast EMA Length', 5, { min: 1, max: 200 });
const mySlowLength = input.number('Slow EMA Length', 13, { min: 1, max: 200 });

const myFastEma = ema(close, myFastLength);
const mySlowEma = ema(close, mySlowLength);

// Crossover / crossunder detection, equivalent to ta.crossover / ta.crossunder
const myLongCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	const myPrevFast = myFastEma[_index - 1];
	const myPrevSlow = mySlowEma[_index - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _index) => {
	if (_index < 1) return false;
	const myPrevFast = myFastEma[_index - 1];
	const myPrevSlow = mySlowEma[_index - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

paint(myFastEma, { name: 'Fast EMA', color: '#2962FF', thickness: 2 });
paint(mySlowEma, { name: 'Slow EMA', color: '#EF5350', thickness: 2 });

// Register signals so they can be used in Scanners, Alerts and Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');