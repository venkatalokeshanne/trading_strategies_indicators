describe_indicator('Market Structure Swing Strategy', 'price');

const myTab = input.tab('Settings');
const myEmaLength = myTab.number('Trend EMA', 200, { min: 1, max: 1000 });
const mySwingLength = myTab.number('Swing Lookback', 5, { min: 1, max: 200 });
const myRsiLength = myTab.number('RSI Length', 14, { min: 1, max: 200 });
const myAtrLength = myTab.number('ATR Length', 14, { min: 1, max: 200 });
const myStopAtrRow = myTab.row();
const myStopAtrMult = myStopAtrRow.number('Stop ATR Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myTargetAtrMult = myStopAtrRow.number('Target ATR Multiplier', 3.0, { min: 0.1, max: 20, step: 0.1 });

// Core indicators
const myEma200 = ema(close, myEmaLength);
const myRsi = rsi(close, myRsiLength);
const myAtr = atr(high, low, close, myAtrLength);

// Swing high/low, trailing windows including current bar (ta.highest/ta.lowest)
const mySwingHigh = highest(high, mySwingLength);
const mySwingLow = lowest(low, mySwingLength);

// Pine's [1] means "previous bar value", so shift the swing series forward by 1
const mySwingHighPrev = shift(mySwingHigh, 1);
const mySwingLowPrev = shift(mySwingLow, 1);

// Liquidity sweeps
const myLiquiditySweepHigh = for_every(high, close, mySwingHighPrev, (_h, _c, _sh) => _sh != null && _h > _sh && _c < _sh);
const myLiquiditySweepLow = for_every(low, close, mySwingLowPrev, (_l, _c, _sl) => _sl != null && _l < _sl && _c > _sl);

// Trend filter
const myBullTrend = for_every(close, myEma200, (_c, _e) => _c > _e);
const myBearTrend = for_every(close, myEma200, (_c, _e) => _c < _e);

// Entry logic
const myLongCondition = for_every(myBullTrend, myLiquiditySweepLow, myRsi, (_bull, _sweep, _r) => _bull && _sweep && _r > 40);
const myShortCondition = for_every(myBearTrend, myLiquiditySweepHigh, myRsi, (_bear, _sweep, _r) => _bear && _sweep && _r < 60);

// Stop and target levels (informational, based on close and ATR)
const myLongStop = sub(close, mult(myAtr, myStopAtrMult));
const myLongTarget = add(close, mult(myAtr, myTargetAtrMult));
const myShortStop = add(close, mult(myAtr, myStopAtrMult));
const myShortTarget = sub(close, mult(myAtr, myTargetAtrMult));

// Plot trend EMA
paint(myEma200, { name: 'EMA200', color: 'orange', thickness: 2 });

// Plot signal markers
const myLongMarks = for_every(myLongCondition, _l => _l ? constants.icons.triangle_up : null);
const myShortMarks = for_every(myShortCondition, _s => _s ? constants.icons.triangle_down : null);

paint(myLongMarks, { name: 'LongSignal', style: 'labels_below', color: 'green' });
paint(myShortMarks, { name: 'ShortSignal', style: 'labels_above', color: 'red' });

// Register signals for scanners, alerts and strategy tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');