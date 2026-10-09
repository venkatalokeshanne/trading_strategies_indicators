describe_indicator('55 20 Wilders MACD Trend', 'price');

// Inputs matching the original Pine Script strategy
const myFastLength = input.number('Fast Length', 20, { min: 1, max: 500 });
const mySlowLength = input.number('Slow Length', 55, { min: 1, max: 500 });
const mySignalLength = input.number('Signal Length', 10, { min: 1, max: 500 });

// Wilder's MA (RMA) on close price, matching ta.rma(price, length)
const myFastMA = wildma(close, myFastLength);
const mySlowMA = wildma(close, mySlowLength);

// Crossover: fast crosses above slow (long entry condition)
const myCrossOver = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myFastMA[_index - 1] <= mySlowMA[_index - 1] && _fast > _slow;
});

// Crossunder: fast crosses below slow (short entry condition)
const myCrossUnder = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return myFastMA[_index - 1] >= mySlowMA[_index - 1] && _fast < _slow;
});

// Signal Length is declared as an input to mirror the original script,
// but it is not actually used in any computation in the Pine source
// (it was declared but never referenced in the strategy logic there either).
assert(mySignalLength > 0, "Signal Length must be positive");

paint(myFastMA, { name: 'FastMA', color: '#2962FF', thickness: 2 });
paint(mySlowMA, { name: 'SlowMA', color: '#FF6D00', thickness: 2 });

// Registering signals for use in Scanners, Alerts and Strategy Tester
register_signal(myCrossOver, 'MA2CrossLE Long Entry');
register_signal(myCrossUnder, 'MA2CrossSE Short Entry');