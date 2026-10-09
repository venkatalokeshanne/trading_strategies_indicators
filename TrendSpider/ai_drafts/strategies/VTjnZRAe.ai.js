describe_indicator('EMA Fib Scalping Signals', 'price');

// NOTE: TrendSpider Custom JS has no strategy/backtest engine
// (no strategy.entry/exit, no position sizing, no equity tracking).
// This script reproduces the Pine Script's INDICATOR LOGIC exactly
// (EMA9/21, daily EMA50 trend filter, RSI, ADX, ATR, Fibonacci
// pullback and the long entry conditions), and exposes them as
// register_signal() outputs for scanners/alerts, plus visual plots
// of entries, take profit levels and stop level. Actual order
// sizing, partial exits and equity-based position tracking from
// the original Pine strategy cannot be reproduced here.

const myEmaFastLen = input.number('EMA Fast', 9, { min: 1, max: 200 });
const myEmaSlowLen = input.number('EMA Slow', 21, { min: 1, max: 200 });
const myEmaTrendLen = input.number('Daily Trend EMA', 50, { min: 1, max: 200 });
const myFibLevel = input.number('Fibonacci Level', 0.5, { min: 0, max: 1, step: 0.01 });
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 100 });
const myAdxLen = input.number('ADX Length', 14, { min: 1, max: 100 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 100 });

// ==================== Indicators ====================
const myEma9 = ema(close, myEmaFastLen);
const myEma21 = ema(close, myEmaSlowLen);

// Daily EMA50, requested from Daily time frame and landed onto current chart
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);
const myDailyEma50 = ema(myDailyData.close, myEmaTrendLen);
const myEma50Landed = land_points_onto_series(myDailyData.time, myDailyEma50, time, 'le');
const myEma50 = interpolate_sparse_series(myEma50Landed, 'constant');

const myRsi = rsi(close, myRsiLen);
const myAdxObject = indicators.adx(myAdxLen);
const myAdx = myAdxObject.adx;
const myAtr = atr(high, low, close, myAtrLen);

const myHighest20 = highest(high, 20);
const myVolSma20 = sma(volume, 20);

// ==================== Trend filter ====================
const myTrendUp = for_every(close, myEma50, (_c, _e) => _c > _e);

// ==================== Entry conditions ====================
const myPullback = for_every(close, myEma21, shift(close, 1), (_c, _e21, _prevC) => _c <= _e21 * 1.005 && _prevC > _e21);

const myFibLevelPrice = mult(myHighest20, 1 - myFibLevel);
const myPrevFibLevelPrice = shift(myFibLevelPrice, 1);
const myFibPullback = for_every(close, myFibLevelPrice, shift(close, 1), myPrevFibLevelPrice, (_c, _fib, _prevC, _prevFib) => _c <= _fib && _prevC > _prevFib);

const myVolCondition = for_every(volume, myVolSma20, (_v, _vsma) => _v > _vsma * 1.05);

const myLongCond1 = for_every(myTrendUp, myPullback, myRsi, myAdx, myVolCondition, (_t, _p, _r, _a, _v) => _t && _p && _r > 45 && _a > 15 && _v);
const myLongCond2 = for_every(myTrendUp, myFibPullback, myRsi, myAdx, (_t, _fp, _r, _a) => _t && _fp && _r > 45 && _a > 15);

// ==================== Reference stop / take profit levels ====================
// These are the theoretical levels implied by the Pine logic
// (entry at close on signal bar), not an actual simulated position.
const myStopLevel = sub(close, mult(myAtr, 1.5));
const myRiskDistance = mult(myAtr, 1.5);
const myTp1Level = add(close, mult(myRiskDistance, 1.8));
const myTp2Level = add(close, mult(myRiskDistance, 2.5));

// ==================== Signals for scanners, alerts, strategy tester ====================
register_signal(myLongCond1, 'Long Entry Batch1');
register_signal(myLongCond2, 'Long Entry Batch2');
register_signal(myTrendUp, 'Daily Trend Up');

// ==================== Visualization ====================
paint(myEma9, { name: 'EMA9', color: '#2962ff', thickness: 1 });
paint(myEma21, { name: 'EMA21', color: '#ff9800', thickness: 1 });
paint(myEma50, { name: 'EMA50 Daily', color: '#ef5350', thickness: 2 });

const myEntryMarksBatch1 = for_every(myLongCond1, close, (_c1, _c) => _c1 ? _c : null);
const myEntryMarksBatch2 = for_every(myLongCond2, close, (_c2, _c) => _c2 ? _c : null);

paint(myEntryMarksBatch1, { name: 'Entry Batch1', style: 'labels_below', color: '#26a69a' });
paint(myEntryMarksBatch2, { name: 'Entry Batch2', style: 'labels_below', color: '#00897b' });

const myStopLine = for_every(myLongCond1, myLongCond2, myStopLevel, (_c1, _c2, _s) => (_c1 || _c2) ? _s : null);
const myTp1Line = for_every(myLongCond1, myTp1Level, (_c1, _tp) => _c1 ? _tp : null);
const myTp2Line = for_every(myLongCond2, myTp2Level, (_c2, _tp) => _c2 ? _tp : null);

paint(myStopLine, { name: 'Reference Stop', style: 'dotted', color: '#e53935' });
paint(myTp1Line, { name: 'Reference TP1', style: 'dotted', color: '#43a047' });
paint(myTp2Line, { name: 'Reference TP2', style: 'dotted', color: '#1b5e20' });