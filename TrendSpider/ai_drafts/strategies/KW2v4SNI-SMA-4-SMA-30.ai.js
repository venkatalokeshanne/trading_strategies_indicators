describe_indicator('SMA 4 / SMA 30 Crossover Strategy', 'price');

// Fixed lengths, matching the original Pine Script exactly
const myShortLength = 4;
const myLongLength = 30;

const mySmaShort = sma(close, myShortLength);
const mySmaLong = sma(close, myLongLength);

// Crossover / Crossunder logic computed bar by bar, same as ta.crossover/ta.crossunder
const myLongCondition = for_every(mySmaShort, mySmaLong, (_short, _long, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevShort = mySmaShort[_index - 1];
	const myPrevLong = mySmaLong[_index - 1];
	return myPrevShort <= myPrevLong && _short > _long;
});

const myFlatCondition = for_every(mySmaShort, mySmaLong, (_short, _long, _prev, _index) => {
	if (_index === 0) return false;
	const myPrevShort = mySmaShort[_index - 1];
	const myPrevLong = mySmaLong[_index - 1];
	return myPrevShort >= myPrevLong && _short < _long;
});

// Paint the two moving averages
paint(mySmaShort, { name: 'SMA4', color: 'white', thickness: 1 });
paint(mySmaLong, { name: 'SMA30', color: 'yellow', thickness: 1 });

// Buy/Sell markers on candles, mimicking plotshape triangles
const myBuyMarks = for_every(myLongCondition, _buy => _buy ? constants.icons.triangle_up : null);
const mySellMarks = for_every(myFlatCondition, _sell => _sell ? constants.icons.triangle_down : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Signals exposed for scanners, alerts and strategy tester.
// Position state tracking is NOT replicated here (no strategy engine
// available in Custom JS API), only the raw entry/exit signals.
register_signal(myLongCondition, 'Buy Signal');
register_signal(myFlatCondition, 'Sell Signal');