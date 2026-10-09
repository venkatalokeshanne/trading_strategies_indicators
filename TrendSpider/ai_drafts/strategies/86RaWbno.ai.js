describe_indicator('SMA Strategy Signals', 'price');

// Moving averages replicate ta.sma(close, length) from the Pine script
const mySma5 = sma(close, 5);
const mySma9 = sma(close, 9);
const mySma20 = sma(close, 20);
const mySma50 = sma(close, 50);
const mySma200 = sma(close, 200);

// Crossover / Crossunder logic (ta.crossover / ta.crossunder equivalent)
const myLongSignal = for_every(mySma5, mySma9, (_s5, _s9, _prev, _i) => {
	if (_i === 0) return false;
	return _s5 > _s9 && mySma5[_i - 1] <= mySma9[_i - 1];
});

const myShortSignal = for_every(mySma5, mySma9, (_s5, _s9, _prev, _i) => {
	if (_i === 0) return false;
	return _s5 < _s9 && mySma5[_i - 1] >= mySma9[_i - 1];
});

// Risk/target levels computed exactly like the Pine logic (lowest/highest of last 5)
const myLowest5 = lowest(low, 5);
const myHighest5 = highest(high, 5);

// SMA9 trend direction (bull/bear) used for barcolor
const myBull = for_every(mySma9, (_s9, _prev, _i) => _i > 0 && _s9 > mySma9[_i - 1]);
const myBear = for_every(mySma9, (_s9, _prev, _i) => _i > 0 && _s9 < mySma9[_i - 1]);

const myCandleColors = for_every(myBull, myBear, (_bull, _bear) => {
	if (_bull) return 'rgb(27,230,0)';
	if (_bear) return 'rgb(198,0,0)';
	return 'gray';
});
color_candles(myCandleColors);

// Plot the moving averages (stepline/circles not natively supported, mapped to line/dotted)
paint(mySma9, { name: 'SMA9', color: 'rgb(120,123,134)', style: 'line', thickness: 1 });
paint(mySma20, { name: 'SMA20', color: 'rgb(255,153,0)', style: 'dotted', thickness: 1 });
paint(mySma50, { name: 'SMA50', color: 'rgb(172,0,0)', style: 'dotted', thickness: 1 });
paint(mySma200, { name: 'SMA200', color: 'rgb(0,110,255)', style: 'dotted', thickness: 1 });

// Buy/Sell shapes (plotshape equivalent)
const myBuyMarks = for_every(myLongSignal, (_l) => _l ? true : null);
const mySellMarks = for_every(myShortSignal, (_s) => _s ? true : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'rgb(76,157,175)' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'rgb(218,229,0)' });

// Register signals for use in scanners/alerts/strategy tester
register_signal(myLongSignal, 'Long Entry');
register_signal(myShortSignal, 'Short Entry');
register_signal(myBull, 'SMA9 Bullish');
register_signal(myBear, 'SMA9 Bearish');

// Risk-based stop/target info, registered as signals (not visually plottable as discrete trade levels)
const myLongStop = myLowest5;
const myLongTarget = for_every(close, myLowest5, (_c, _sl) => _c + (_c - _sl) * 2);
const myShortStop = myHighest5;
const myShortTarget = for_every(close, myHighest5, (_c, _sh) => _c - (_sh - _c) * 2);

register_signal(for_every(myLongSignal, myLongStop, myLongTarget, close, (_l, _sl, _tp, _c) => _l && (_c - _sl) > 0), 'Long Valid Risk');
register_signal(for_every(myShortSignal, myShortStop, myShortTarget, close, (_s, _sh, _tp, _c) => _s && (_sh - _c) > 0), 'Short Valid Risk');