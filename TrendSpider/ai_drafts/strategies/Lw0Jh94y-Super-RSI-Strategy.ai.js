describe_indicator('Super RSI Strategy', 'price');

// ===== INPUTS =====
const myAtrPeriod = input.number('ATR Period', 10, { min: 1, max: 100 });
const myFactor = input.number('Supertrend Factor', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myRsiOverbought = input.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOversold = input.number('RSI Oversold', 30, { min: 1, max: 99 });

// The built-in supertrend() function returns a plain time series (the
// Supertrend line itself), not an object with "trend"/"direction"
// properties. That mismatch was the root cause of the error: we were
// passing an object (not a series) into for_every(), which only accepts
// time series arguments. We fixed it by using the series directly and
// deriving the trend direction ourselves by comparing close to the line.
const mySupertrendLine = supertrend(myAtrPeriod, myFactor, false);
const myDirection = for_every(close, mySupertrendLine, (_c, _t) => (_c > _t ? -1 : 1));

const myRsi = rsi(close, myRsiLength);

// Buy when Supertrend turns bullish and RSI above 50
const myBuyCondition = for_every(myDirection, myRsi, (_d, _r) => _d < 0 && _r > 50);

// Sell when Supertrend turns bearish and RSI below 50
const mySellCondition = for_every(myDirection, myRsi, (_d, _r) => _d > 0 && _r < 50);

// Exit conditions, exposed as signals too (close long / close short)
const myCloseLong = for_every(myRsi, _r => _r > myRsiOverbought);
const myCloseShort = for_every(myRsi, _r => _r < myRsiOversold);

// Dynamic color for the Supertrend line, matching Pine's green/red coloring
const mySupertrendColor = for_every(myDirection, _d => (_d < 0 ? '#26A69A' : '#EF5350'));

paint(mySupertrendLine, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });

// Buy/Sell markers, as labels below/above bars
const myBuyMarks = for_every(myBuyCondition, low, (_b, _l) => (_b ? _l : null));
const mySellMarks = for_every(mySellCondition, high, (_s, _h) => (_s ? _h : null));

paint(myBuyMarks, { name: 'BuySignal', style: 'labels_below', color: '#26A69A' });
paint(mySellMarks, { name: 'SellSignal', style: 'labels_above', color: '#EF5350' });

// Signals for scanners, alerts and strategy tester
register_signal(myBuyCondition, 'Buy');
register_signal(mySellCondition, 'Sell');
register_signal(myCloseLong, 'Close Buy (RSI Overbought)');
register_signal(myCloseShort, 'Close Sell (RSI Oversold)');