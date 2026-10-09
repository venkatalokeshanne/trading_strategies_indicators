describe_indicator('EMA Cross Strategy Signals', 'price');

// EMA lengths, configurable to mirror the Pine Script defaults
const myEma20Length = input.number('Fast EMA Length', 20, { min: 1, max: 500 });
const myEma50Length = input.number('Slow EMA Length', 50, { min: 1, max: 500 });

const myEma20 = ema(close, myEma20Length);
const myEma50 = ema(close, myEma50Length);

// Crossover / crossunder logic, replicating ta.crossover / ta.crossunder
// crossover: fast was <= slow previous bar and is > slow this bar
// crossunder: fast was >= slow previous bar and is < slow this bar
const mySignalLong = for_every(myEma20, myEma50, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myEma20[_i - 1];
	const myPrevSlow = myEma50[_i - 1];
	if (myPrevFast === null || myPrevSlow === null || _fast === null || _slow === null) return false;
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const mySignalShort = for_every(myEma20, myEma50, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	const myPrevFast = myEma20[_i - 1];
	const myPrevSlow = myEma50[_i - 1];
	if (myPrevFast === null || myPrevSlow === null || _fast === null || _slow === null) return false;
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

paint(myEma20, { name: 'EMA20', color: '#FFC107', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#2196F3', thickness: 2 });

// Visual markers equivalent to plotshape triangleup/triangledown
const myLongMarks = for_every(mySignalLong, low, (_sig, _low) => _sig ? _low : null);
const myShortMarks = for_every(mySignalShort, high, (_sig, _high) => _sig ? _high : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: 'lime', thickness: 3 });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: 'red', thickness: 3 });

// Signals exposed for scanners, alerts and strategy tester
register_signal(mySignalLong, 'EMA Cross Long');
register_signal(mySignalShort, 'EMA Cross Short');