describe_indicator('Gemini Scalper V1 Signals', 'price');

// This script reproduces the entry logic of the original Pine Script
// strategy (EMA 50/200 crossover filtered by RSI). The Custom JS API
// does not support strategy position management (entries, exits,
// take-profit/stop-loss orders) inside an indicator script, so the
// risk management part (TP 1% / SL 0.5%) is not executed here. Use
// the registered Buy/Sell signals together with TrendSpider's
// Strategy Tester component to backtest with your own exit rules.

const myFastLength = input.number('Fast EMA Length', 50, { min: 1, max: 500 });
const mySlowLength = input.number('Slow EMA Length', 200, { min: 1, max: 500 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOverbought = input.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOversold = input.number('RSI Oversold', 30, { min: 1, max: 99 });

const myFastEma = ema(close, myFastLength);
const mySlowEma = ema(close, mySlowLength);
const myRsi = rsi(close, myRsiLength);

// crossover: fast EMA crosses above slow EMA
const myCrossUp = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast > _slow && myFastEma[_i - 1] <= mySlowEma[_i - 1];
});

// crossunder: fast EMA crosses below slow EMA
const myCrossDown = for_every(myFastEma, mySlowEma, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast < _slow && myFastEma[_i - 1] >= mySlowEma[_i - 1];
});

const myBuySignal = for_every(myCrossUp, myRsi, (_up, _r) => _up && _r < myRsiOverbought);
const mySellSignal = for_every(myCrossDown, myRsi, (_down, _r) => _down && _r > myRsiOversold);

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myFastEma, { name: 'EMA Fast', color: '#2962FF', thickness: 2 });
paint(mySlowEma, { name: 'EMA Slow', color: '#FF9800', thickness: 2 });
paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#EF5350' });

// Names passed to register_signal() must be unique across the whole
// indicator (including paint() names), so they were renamed to avoid
// the "already exists" collision with the painted lines above.
register_signal(myBuySignal, 'Buy Entry Signal');
register_signal(mySellSignal, 'Sell Entry Signal');