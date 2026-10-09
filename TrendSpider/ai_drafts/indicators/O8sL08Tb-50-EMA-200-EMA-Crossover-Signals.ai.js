describe_indicator('50 EMA / 200 EMA Crossover Signals', 'price');

// User-configurable EMA lengths
const myFastLength = input.number('Fast EMA Length', 50, { min: 1, max: 500 });
const mySlowLength = input.number('Slow EMA Length', 200, { min: 1, max: 500 });

// EMA calculations
const myEma50 = ema(close, myFastLength);
const myEma200 = ema(close, mySlowLength);

// Crossover / crossunder detection, replicating ta.crossover / ta.crossunder
const myBuySignal = for_every(myEma50, myEma200, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myEma50[_i - 1] <= myEma200[_i - 1] && _fast > _slow;
});

const mySellSignal = for_every(myEma50, myEma200, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return myEma50[_i - 1] >= myEma200[_i - 1] && _fast < _slow;
});

// Plot EMAs
paint(myEma50, { name: 'EMA50', color: '#2962FF', thickness: 2 });
paint(myEma200, { name: 'EMA200', color: '#2E7D32', thickness: 4 });

// Buy/Sell labels below/above bars
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// Background highlight via candle coloring (approximation of bgcolor)
const myBgColors = for_every(myBuySignal, mySellSignal, (_b, _s) => {
	if (_b) return 'rgba(0,255,0,0.1)';
	if (_s) return 'rgba(255,0,0,0.1)';
	return null;
});
color_candles(myBgColors);

// Signals for scanners, alerts and strategy testing
register_signal(myBuySignal, 'Golden Cross Buy');
register_signal(mySellSignal, 'Death Cross Sell');