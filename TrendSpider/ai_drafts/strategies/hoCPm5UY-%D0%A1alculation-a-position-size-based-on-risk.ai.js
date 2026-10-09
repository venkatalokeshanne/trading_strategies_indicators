// This indicator approximates the entry/exit logic of the original Pine
// Script strategy. The Custom JS API has no concept of "strategy equity",
// "position size" or broker-style order execution (strategy.entry,
// strategy.exit, strategy.position_avg_price, strategy.equity do not
// exist here). Therefore the position-sizing math (percent2money,
// percent2points, calcPositionSize, risk % of equity) cannot be
// reproduced exactly - there is no portfolio state to size against.
// What IS reproduced exactly is the entry trigger logic (candle index
// modulo 333 / 444) and the stop-loss price levels (+/- slPcnt% from
// the entry price), exposed as signals usable in Scanner/Alerts/Backtest.
describe_indicator('Random Entry with Percent Stop Loss', 'price');

const myStopLossPercent = input.number('Stop Loss Percent', 10, { min: 0.01, max: 100 });

// Reproduces "bar_index %% 333 == 0" and "bar_index %% 444 == 0".
// Pine's bar_index is 0-based from the first bar of the dataset,
// which corresponds to the candle index here.
const myLongCondition = for_every(close, (_c, _p, _i) => _i % 333 === 0);
const myShortCondition = for_every(close, (_c, _p, _i) => _i % 444 === 0);

// Stop loss levels computed from the entry price (close of the
// signal candle), mirroring "percent2points" direction logic.
const myLongStop = for_every(close, myLongCondition, (_c, _long) => _long ? _c * (1 - myStopLossPercent / 100) : null);
const myShortStop = for_every(close, myShortCondition, (_c, _short) => _short ? _c * (1 + myStopLossPercent / 100) : null);

const myLongMarks = for_every(close, myLongCondition, (_c, _long) => _long ? _c : null);
const myShortMarks = for_every(close, myShortCondition, (_c, _short) => _short ? _c : null);

paint(myLongMarks, { name: 'LongEntry', style: 'labels_below', color: '#26A69A', thickness: 6 });
paint(myShortMarks, { name: 'ShortEntry', style: 'labels_above', color: '#EF5350', thickness: 6 });
paint(myLongStop, { name: 'LongStopLoss', style: 'dotted', color: '#26A69A', thickness: 1 });
paint(myShortStop, { name: 'ShortStopLoss', style: 'dotted', color: '#EF5350', thickness: 1 });

register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');