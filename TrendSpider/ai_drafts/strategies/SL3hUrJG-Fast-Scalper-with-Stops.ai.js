describe_indicator('Fast Scalper EMA Cross', 'price');

// EMA lengths matching the Pine script defaults
const myFastLength = input.number('Fast EMA Length', 5, { min: 1, max: 200 });
const mySlowLength = input.number('Slow EMA Length', 13, { min: 1, max: 200 });

const myFastEma = ema(close, myFastLength);
const mySlowEma = ema(close, mySlowLength);

// crossover: fast crosses above slow
// crossunder: fast crosses below slow
const myLongCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myFastEma[_i - 1];
	const myPrevSlow = mySlowEma[_i - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myShortCondition = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myFastEma[_i - 1];
	const myPrevSlow = mySlowEma[_i - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

paint(myFastEma, { name: 'FastEMA', color: '#2962FF', thickness: 2 });
paint(mySlowEma, { name: 'SlowEMA', color: '#EF5350', thickness: 2 });

// Signals usable in Scanners, Alerts, and Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');