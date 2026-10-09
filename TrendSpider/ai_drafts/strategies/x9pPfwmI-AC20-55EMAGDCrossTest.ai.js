describe_indicator('Gold 20/55 EMA Cross Strategy', 'price');

// Input parameters for the fast and slow EMA lengths
const myFastLen = input.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 55, { min: 1, max: 500 });

// Core moving averages, same as ta.ema(close, fastLen/slowLen) in Pine
const myFastMA = ema(close, myFastLen);
const mySlowMA = ema(close, mySlowLen);

// Golden Cross (crossover) and Death Cross (crossunder) detection
// equivalent to ta.crossover / ta.crossunder in Pine Script
const myGoldCross = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastMA[_index - 1];
	const myPrevSlow = mySlowMA[_index - 1];
	return myPrevFast <= myPrevSlow && _fast > _slow;
});

const myDeathCross = for_every(myFastMA, mySlowMA, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevFast = myFastMA[_index - 1];
	const myPrevSlow = mySlowMA[_index - 1];
	return myPrevFast >= myPrevSlow && _fast < _slow;
});

// Paint the moving averages
paint(myFastMA, { name: 'Fast EMA', color: '#A64CA6', thickness: 2 });
paint(mySlowMA, { name: 'Slow EMA', color: '#E6C229', thickness: 2 });

// Marks below/above bar for the gold/death crosses
const myGoldMarks = for_every(myGoldCross, low, (_cross, _low) => _cross ? _low : null);
const myDeathMarks = for_every(myDeathCross, high, (_cross, _high) => _cross ? _high : null);

paint(myGoldMarks, { name: 'Gold Cross', style: 'labels_below', color: 'green' });
paint(myDeathMarks, { name: 'Death Cross', style: 'labels_above', color: 'red' });

// Register signals for use in Scanners, Alerts and Strategy Tester
register_signal(myGoldCross, 'Gold Cross Long Entry');
register_signal(myDeathCross, 'Death Cross Short Entry');