describe_indicator('Beginner Trend and Risk Model EMA RSI', 'price');

// NOTE: This is a custom-indicator conversion of a Pine Script STRATEGY.
// The Custom JS API has no access to strategy.equity, broker simulation,
// pyramiding, commissions, stop/limit order execution or strategy.position_size.
// So actual trade management (entries, exits, equity-based position sizing,
// stop loss / take profit fills) cannot be reproduced here. This script
// reproduces the signal logic (EMA cross + RSI filter), the ATR based
// SL/TP levels, and a position size ESTIMATE using a user supplied capital
// input instead of live strategy equity.

// Renamed tab from "Inputs" to "Settings" because "Inputs" is a reserved
// tab name in the platform and caused an error.
const myTab = input.tab('Settings');
const myEmaRow = myTab.row();
const myFastLen = myEmaRow.number('Fast EMA', 9, { min: 1, max: 500 });
const mySlowLen = myEmaRow.number('Slow EMA', 21, { min: 1, max: 500 });

const myRsiGroup = myTab.group('RSI');
const myRsiLen = myRsiGroup.number('RSI Length', 14, { min: 2, max: 200 });
const myRsiRow = myRsiGroup.row();
const myRsiOB = myRsiRow.number('RSI Overbought', 70, { min: 50, max: 100 });
const myRsiOS = myRsiRow.number('RSI Oversold', 30, { min: 0, max: 50 });

const myRiskGroup = myTab.group('Risk');
const myAtrLen = myRiskGroup.number('ATR Length', 14, { min: 1, max: 200 });
const myRiskRow = myRiskGroup.row();
const myRiskRR = myRiskRow.number('Risk Reward', 2.0, { min: 0.5, max: 20, step: 0.5 });
const myRiskPct = myRiskRow.number('Risk Percent per Trade', 1.0, { min: 0.1, max: 5, step: 0.1 });
const myCapital = myRiskGroup.number('Assumed Capital for Sizing', 10000, { min: 1, max: 100000000 });

// ───────── Core calcs ─────────
const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);
const myRsi = rsi(close, myRsiLen);
const myAtr = atr(high, low, close, myAtrLen);

// Trend filter
const myBullTrend = for_every(myFastEMA, mySlowEMA, (_f, _s) => _f > _s);

// Crossover / crossunder detection (replicates ta.crossover / ta.crossunder)
const myFastPrev = shift(myFastEMA, 1);
const mySlowPrev = shift(mySlowEMA, 1);

const myLongEntryCond = for_every(
	myFastEMA, mySlowEMA, myFastPrev, mySlowPrev, myRsi,
	(_f, _s, _fp, _sp, _r) => (_fp <= _sp && _f > _s) && (_f > _s) && (_r > myRsiOS) && (_r < myRsiOB)
);

const myLongExitCond = for_every(
	myFastEMA, mySlowEMA, myFastPrev, mySlowPrev, myRsi,
	(_f, _s, _fp, _sp, _r) => (_fp >= _sp && _f < _s) || (_r > myRsiOB)
);

// ───────── Position sizing estimate (uses assumed capital, not live equity) ─────────
const myRiskAmount = myCapital * (myRiskPct / 100.0);
const myRawQty = for_every(myAtr, _a => _a > 0 ? myRiskAmount / _a : 0);
const myQty = for_every(myRawQty, _q => _q > 0 ? Math.floor(_q) : 0);
const myLongSL = sub(close, myAtr);
const myLongTP = add(close, mult(myAtr, myRiskRR));

// ───────── Visuals ─────────
paint(myFastEMA, { name: 'Fast EMA', color: '#2ca599', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: '#ee5451', thickness: 2 });

// Approximation of bgcolor(): colors candles instead of background panel,
// since Custom JS API cannot paint a full chart background color.
const myCandleColors = for_every(myBullTrend, _b => _b ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)');
color_candles(myCandleColors);

const myBuyLabels = for_every(myLongEntryCond, _c => _c ? constants.icons.triangle_up : null);
const mySellLabels = for_every(myLongExitCond, _c => _c ? constants.icons.triangle_down : null);
paint(myBuyLabels, { style: 'labels_below', color: 'lime', name: 'Buy' });
paint(mySellLabels, { style: 'labels_above', color: 'red', name: 'Sell' });

// SL/TP reference lines, only meaningful on entry bars; shown as sparse lines
const mySLLine = for_every(myLongEntryCond, myLongSL, (_c, _sl) => _c ? _sl : null);
const myTPLine = for_every(myLongEntryCond, myLongTP, (_c, _tp) => _c ? _tp : null);
paint(mySLLine, { style: 'dotted', color: 'orange', name: 'Stop Loss Estimate' });
paint(myTPLine, { style: 'dotted', color: 'blue', name: 'Take Profit Estimate' });

// ───────── Signals for Scanner, Alerts, Strategy Tester ─────────
register_signal(myLongEntryCond, 'BUY Signal');
register_signal(myLongExitCond, 'SELL Signal');
register_signal(myBullTrend, 'Bull Trend');