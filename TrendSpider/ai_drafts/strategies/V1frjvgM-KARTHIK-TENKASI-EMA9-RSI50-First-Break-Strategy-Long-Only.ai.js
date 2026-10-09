describe_indicator('EMA9 RSI50 First Break Strategy', 'price');

// Inputs matching the Pine script's input.int() calls
const myEmaLength = input.number('EMA Length', 9, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 500 });

// Core calculations, equivalent to ta.ema() and ta.rsi()
const myEma9 = ema(close, myEmaLength);
const myRsi = rsi(close, myRsiLength);

// Core condition: close > ema9 and rsi > 50
const myCond = for_every(close, myEma9, myRsi, (_c, _e, _r) => _c > _e && _r > 50);

// First candle where condition becomes true (cond and not cond[1])
const myFirstSignal = for_every(myCond, (_cond, _prev, _index) => {
	if (_index === 0) return false;
	return _cond && !myCond[_index - 1];
});

// Exit condition: close < ema9
const myExitCondition = for_every(close, myEma9, (_c, _e) => _c < _e);

// Paint the EMA line, same color/style as the Pine plot
paint(myEma9, { name: 'EMA9', color: 'orange', thickness: 2, style: 'line' });

// Color candles yellow on the first qualifying candle (barcolor equivalent)
const myCandleColors = for_every(myFirstSignal, _signal => _signal ? 'yellow' : null);
color_candles(myCandleColors);

// Buy label below bar (plotshape BUY equivalent)
const myBuyMarks = for_every(myFirstSignal, low, (_signal, _low) => _signal ? _low : null);
paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });

// Exit label above bar (plotshape EXIT equivalent)
const myExitMarks = for_every(myExitCondition, high, (_exit, _high) => _exit ? _high : null);
paint(myExitMarks, { name: 'Exit', style: 'labels_above', color: 'red' });

// Register signals so these can be used in Scanners, Alerts, Strategy Tester
register_signal(myFirstSignal, 'Buy Signal');
register_signal(myExitCondition, 'Exit Signal');