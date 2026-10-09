describe_indicator('Sniper Scalping Bot 15M', 'price');

// EMA lengths and RSI thresholds, exposed as inputs since the
// original Pine script hardcodes them.
const myEma20Length = input.number('EMA Fast Length', 20, { min: 1, max: 500 });
const myEma50Length = input.number('EMA Medium Length', 50, { min: 1, max: 500 });
const myEma200Length = input.number('EMA Trend Length', 200, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiLongLevel = input.number('RSI Long Threshold', 55, { min: 1, max: 99 });
const myRsiShortLevel = input.number('RSI Short Threshold', 45, { min: 1, max: 99 });

// Core indicators
const myEma20 = ema(close, myEma20Length);
const myEma50 = ema(close, myEma50Length);
const myEma200 = ema(close, myEma200Length);
const myRsi = rsi(close, myRsiLength);

// Trend filter
const myBull = for_every(close, myEma200, (_c, _e) => _c > _e);
const myBear = for_every(close, myEma200, (_c, _e) => _c < _e);

// ta.crossover(close, ema20): close crosses above ema20 this bar
const myCrossOver = for_every(close, myEma20, (_c, _e, _prev, _i) => {
	if (_i === 0) return false;
	return close[_i - 1] <= myEma20[_i - 1] && _c > _e;
});

// ta.crossunder(close, ema20): close crosses below ema20 this bar
const myCrossUnder = for_every(close, myEma20, (_c, _e, _prev, _i) => {
	if (_i === 0) return false;
	return close[_i - 1] >= myEma20[_i - 1] && _c < _e;
});

// Long/Short entry conditions, identical logic to the Pine script
const myLongCondition = for_every(myBull, myCrossOver, myRsi, (_bull, _cross, _r) => _bull && _cross && _r > myRsiLongLevel);
const myShortCondition = for_every(myBear, myCrossUnder, myRsi, (_bear, _cross, _r) => _bear && _cross && _r < myRsiShortLevel);

// Signals for scanning/alerts/strategy testing
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');

// Visuals: same colors as the original Pine plots
paint(myEma20, { name: 'EMA20', color: '#2962FF', thickness: 1 });
paint(myEma50, { name: 'EMA50', color: '#FF9800', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: '#F23645', thickness: 1 });

// Entry marker lines (null unless condition fires on that bar)
const myLongMarker = for_every(myLongCondition, low, (_cond, _l) => _cond ? _l : null);
const myShortMarker = for_every(myShortCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myLongMarker, { name: 'LongSignal', style: 'labels_below', color: '#00C853', thickness: 3 });
paint(myShortMarker, { name: 'ShortSignal', style: 'labels_above', color: '#D50000', thickness: 3 });