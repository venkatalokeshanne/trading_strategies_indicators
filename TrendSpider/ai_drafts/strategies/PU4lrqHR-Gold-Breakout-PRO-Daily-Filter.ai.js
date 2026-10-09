describe_indicator('Gold Breakout PRO Daily Filter', 'price');

const myRangeLength = input.number('Range Length', 20, { min: 1, max: 500 });
const myRiskReward = input.number('Risk Reward', 1.5, { min: 0.1, max: 10, step: 0.1 });

// Daily trend filter: fetch Daily close and compute EMA(50) on Daily data,
// then land/interpolate those values onto the current chart's candles.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching Daily data: "${myDailyData.error}"`);

const myDailyEMA50Raw = ema(myDailyData.close, 50);

const myDailyCloseLanded = land_points_onto_series(myDailyData.time, myDailyData.close, time, 'le');
const myDailyEMA50Landed = land_points_onto_series(myDailyData.time, myDailyEMA50Raw, time, 'le');

const myDailyClose = interpolate_sparse_series(myDailyCloseLanded, 'constant');
const myDailyEMA50 = interpolate_sparse_series(myDailyEMA50Landed, 'constant');

const myDailyUptrend = for_every(myDailyClose, myDailyEMA50, (_c, _e) => _c != null && _e != null && _c > _e);
const myDailyDowntrend = for_every(myDailyClose, myDailyEMA50, (_c, _e) => _c != null && _e != null && _c < _e);

// Range (trailing highest/lowest over rangeLength candles)
const myHighestHigh = highest(high, myRangeLength);
const myLowestLow = lowest(low, myRangeLength);

// Breakout strength: current bar's high-low vs 20% of current range
const myRangeSize = sub(myHighestHigh, myLowestLow);
const myStrongMove = for_every(high, low, myRangeSize, (_h, _l, _r) => (_h - _l) > (_r * 0.2));

// Momentum: breakout vs PREVIOUS bar's highest/lowest (Pine's [1] offset)
const myPrevHighestHigh = shift(myHighestHigh, 1);
const myPrevLowestLow = shift(myLowestLow, 1);

const myBullBreak = for_every(close, open, myPrevHighestHigh, (_c, _o, _ph) => _ph != null && _c > _ph && _c > _o);
const myBearBreak = for_every(close, open, myPrevLowestLow, (_c, _o, _pl) => _pl != null && _c < _pl && _c < _o);

// Entry conditions (with Daily trend filter)
const myLongCondition = for_every(myBullBreak, myStrongMove, myDailyUptrend, (_b, _s, _u) => _b && _s && _u);
const myShortCondition = for_every(myBearBreak, myStrongMove, myDailyDowntrend, (_b, _s, _d) => _b && _s && _d);

// SL/TP reference levels for the breakout bar (informational only; this
// script is an indicator, not an executable strategy, see note below)
const myLongStopLoss = myLowestLow;
const myShortStopLoss = myHighestHigh;
const myLongTakeProfit = for_every(close, myLongStopLoss, (_c, _sl) => _c + (_c - _sl) * myRiskReward);
const myShortTakeProfit = for_every(close, myShortStopLoss, (_c, _sl) => _c - (_sl - _c) * myRiskReward);

// Plots
paint(myHighestHigh, { name: 'HighestHigh', color: '#26A69A', thickness: 2 });
paint(myLowestLow, { name: 'LowestLow', color: '#EF5350', thickness: 2 });
paint(myDailyEMA50, { name: 'DailyEMA50', color: '#4DA3FF', thickness: 2 });

const myBuyLabels = for_every(myLongCondition, low, (_cond, _l) => _cond ? _l : null);
const mySellLabels = for_every(myShortCondition, high, (_cond, _h) => _cond ? _h : null);

paint(myBuyLabels, { name: 'Buy', style: 'labels_below', color: '#26A69A' });
paint(mySellLabels, { name: 'Sell', style: 'labels_above', color: '#EF5350' });

// Also expose levels for reference (optional on-chart info)
paint(myLongTakeProfit, { name: 'LongTakeProfit', color: '#81C784', style: 'dotted' });
paint(myShortTakeProfit, { name: 'ShortTakeProfit', color: '#E57373', style: 'dotted' });

// Signals for Scanners / Alerts / Strategy Tester
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');