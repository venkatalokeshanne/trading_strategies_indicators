describe_indicator('VWAP Mean Reversion Strategy v6', 'price');

// ============================================================
// INPUTS (grouped like the original Pine script)
// ============================================================

const indTab = input.tab('Indicator Settings');
const myVwapLength = indTab.number('VWAP Length', 60, { min: 1 });
const myRsiLength = indTab.number('RSI Length', 14, { min: 1 });
const myRsiOverbought = indTab.number('RSI Overbought', 65, { min: 1, max: 100 });
const myRsiOversold = indTab.number('RSI Oversold', 25, { min: 1, max: 100 });

const riskTab = input.tab('Risk Management');
const myStopLossPct = riskTab.number('Stop Loss Percent', 0.5, { min: 0.01, max: 100, step: 0.1 });

const filterTab = input.tab('Volume Filter');
const myEnableVolFilter = filterTab.boolean('Enable Volume Filter', true);
const myVolLookback = filterTab.number('Volume MA Length', 20, { min: 1 });
const myVolMultiplier = filterTab.number('Volume Multiplier', 3.0, { min: 0.1, step: 0.5 });

// Pine's input.source(close, ...) is reproduced using "close" directly,
// since custom source selection via UI is not requested beyond default.
const mySrc = close;

// ============================================================
// VOLUME WEIGHTED MEAN / DEVIATION (replicates Pine's custom functions)
// ============================================================

// basis = sum(volume * src) / sum(volume) over a rolling window -
// this matches Pine's vwMean() exactly using built-in sum()
const myWeightedSrc = mult(volume, mySrc);
const myBasis = div(sum(myWeightedSrc, myVwapLength), sum(volume, myVwapLength));

// vwAbsDev() needs, for each candle, the *that candle's* basis value
// applied across the whole trailing window - this cannot be expressed
// using sum() alone since the weight term depends on the window's own
// basis value, so a small per-candle loop (plain math, no indicator
// calls) is used here, matching the Pine for-loop logic exactly.
const myDev = for_every(myBasis, (_b, _prev, _index) => {
	let myWeightedDevSum = 0;
	let myVolumeSum = 0;
	const myStart = Math.max(0, _index - myVwapLength + 1);
	for (let myI = myStart; myI <= _index; myI += 1) {
		myWeightedDevSum += volume[myI] * Math.abs(mySrc[myI] - _b);
		myVolumeSum += volume[myI];
	}
	return myVolumeSum !== 0 ? myWeightedDevSum / myVolumeSum : null;
});

const myUpper2 = add(myBasis, mult(myDev, 2.0));
const myUpper3 = add(myBasis, mult(myDev, 3.0));
const myLower2 = sub(myBasis, mult(myDev, 2.0));
const myLower3 = sub(myBasis, mult(myDev, 3.0));

const myRsiValue = rsi(mySrc, myRsiLength);

// ============================================================
// VOLUME FILTER
// ============================================================

const myAvgVol = sma(volume, myVolLookback);
const myExtremeVol = for_every(volume, myAvgVol, (_v, _avg) => _v > _avg * myVolMultiplier);
const myVolCondition = for_every(myExtremeVol, _extreme => !myEnableVolFilter || !_extreme);

// ============================================================
// ENTRY CONDITIONS (crossunder / crossover replicated manually)
// ============================================================

const myPrevSrc = shift(mySrc, 1);
const myPrevLower2 = shift(myLower2, 1);
const myPrevUpper2 = shift(myUpper2, 1);

const myCrossUnderLower2 = for_every(mySrc, myLower2, myPrevSrc, myPrevLower2, (_s, _l, _ps, _pl) => _ps >= _pl && _s < _l);
const myCrossOverUpper2 = for_every(mySrc, myUpper2, myPrevSrc, myPrevUpper2, (_s, _u, _ps, _pu) => _ps <= _pu && _s > _u);

const myLongCondition = for_every(myCrossUnderLower2, myRsiValue, myVolCondition, (_cross, _rsi, _volOk) => _cross && _rsi < myRsiOversold && _volOk);
const myShortCondition = for_every(myCrossOverUpper2, myRsiValue, myVolCondition, (_cross, _rsi, _volOk) => _cross && _rsi > myRsiOverbought && _volOk);

// ============================================================
// SIGNALS (for Scanner / Alerts / Strategy Tester)
// ============================================================

register_signal(myLongCondition, "Long Entry");
register_signal(myShortCondition, "Short Entry");

// Approximate stop/limit exit trigger levels (informational only - see note below)
const myLongStopLevel = mult(close, 1.0 - myStopLossPct / 100);
const myShortStopLevel = mult(close, 1.0 + myStopLossPct / 100);

const myLongExitHit = for_every(close, myLongStopLevel, (_c, _stop) => _c <= _stop);
const myShortExitHit = for_every(close, myShortStopLevel, (_c, _stop) => _c >= _stop);

register_signal(myLongExitHit, "Long Stop Hit");
register_signal(myShortExitHit, "Short Stop Hit");

// ============================================================
// PLOTS
// ============================================================

paint(myBasis, { name: 'VWAP Basis', color: 'gray', thickness: 2 });

const myUpper2Painted = paint(myUpper2, { name: 'Upper Band 2', color: '#E53935' });
const myUpper3Painted = paint(myUpper3, { name: 'Upper Band 3', color: '#E5393966' });

const myLower2Painted = paint(myLower2, { name: 'Lower Band 2', color: '#2E7D32' });
const myLower3Painted = paint(myLower3, { name: 'Lower Band 3', color: '#2E7D3266' });

fill(myUpper2Painted, myUpper3Painted, '#E53935', 0.15);
fill(myLower3Painted, myLower2Painted, '#2E7D32', 0.15);

// Entry markers on the price chart
const myLongMarks = for_every(myLongCondition, low, (_cond, _low) => _cond ? _low : null);
const myShortMarks = for_every(myShortCondition, high, (_cond, _high) => _cond ? _high : null);

paint(myLongMarks, { name: 'Long Signal', color: '#26A69A', style: 'labels_below' });
paint(myShortMarks, { name: 'Short Signal', color: '#EF5350', style: 'labels_above' });