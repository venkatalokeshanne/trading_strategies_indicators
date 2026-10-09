describe_indicator('ATR Exhaustion and Volume Spike Strategy', 'price');

// ===== Inputs =====
const pivotTab = input.tab('Pivots');
const myPivotLeft = pivotTab.number('Pivot Left Shoulder', 5, { min: 1, max: 50 });
const myPivotRight = pivotTab.number('Pivot Right Shoulder', 5, { min: 1, max: 50 });
const myLevelProximityPercent = pivotTab.number('Level Proximity Percent', 0.5, { min: 0.01, max: 10, step: 0.1 });

const atrTab = input.tab('ATR');
const myAtrLength = atrTab.number('ATR Length', 14, { min: 1, max: 100 });
const myAtrMultiplier = atrTab.number('ATR Exhaustion Multiplier', 2.0, { min: 0.1, max: 20, step: 0.1 });

const volTab = input.tab('Volume');
const myVolSmaLength = volTab.number('Volume SMA Length', 20, { min: 1, max: 200 });
const myVolMultiplier = volTab.number('Volume Spike Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });

// Risk management inputs are kept for reference / potential use in
// scanners or alerts; the actual order execution and position sizing
// from the original Pine strategy cannot be reproduced here, since
// this platform's Custom JS indicators do not place orders.
const riskTab = input.tab('Risk Management');
const myRiskPerTradePercent = riskTab.number('Risk per Trade Percent', 0.5, { min: 0.01, max: 100, step: 0.1 });
const myRiskRewardRatio = riskTab.number('Risk Reward Ratio', 2.0, { min: 0.1, max: 20, step: 0.1 });

const myLevelDiffPer = myLevelProximityPercent / 100;
const myRiskPerTrade = myRiskPerTradePercent / 100;

// ===== 1. Pivot levels =====
const myPivotHighSparse = pivot_high(high, myPivotLeft, myPivotRight);
const myPivotLowSparse = pivot_low(low, myPivotLeft, myPivotRight);

// Carry forward last known pivot high/low, like Pine's "var float" persistence
const myLastPivotHigh = for_every(myPivotHighSparse, (_v, _prev) => (_v !== null && _v !== undefined) ? _v : (_prev === undefined ? null : _prev));
const myLastPivotLow = for_every(myPivotLowSparse, (_v, _prev) => (_v !== null && _v !== undefined) ? _v : (_prev === undefined ? null : _prev));

// ===== 2. ATR exhaustion =====
const myAtr = atr(high, low, close, myAtrLength);

const myDistFromHigh = for_every(myLastPivotHigh, low, (_ph, _low) => (_ph === null ? null : _ph - _low));
const myDistFromLow = for_every(close, myLastPivotLow, (_close, _pl) => (_pl === null ? null : _close - _pl));

const myIsExhaustedLong = for_every(myDistFromHigh, myAtr, (_dist, _atr) => (_dist !== null && _dist > _atr * myAtrMultiplier));
const myIsExhaustedShort = for_every(myDistFromLow, myAtr, (_dist, _atr) => (_dist !== null && _dist > _atr * myAtrMultiplier));

// ===== 3. Volume spike =====
const myVolSma = sma(volume, myVolSmaLength);
const myIsVolSpike = for_every(volume, myVolSma, (_v, _vsma) => _v > _vsma * myVolMultiplier);

// ===== 4. Level proximity =====
const myNearPivotLow = for_every(low, myLastPivotLow, (_low, _pl) => {
	if (_pl === null) return false;
	return _low <= _pl * (1 + myLevelDiffPer) && _low >= _pl * (1 - myLevelDiffPer);
});

const myNearPivotHigh = for_every(high, myLastPivotHigh, (_high, _ph) => {
	if (_ph === null) return false;
	return _high >= _ph * (1 - myLevelDiffPer) && _high <= _ph * (1 + myLevelDiffPer);
});

// ===== Entry triggers =====
const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);

const myBullishTrigger = for_every(close, open, myPrevHigh, (_c, _o, _ph1) => (_c > _o || _c > _ph1));
const myBearishTrigger = for_every(close, open, myPrevLow, (_c, _o, _pl1) => (_c < _o || _c < _pl1));

// ===== Final conditions =====
const myLongCondition = for_every(myNearPivotLow, myIsExhaustedLong, myIsVolSpike, myBullishTrigger, (_a, _b, _c, _d) => (_a && _b && _c && _d));
const myShortCondition = for_every(myNearPivotHigh, myIsExhaustedShort, myIsVolSpike, myBearishTrigger, (_a, _b, _c, _d) => (_a && _b && _c && _d));

// ===== Visuals =====
paint(myLastPivotHigh, { name: 'Resistance Level', color: '#EF5350', style: 'ladder' });
paint(myLastPivotLow, { name: 'Support Level', color: '#26A69A', style: 'ladder' });

const myLongShapeSeries = for_every(myLongCondition, _cond => (_cond ? constants.icons.triangle_up : null));
const myShortShapeSeries = for_every(myShortCondition, _cond => (_cond ? constants.icons.triangle_down : null));

paint(myLongShapeSeries, { name: 'Long Signal', style: 'labels_below', color: '#26A69A' });
paint(myShortShapeSeries, { name: 'Short Signal', style: 'labels_above', color: '#EF5350' });

// ===== Signals for Scanners, Alerts and Strategy Tester =====
register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');