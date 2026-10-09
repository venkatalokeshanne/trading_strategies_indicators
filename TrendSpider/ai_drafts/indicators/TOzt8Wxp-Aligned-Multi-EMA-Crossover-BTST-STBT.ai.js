describe_indicator('Aligned Multi EMA Crossover BTST STBT', 'price');

// --- Inputs ---
const myLen20 = input.number('Fast EMA Period', 20, { min: 1, max: 1000 });
const myLen50 = input.number('Medium EMA Period', 50, { min: 1, max: 1000 });
const myLen100 = input.number('Slow EMA Period', 100, { min: 1, max: 1000 });
const myLen200 = input.number('Baseline EMA Period', 200, { min: 1, max: 1000 });

// --- EMA Calculations ---
const myEma20 = ema(close, myLen20);
const myEma50 = ema(close, myLen50);
const myEma100 = ema(close, myLen100);
const myEma200 = ema(close, myLen200);

// --- Signal Logic ---
// bullish alignment: 50 > 100 > 200
const myBullishAlignment = for_every(myEma50, myEma100, myEma200, (_e50, _e100, _e200) => _e50 > _e100 && _e100 > _e200);

// bearish alignment: 50 < 100 < 200
const myBearishAlignment = for_every(myEma50, myEma100, myEma200, (_e50, _e100, _e200) => _e50 < _e100 && _e100 < _e200);

// crossover(ema20, ema50): ema20 crosses above ema50 this bar
const myCrossover = for_every(myEma20, myEma50, (_e20, _e50, _prev, _index) => {
	if (_index < 1) return false;
	return myEma20[_index - 1] <= myEma50[_index - 1] && _e20 > _e50;
});

// crossunder(ema20, ema50): ema20 crosses below ema50 this bar
const myCrossunder = for_every(myEma20, myEma50, (_e20, _e50, _prev, _index) => {
	if (_index < 1) return false;
	return myEma20[_index - 1] >= myEma50[_index - 1] && _e20 < _e50;
});

const myBuySignal = for_every(myCrossover, myBullishAlignment, (_c, _a) => _c && _a);
const mySellSignal = for_every(myCrossunder, myBearishAlignment, (_c, _a) => _c && _a);

// --- Plot Moving Averages ---
paint(myEma20, { name: 'EMA20', color: '#2196F3', thickness: 2 });
paint(myEma50, { name: 'EMA50', color: '#FF9800', thickness: 2 });
paint(myEma100, { name: 'EMA100', color: '#9C27B0', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: '#F44336', thickness: 2 });

// --- Visual Chart Signals ---
const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: 'green', thickness: 3 });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: 'red', thickness: 3 });

// --- Signals for scanners, alerts and strategies ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');