describe_indicator('Rabiah6X 75 Percent Target Pullback', 'price');

const maLongTab = input.tab('Trend');
const maLongLen = maLongTab.number('Macro Trend Filter MA', 200, { min: 1, max: 500 });
const maShortLen = maLongTab.number('Short Trend MA', 21, { min: 1, max: 500 });

const rsiTab = input.tab('RSI');
const rsiLen = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const rsiOversold = rsiTab.number('RSI Pullback Low Threshold', 45, { min: 0, max: 100 });
const rsiOverbought = rsiTab.number('RSI Overbought Cap', 70, { min: 0, max: 100 });

const adxTab = input.tab('ADX');
const adxLen = adxTab.number('ADX Smoothing', 14, { min: 1, max: 200 });
const adxThreshold = adxTab.number('Minimum ADX Trend Strength', 20, { min: 0, max: 100, step: 0.1 });

const riskTab = input.tab('Risk');
const atrLen = riskTab.number('ATR Length', 14, { min: 1, max: 200 });
const stopMult = riskTab.number('Stop Loss ATR Mult', 1.8, { min: 0.1, max: 20, step: 0.1 });
const targetMult = riskTab.number('Take Profit ATR Mult', 1.2, { min: 0.1, max: 20, step: 0.1 });

// Macro and short trend moving averages
const myMacroMa = sma(close, maLongLen);
const myShortMa = ema(close, maShortLen);

// ADX computed using the built-in indicator (Wilder's RMA based, matching Pine's ta.rma approach)
const myAdxObject = indicators.adx(adxLen);
const myAdx = myAdxObject.adx;

// RSI momentum
const myRsi = rsi(close, rsiLen);

// Condition 1: price above macro MA (bull regime)
const myMacroTrendOk = for_every(close, myMacroMa, (_c, _m) => _c > _m);

// Condition 2: ADX shows real trend strength
const myTrendStrong = for_every(myAdx, _a => _a > adxThreshold);

// Condition 3: pullback trigger - crossover of close above short MA, or
// close is above short MA this bar while it was at/below it the previous bar
const myCloseShifted = shift(close, 1);
const myShortMaShifted = shift(myShortMa, 1);
const myPullbackTrigger = for_every(close, myShortMa, myCloseShifted, myShortMaShifted, (_c, _s, _pc, _ps) => {
	const myCrossover = _pc <= _ps && _c > _s;
	const myAboveAfterTouch = _c > _s && _pc <= _ps;
	return myCrossover || myAboveAfterTouch;
});

// Condition 4: RSI within the pullback value zone
const myRsiFilter = for_every(myRsi, _r => _r >= rsiOversold && _r <= rsiOverbought);

// Final buy confluence signal
const myBuySignal = for_every(myMacroTrendOk, myTrendStrong, myPullbackTrigger, myRsiFilter,
	(_mt, _ts, _pt, _rf) => Boolean(_mt && _ts && _pt && _rf));

// Risk management levels (computed every bar, used while a hypothetical position would be open)
const myAtrVal = atr(high, low, close, atrLen);
const myStopLoss = sub(close, mult(myAtrVal, stopMult));
const myTakeProfit = add(close, mult(myAtrVal, targetMult));

paint(myMacroMa, { name: 'MacroTrendMA', color: '#2962FF', thickness: 2 });
paint(myShortMa, { name: 'ShortTrendMA', color: '#FF9800', thickness: 2 });

// Buy signal markers below bars
const myBuyMarkers = for_every(myBuySignal, _b => _b ? constants.icons.triangle_up : null);
paint(myBuyMarkers, { style: 'labels_below', color: '#26A69A', name: 'HighProbabilityBuy' });

// Stop loss / take profit reference lines (only meaningful at the signal bars,
// kept constant so paint() calls remain stable regardless of signal state)
const myStopLossSparse = for_every(myBuySignal, myStopLoss, (_b, _s) => _b ? _s : null);
const myTakeProfitSparse = for_every(myBuySignal, myTakeProfit, (_b, _t) => _b ? _t : null);
paint(myStopLossSparse, { name: 'StopLossLevel', color: '#EF5350', style: 'ladder' });
paint(myTakeProfitSparse, { name: 'TakeProfitLevel', color: '#26A69A', style: 'ladder' });

// Signals for scanners, alerts, and strategy backtesting
register_signal(myBuySignal, 'High Probability Pullback Buy');
register_signal(myMacroTrendOk, 'Above Macro Trend');
register_signal(myTrendStrong, 'ADX Trend Strong');
register_signal(myPullbackTrigger, 'Pullback Trigger');
register_signal(myRsiFilter, 'RSI In Pullback Zone');