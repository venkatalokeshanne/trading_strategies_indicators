describe_indicator('Adaptive Multi Factor Swing Strategy', 'lower');

// ------------------------------------------------------------------
// Inputs, organized into tabs/groups since there are many parameters
// ------------------------------------------------------------------
const myMacdTab = input.tab('MACD / Momentum');
const myMacdRow = myMacdTab.row();
const myFast = myMacdRow.number('Fast', 12, { min: 1, max: 200 });
const mySlow = myMacdRow.number('Slow', 26, { min: 1, max: 200 });
const mySig = myMacdRow.number('Signal', 7, { min: 1, max: 200 });

const myMomRow = myMacdTab.row();
const myStochLen = myMomRow.number('Stoch Length', 14, { min: 1, max: 200 });
const myStochSig = myMomRow.number('Stoch Signal', 3, { min: 1, max: 200 });
const myMomLen = myMomRow.number('Momentum Length', 10, { min: 1, max: 200 });
const myRsiLen = myMomRow.number('RSI Length', 7, { min: 1, max: 200 });

const myLimitsGroup = myMacdTab.group('Limits');
const myRsiLongLimit = myLimitsGroup.number('RSI Long Limit', 100, { min: 1, max: 100 });
const myRsiShortLimit = myLimitsGroup.number('RSI Short Limit', 30, { min: 1, max: 100 });

const myPsarTab = input.tab('PSAR / Vortex / DMI / MFI / Fisher');
const myPsarRow = myPsarTab.row();
const myPsarStart = myPsarRow.number('PSAR Start', 0.0, { min: 0, max: 1, step: 0.01 });
const myPsarInc = myPsarRow.number('PSAR Increment', 0.02, { min: 0.001, max: 1, step: 0.001 });
const myPsarMax = myPsarRow.number('PSAR Max', 0.2, { min: 0.01, max: 1, step: 0.01 });

const myOtherRow = myPsarTab.row();
const myVortexLen = myOtherRow.number('Vortex Length', 8, { min: 1, max: 200 });
const myDmiLen = myOtherRow.number('DMI Length', 8, { min: 1, max: 200 });
const myMfiLen = myOtherRow.number('MFI Length', 10, { min: 1, max: 200 });

const myFishRow = myPsarTab.row();
const myFishLen = myFishRow.number('Fisher Length', 10, { min: 1, max: 200 });
const myFishSig = myFishRow.number('Fisher Signal', 6, { min: 1, max: 200 });

const myScoreTab = input.tab('Score / Risk Filter');
const myScoreRow = myScoreTab.row();
const myLongScoreTh = myScoreRow.number('Long Score Threshold', 4, { min: -8, max: 8 });
const myLongExitTh = myScoreRow.number('Long Exit Threshold', 1, { min: -8, max: 8 });

const myShortScoreRow = myScoreTab.row();
const myShortScoreTh = myShortScoreRow.number('Short Score Threshold', -6, { min: -8, max: 8 });
const myShortExitTh = myShortScoreRow.number('Short Exit Threshold', -2, { min: -8, max: 8 });

const myRiskGroup = myScoreTab.group('Risk Filter');
const myRiskRow = myRiskGroup.row();
const myAdxLimit = myRiskRow.number('ADX Danger', 10, { min: 0, max: 100 });
const myAtrLen = myRiskRow.number('ATR Length', 14, { min: 1, max: 200 });
const myCooldownBars = myRiskRow.number('Cooldown Bars', 50, { min: 0, max: 1000 });

// ------------------------------------------------------------------
// Core indicator math
// ------------------------------------------------------------------
const myMacdLine = sub(ema(close, myFast), ema(close, mySlow));
const mySignal = ema(myMacdLine, mySig);

const myK = stochastic(close, high, low, myStochLen);
const myD = sma(myK, myStochSig);

const myMom = momentum(close, myMomLen);
const myRsi = rsi(close, myRsiLen);

// Note: built-in psar() parameter order is (maximum, acceleration, start),
// different from Pine's ta.sar(start, increment, max). Mapped accordingly.
const myPsar = psar(myPsarMax, myPsarInc, myPsarStart);

const myAtr = atr(high, low, close, myAtrLen);
const myAtrMA = sma(myAtr, 20);

const myAdxObj = indicators.adx(myDmiLen);

// Built-in vortex() is used instead of the hand-rolled sumN() version in Pine,
// assuming it implements the standard Vortex Indicator formula (same result).
const myVortexObj = vortex(myVortexLen);

// Built-in mfi() uses typical price (hlc3), same as the manual tp calculation in Pine.
const myMfi = mfi(hlc3, volume, myMfiLen);

// Fisher Transform (manual, since there is no built-in Fisher function)
const myHi = highest(close, myFishLen);
const myLo = lowest(close, myFishLen);
const myVraw = for_every(close, myHi, myLo, (_c, _h, _l) => _h !== _l ? (_c - _l) / (_h - _l) : 0.5);
const myVclamped = for_every(myVraw, _v => Math.max(Math.min(_v, 0.999), 0.001));
const myFish = for_every(myVclamped, _v => 0.5 * Math.log(_v / (1 - _v)));
const myFishSigLine = sma(myFish, myFishSig);

// ------------------------------------------------------------------
// Score (sum of 8 +1/-1 factors)
// ------------------------------------------------------------------
const myScore1 = for_every(myMacdLine, mySignal, (_a, _b) => _a > _b ? 1 : -1);
const myScore2 = for_every(myK, myD, (_a, _b) => _a > _b ? 1 : -1);
const myScore3 = for_every(myMom, _a => _a > 0 ? 1 : -1);
const myScore4 = for_every(myRsi, _a => _a > 50 ? 1 : -1);
const myScore5 = for_every(myVortexObj.positive, myVortexObj.negative, (_a, _b) => _a > _b ? 1 : -1);
const myScore6 = for_every(myAdxObj.dmiPlus, myAdxObj.dmiMinus, (_a, _b) => _a > _b ? 1 : -1);
const myScore7 = for_every(myMfi, _a => _a > 50 ? 1 : -1);
const myScore8 = for_every(myFish, myFishSigLine, (_a, _b) => _a > _b ? 1 : -1);

const myScore = add(myScore1, myScore2, myScore3, myScore4, myScore5, myScore6, myScore7, myScore8);

// ------------------------------------------------------------------
// Risk filter (chop zone / cooldown)
// ------------------------------------------------------------------
const myChopZone = for_every(myAdxObj.adx, myAtr, myAtrMA, (_adx, _atr, _atrMA) => (_adx < myAdxLimit) && (_atr > _atrMA));

// Replicates: var stopUntil = na; if chopZone -> stopUntil = bar_index + cooldownBars
const myStopUntil = for_every(myChopZone, (_chop, _prevStopUntil, _idx) => _chop ? (_idx + myCooldownBars) : (_prevStopUntil === undefined ? null : _prevStopUntil));

const myTradeAllowed = for_every(myStopUntil, (_su, _prev, _idx) => (_su === null || _su === undefined) || (_idx > _su));

// ------------------------------------------------------------------
// Entry / exit conditions
// NOTE: Pine's bankruptcy logic (strategy.equity, strategy.close_all) relies on
// live backtest equity which is not exposed to Custom JS indicators. That part
// of the logic cannot be reproduced here and has been omitted (isBankrupt is
// effectively always false).
// ------------------------------------------------------------------
const myLongEntryRaw = for_every(myScore, myPsar, close, myRsi, (_s, _p, _c, _r) => _s >= myLongScoreTh && _p < _c && _r < myRsiLongLimit);
const myLongExit = for_every(myScore, myPsar, close, (_s, _p, _c) => _s <= myLongExitTh || _p > _c);

const myShortEntryRaw = for_every(myScore, myPsar, close, myRsi, (_s, _p, _c, _r) => _s <= myShortScoreTh && _p > _c && _r > myRsiShortLimit);
const myShortExit = for_every(myScore, myPsar, close, (_s, _p, _c) => _s >= myShortExitTh || _p < _c);

const myLongEntry = for_every(myLongEntryRaw, myTradeAllowed, (_l, _t) => _l && _t);
const myShortEntry = for_every(myShortEntryRaw, myTradeAllowed, (_s, _t) => _s && _t);

// ------------------------------------------------------------------
// Visualization
// ------------------------------------------------------------------
paint(myScore, { name: 'Score', color: '#2962ff', style: 'line' });

const myCandleColors = for_every(myChopZone, _chop => _chop ? 'rgba(255,0,0,0.25)' : null);
color_candles(myCandleColors);

// ------------------------------------------------------------------
// Scanner / Alert / Strategy signals
// ------------------------------------------------------------------
register_signal(myLongEntry, 'Long Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortEntry, 'Short Entry');
register_signal(myShortExit, 'Short Exit');
register_signal(myChopZone, 'Chop Zone Risk Filter');