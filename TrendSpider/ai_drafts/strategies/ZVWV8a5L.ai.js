// ============================================================================
// NOTE: This is a conversion of a TradingView Pine v6 STRATEGY script into a
// TrendSpider indicator. TrendSpider Custom JS indicators cannot simulate
// strategy.equity, strategy.position_size, strategy.close_all(), bankruptcy
// tracking or the "position direction guard" (tradeAllowed depends on live
// position state kept by the broker emulator). Those parts of the Pine script
// are NOT reproducible here and have been omitted (see flag below). All of
// the technical score/entry/exit MATH has been reproduced as closely as the
// built-in functions allow.
// ============================================================================

describe_indicator('Adaptive Multi Factor Swing Score V22', 'lower');

const myMacdTab = input.tab('MACD / Stoch / Mom / RSI');
const myMacdRow = myMacdTab.row();
const myFast = myMacdRow.number('MACD Fast', 12, { min: 1, max: 200 });
const mySlow = myMacdRow.number('MACD Slow', 26, { min: 1, max: 300 });
const mySig = myMacdRow.number('MACD Signal', 7, { min: 1, max: 100 });

const myStochRow = myMacdTab.row();
const myStochLen = myStochRow.number('Stoch Length', 14, { min: 1, max: 200 });
const myStochSig = myStochRow.number('Stoch Signal', 3, { min: 1, max: 100 });

const myMomRsiRow = myMacdTab.row();
const myMomLen = myMomRsiRow.number('Momentum Length', 10, { min: 1, max: 200 });
const myRsiLen = myMomRsiRow.number('RSI Length', 7, { min: 1, max: 200 });

const myLimitsRow = myMacdTab.row();
const myRsiLongLimit = myLimitsRow.number('RSI Long Limit', 100, { min: 1, max: 100 });
const myRsiShortLimit = myLimitsRow.number('RSI Short Limit', 30, { min: 1, max: 100 });

const myPsarTab = input.tab('PSAR / Vortex / DMI / MFI / Fisher');
const myPsarRow = myPsarTab.row();
const myPsarStart = myPsarRow.number('PSAR Start', 0.0, { min: 0, max: 10, step: 0.01 });
const myPsarInc = myPsarRow.number('PSAR Increment', 0.02, { min: 0.001, max: 1, step: 0.001 });
const myPsarMax = myPsarRow.number('PSAR Max', 0.2, { min: 0.01, max: 2, step: 0.01 });

const myVortexDmiRow = myPsarTab.row();
const myVortexLen = myVortexDmiRow.number('Vortex Length', 8, { min: 1, max: 200 });
const myDmiLen = myVortexDmiRow.number('DMI Length', 8, { min: 1, max: 200 });
const myMfiLen = myVortexDmiRow.number('MFI Length', 10, { min: 1, max: 200 });

const myFishRow = myPsarTab.row();
const myFishLen = myFishRow.number('Fisher Length', 10, { min: 1, max: 200 });
const myFishSig = myFishRow.number('Fisher Signal', 6, { min: 1, max: 100 });

const myThTab = input.tab('Score Thresholds');
const myLongRow = myThTab.row();
const myLongScoreTh = myLongRow.number('Long Entry Score Threshold', 4, { min: -8, max: 8 });
const myLongExitTh = myLongRow.number('Long Exit Score Threshold', 1, { min: -8, max: 8 });

const myShortRow = myThTab.row();
const myShortScoreTh = myShortRow.number('Short Entry Score Threshold', -6, { min: -8, max: 8 });
const myShortExitTh = myShortRow.number('Short Exit Score Threshold', -2, { min: -8, max: 8 });

// ----- Core math -----
const myMacdLine = sub(ema(close, myFast), ema(close, mySlow));
const mySignalLine = ema(myMacdLine, mySig);

const myK = stochastic(close, high, low, myStochLen);
const myD = sma(myK, myStochSig);

const myMom = momentum(close, myMomLen);
const myRsi = rsi(close, myRsiLen);

const myPsar = psar(myPsarMax, myPsarInc, myPsarStart);

// Vortex: built-in vortex() reproduces sum(|high-low[1]|)/sum(TR) and
// sum(|low-high[1]|)/sum(TR), which is exactly the Pine sumN() formula here.
const myVortexObj = vortex(myVortexLen);
const myVip = myVortexObj.positive;
const myVim = myVortexObj.negative;

// DMI/ADX via built-in indicator (ADX itself not used in score, only +DI/-DI).
const myAdxObj = indicators.adx(myDmiLen);
const myPlusDI = myAdxObj.dmiPlus;
const myMinusDI = myAdxObj.dmiMinus;

// MFI: built-in mfi(hlc3, volume, length) implements the same typical-price
// positive/negative money flow sum ratio, including the "100 if negative
// sum is 0" edge case used in the Pine script.
const myMfi = mfi(hlc3, volume, myMfiLen);

// Fisher-style normalized price oscillator (no recursive smoothing in the
// original script, just a direct 0..1 normalization + logit transform).
const myHi = highest(close, myFishLen);
const myLo = lowest(close, myFishLen);
const myVRaw = for_every(close, myHi, myLo, (_c, _h, _l) => (_h !== _l ? (_c - _l) / (_h - _l) : 0.5));
const myVClamped = for_every(myVRaw, _v => Math.max(Math.min(_v, 0.999), 0.001));
const myFish = for_every(myVClamped, _v => 0.5 * Math.log(_v / (1 - _v)));
const myFishSigLine = sma(myFish, myFishSig);

// ----- Score (sum of 8 x +1/-1 votes) -----
const myScore = for_every(
	myMacdLine, mySignalLine, myK, myD, myMom, myRsi, myVip, myVim, myPlusDI, myMinusDI, myMfi, myFish, myFishSigLine,
	(_macd, _sig, _k, _d, _mom, _rsi, _vip, _vim, _plusDI, _minusDI, _mfi, _fish, _fishSig) => {
		let myTotal = 0;
		myTotal += _macd > _sig ? 1 : -1;
		myTotal += _k > _d ? 1 : -1;
		myTotal += _mom > 0 ? 1 : -1;
		myTotal += _rsi > 50 ? 1 : -1;
		myTotal += _vip > _vim ? 1 : -1;
		myTotal += _plusDI > _minusDI ? 1 : -1;
		myTotal += _mfi > 50 ? 1 : -1;
		myTotal += _fish > _fishSig ? 1 : -1;
		return myTotal;
	}
);

// ----- Entry / exit conditions (same-direction re-entry guard and
// bankruptcy state cannot be modeled here; see flagged note) -----
const myLongEntry = for_every(myScore, myRsi, (_s, _r) => _s >= myLongScoreTh && _r < myRsiLongLimit);
const myShortEntry = for_every(myScore, myRsi, (_s, _r) => _s <= myShortScoreTh && _r > myRsiShortLimit);
const myLongExit = for_every(myScore, myPsar, close, (_s, _p, _c) => _s <= myLongExitTh || _p > _c);
const myShortExit = for_every(myScore, myPsar, close, (_s, _p, _c) => _s >= myShortExitTh || _p < _c);

// ----- Painting -----
paint(myScore, { name: 'Score', color: '#2E86DE', style: 'line', thickness: 2 });
paint(horizontal_line(myLongScoreTh), { name: 'Long Entry Th', color: '#26A69A', style: 'dotted' });
paint(horizontal_line(myShortScoreTh), { name: 'Short Entry Th', color: '#EF5350', style: 'dotted' });

const myLongEntryMarks = for_every(myLongEntry, close, (_e, _c) => _e ? _c : null);
const myShortEntryMarks = for_every(myShortEntry, close, (_e, _c) => _e ? _c : null);

paint(myLongEntryMarks, { name: 'Long Entry Marker', style: 'labels_below', color: '#26A69A' });
paint(myShortEntryMarks, { name: 'Short Entry Marker', style: 'labels_above', color: '#EF5350' });

// ----- Scanner / Alert / Strategy signals -----
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortExit, 'Short Exit');