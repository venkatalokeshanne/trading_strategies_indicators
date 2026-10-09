describe_indicator('TEMA Zero-Lag Momentum', 'price');

// Inputs mirroring the Pine Script parameters
const myTab = input.tab('Settings');
const myTemaLength = myTab.number('TEMA Period', 81, { min: 1, max: 500 });
const myFilterRow = myTab.row();
const myFastLength = myFilterRow.number('Filter Fast Length', 29, { min: 1, max: 500 });
const mySlowLength = myFilterRow.number('Filter Slow Length', 27, { min: 1, max: 500 });
const mySignalLength = myTab.number('Filter Signal Length', 5, { min: 1, max: 500 });

// Triple EMA (TEMA) computed as 3*(ema1-ema2)+ema3, same as Pine's "avg"
const myEma1 = ema(close, myTemaLength);
const myEma2 = ema(myEma1, myTemaLength);
const myEma3 = ema(myEma2, myTemaLength);
const myTemaLine = add(mult(sub(myEma1, myEma2), 3), myEma3);

// MACD-style filter
const myFastMA = ema(close, myFastLength);
const mySlowMA = ema(close, mySlowLength);
const myFmacd = sub(myFastMA, mySlowMA);
const myFsignal = sma(myFmacd, mySignalLength);

// Crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myCrossOver = for_every(myFmacd, myFsignal, (_macd, _signal, _prev, _index) => {
	if (_index < 1) return false;
	return _macd > _signal && (myFmacd[_index - 1] <= myFsignal[_index - 1]);
});

const myCrossUnder = for_every(myFmacd, myFsignal, (_macd, _signal, _prev, _index) => {
	if (_index < 1) return false;
	return _macd < _signal && (myFmacd[_index - 1] >= myFsignal[_index - 1]);
});

// avg[i] > avg[i-1] / avg[i] < avg[i-1]
const myTemaRising = for_every(myTemaLine, (_val, _prev, _index) => {
	if (_index < 1) return false;
	return _val > myTemaLine[_index - 1];
});

const myTemaFalling = for_every(myTemaLine, (_val, _prev, _index) => {
	if (_index < 1) return false;
	return _val < myTemaLine[_index - 1];
});

// Final long/short signals
const myLongSignal = for_every(myCrossOver, myTemaRising, (_co, _rising) => _co && _rising);
const myShortSignal = for_every(myCrossUnder, myTemaFalling, (_cu, _falling) => _cu && _falling);

// Plot the TEMA line (the only plot() in the original Pine script)
paint(myTemaLine, { name: 'TEMA Line', color: '#2962FF', thickness: 2 });

// Markers for the visual signals on chart
const myLongMarks = for_every(myLongSignal, close, (_sig, _c) => _sig ? _c : null);
const myShortMarks = for_every(myShortSignal, close, (_sig, _c) => _sig ? _c : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: '#EF5350', thickness: 3 });

// Register signals for use in scanners, alerts and strategy tester
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');