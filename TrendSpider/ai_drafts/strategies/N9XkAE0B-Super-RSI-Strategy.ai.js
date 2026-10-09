describe_indicator('Super RSI Strategy', 'price');

// ===== INPUTS =====
const myAtrPeriod = input.number('ATR Period', 10, { min: 1, max: 100 });
const myFactor = input.number('Supertrend Factor', 3.0, { min: 0.1, max: 20, step: 0.1 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myRsiOverbought = input.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOversold = input.number('RSI Oversold', 30, { min: 1, max: 99 });

// Built-in supertrend() returns a single series (the trend line itself),
// not an object with { trend, direction }. We derive the trend direction
// ourselves by comparing price to the Supertrend line: price above the
// line means bullish (uptrend), price below means bearish (downtrend).
const mySupertrendLine = supertrend(myAtrPeriod, myFactor, false);
const myDirection = for_every(close, mySupertrendLine, (_c, _s) => _c >= _s ? -1 : 1);

const myRsi = rsi(close, myRsiLength);

// Buy when Supertrend turns bullish and RSI above 50
const myBuyCondition = for_every(myDirection, myRsi, (_d, _r) => _d < 0 && _r > 50);

// Sell when Supertrend turns bearish and RSI below 50
const mySellCondition = for_every(myDirection, myRsi, (_d, _r) => _d > 0 && _r < 50);

// Exit conditions (for scanning/strategy use, not an actual broker exit)
const myCloseBuyCondition = for_every(myRsi, _r => _r > myRsiOverbought);
const myCloseSellCondition = for_every(myRsi, _r => _r < myRsiOversold);

// Supertrend line colored by trend direction
const mySupertrendColor = for_every(myDirection, _d => _d < 0 ? '#26A69A' : '#EF5350');
paint(mySupertrendLine, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });

// Buy/Sell markers
const myBuyMarks = for_every(myBuyCondition, _b => _b ? constants.icons.triangle_up : null);
const mySellMarks = for_every(mySellCondition, _s => _s ? constants.icons.triangle_down : null);
paint(myBuyMarks, { name: 'Buy', color: '#26A69A', style: 'labels_below' });
paint(mySellMarks, { name: 'Sell', color: '#EF5350', style: 'labels_above' });

// ===== SIGNALS for Scanners/Alerts/Strategy Tester =====
register_signal(myBuyCondition, 'Buy Signal');
register_signal(mySellCondition, 'Sell Signal');
register_signal(myCloseBuyCondition, 'Close Buy RSI Overbought');
register_signal(myCloseSellCondition, 'Close Sell RSI Oversold');