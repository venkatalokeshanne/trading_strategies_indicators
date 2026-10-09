describe_indicator('RAM Indicator (Supertrend plus RSI)', 'price');

// ===== INPUTS =====
const myAtrPeriod = input.number('ATR Period', 10, { min: 1, max: 100 });
const myFactor = input.number('Supertrend Factor', 3, { min: 0.1, max: 20 });
const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myRsiOverbought = input.number('RSI Overbought', 70, { min: 50, max: 100 });
const myRsiOversold = input.number('RSI Oversold', 30, { min: 0, max: 50 });

// ===== SUPERTREND =====
// The built-in supertrend() function only returns the Supertrend line itself,
// not a separate "direction" series like Pine's ta.supertrend(). Direction is
// derived here the same way Pine computes it internally: price above the
// Supertrend line means bullish (direction < 0), price below means bearish
// (direction > 0).
const mySupertrendLine = supertrend(myAtrPeriod, myFactor, false);
const myDirectionIsBullish = for_every(close, mySupertrendLine, (_c, _s) => _c > _s);

// ===== RSI =====
const myRsi = rsi(close, myRsiLength);

// ===== BUY and SELL CONDITIONS =====
const myBuyCondition = for_every(myDirectionIsBullish, myRsi, (_bull, _r) => _bull && _r > 50);
const mySellCondition = for_every(myDirectionIsBullish, myRsi, (_bull, _r) => !_bull && _r < 50);

// ===== EXIT CONDITIONS =====
const myExitBuyCondition = for_every(myRsi, _r => _r > myRsiOverbought);
const myExitSellCondition = for_every(myRsi, _r => _r < myRsiOversold);

// ===== PLOTS =====
const mySupertrendColor = for_every(myDirectionIsBullish, _bull => _bull ? 'green' : 'red');
paint(mySupertrendLine, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });

// Buy and Sell markers
const myBuyMarks = for_every(myBuyCondition, _b => _b ? constants.icons.arrow_up : null);
const mySellMarks = for_every(mySellCondition, _s => _s ? constants.icons.arrow_down : null);

paint(myBuyMarks, { name: 'BuyMarker', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'SellMarker', style: 'labels_above', color: 'red' });

// ===== SIGNALS (for scanners, alerts, strategy tester) =====
// Note: register_signal() names must be unique and were colliding with
// paint() line names ("Buy Signal" / "Sell Signal"); renamed to avoid the
// "signal already exists" error.
register_signal(myBuyCondition, 'BuySignal');
register_signal(mySellCondition, 'SellSignal');
register_signal(myExitBuyCondition, 'ExitBuyRsiOverbought');
register_signal(myExitSellCondition, 'ExitSellRsiOversold');