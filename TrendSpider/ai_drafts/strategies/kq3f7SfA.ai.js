describe_indicator('Withdrawn pxeo SMA Cross', 'price');

// Converts the Pine Script "Withdrawn-pxeo" strategy logic.
// fast = sma(close, 10), slow = sma(close, 30)
// Long entry on crossover, close on crossunder.
// Since this is converted from a strategy script (not an indicator),
// there is no portfolio/strategy engine here; instead, we expose
// the long entry and exit conditions as signals usable in
// scanners/alerts/strategy tester, and paint the two moving averages
// plus markers for entry/exit bars.

const myFastLength = input.number('Fast Length', 10, { min: 1, max: 500 });
const mySlowLength = input.number('Slow Length', 30, { min: 1, max: 500 });

const myFast = sma(close, myFastLength);
const mySlow = sma(close, mySlowLength);

// Crossover: fast crosses above slow
const myCrossoverSignal = for_every(myFast, mySlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast > _slow && myFast[_index - 1] <= mySlow[_index - 1];
});

// Crossunder: fast crosses below slow
const myCrossunderSignal = for_every(myFast, mySlow, (_fast, _slow, _prev, _index) => {
	if (_index === 0) return false;
	return _fast < _slow && myFast[_index - 1] >= mySlow[_index - 1];
});

const myLongEntryMarks = for_every(myCrossoverSignal, low, (_cross, _low) => _cross ? _low : null);
const myLongExitMarks = for_every(myCrossunderSignal, high, (_cross, _high) => _cross ? _high : null);

paint(myFast, { name: 'Fast', color: '#26A69A', thickness: 2 });
paint(mySlow, { name: 'Slow', color: '#EF5350', thickness: 2 });
paint(myLongEntryMarks, { name: 'LongEntry', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(myLongExitMarks, { name: 'LongExit', style: 'labels_above', color: '#EF5350', thickness: 3 });

register_signal(myCrossoverSignal, 'Long Entry');
register_signal(myCrossunderSignal, 'Long Exit');