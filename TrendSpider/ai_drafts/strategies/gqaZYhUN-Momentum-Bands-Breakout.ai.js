describe_indicator('Momentum Exhaustion Breakout', 'price');

// NOTE: This script reproduces the Pine Script's indicator/signal logic
// (trend filter, breakout, volume expansion, RSI momentum confirmation,
// ATR bands, state coloring). TrendSpider Custom JS API has no strategy
// engine (no position sizing, entries, trailing stops, equity tracking),
// so strategy.entry/strategy.exit/position sizing could not be ported.
// Signals (longSignal/fadeSignal) are registered for scanners/alerts.
// Candle coloring approximates Pine's persistent "stateColor" by holding
// the last signal color until the opposite signal fires (no simulated
// open/closed position state, since that requires a strategy engine).

const myTab = input.tab('Breakout & Trend');
const myBreakoutGroup = myTab.group('Breakout / Volume');
const myRow1 = myBreakoutGroup.row();
const myNLen = myRow1.number('Breakout Lookback N', 20, { min: 1, max: 500 });
const myVolLen = myRow1.number('Volume MA Length', 20, { min: 1, max: 500 });
const myVolMult = myBreakoutGroup.number('Volume Expansion Multiplier', 1.5, { min: 0.1, max: 20, step: 0.1 });

const myTrendGroup = myTab.group('Trend Filter');
const myTrendRow = myTrendGroup.row();
const myEmaFastLen = myTrendRow.number('EMA Fast', 20, { min: 1, max: 500 });
const myEmaSlowLen = myTrendRow.number('EMA Slow', 50, { min: 1, max: 500 });

const myRsiTab = input.tab('Momentum');
const myRsiGroup = myRsiTab.group('RSI');
const myRsiRow = myRsiGroup.row();
const myRsiLen = myRsiRow.number('RSI Length', 14, { min: 1, max: 500 });
const myRocLen = myRsiRow.number('RSI ROC Lookback', 5, { min: 1, max: 500 });
const myRsiConfirmLvl = myRsiGroup.number('Min RSI to Confirm Longs', 55, { min: 0, max: 100 });

const myAtrTab = input.tab('ATR / Risk');
const myAtrGroup = myAtrTab.group('ATR');
const myAtrRow = myAtrGroup.row();
const myAtrLen = myAtrRow.number('ATR Length', 14, { min: 1, max: 500 });
const myAtrSLMult = myAtrGroup.number('Initial Stop ATR Mult', 1.5, { min: 0.1, max: 20, step: 0.1 });
const myAllowShorts = myAtrGroup.boolean('Enable Fade the Fakeout Shorts', true);

const myVizTab = input.tab('Visuals');
const myBandMult = myVizTab.number('Band Width ATR Mult', 2, { min: 0.1, max: 20, step: 0.1 });
const myShowBands = myVizTab.boolean('Show ATR Bands', true);
const myShowCandles = myVizTab.boolean('Show Breakout Candles', true);

const myBullColor = '#2dd4bf';
const myBearColor = '#ff4335';

// Trend context
const myEmaFast = ema(close, myEmaFastLen);
const myEmaSlow = ema(close, myEmaSlowLen);
const myUptrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f > _s);
const myDowntrend = for_every(myEmaFast, myEmaSlow, (_f, _s) => _f < _s);

// Breakout + momentum (Pine's high[1]/low[1]/rsiVal[1] = shift by 1, excluding current bar)
const myPriorHigh = highest(shift(high, 1), myNLen);
const myPriorLow = lowest(shift(low, 1), myNLen);
const myVolAvg = sma(volume, myVolLen);
const myVolExpansion = for_every(volume, myVolAvg, (_v, _a) => _v > _a * myVolMult);

const myRsiVal = rsi(close, myRsiLen);
const myRsiROC = sub(myRsiVal, shift(myRsiVal, myRocLen));
const myPriorRSIPk = highest(shift(myRsiVal, 1), myNLen);

const myBreakoutUp = for_every(high, myPriorHigh, myVolExpansion, (_h, _ph, _ve) => _h > _ph && _ve);

const myLongSignal = for_every(
	myBreakoutUp, myUptrend, myRsiROC, myRsiVal,
	(_bu, _up, _roc, _rsi) => _bu && _up && _roc > 0 && _rsi > myRsiConfirmLvl
);

const myFadeSignal = for_every(
	myBreakoutUp, myUptrend, myRsiVal, myPriorRSIPk, myRsiROC,
	(_bu, _up, _rsi, _pk, _roc) => myAllowShorts && _bu && !_up && (_rsi < _pk || _roc < 0)
);

const myAtrVal = atr(high, low, close, myAtrLen);

// ATR bands around EMA fast
const myBandWidth = mult(myAtrVal, myBandMult);
const myUpperBand = add(myEmaFast, myBandWidth);
const myLowerBand = sub(myEmaFast, myBandWidth);

const myBasisLine = myShowBands ? myEmaFast : constants.empty_series;
const myUpperLine = myShowBands ? myUpperBand : constants.empty_series;
const myLowerLine = myShowBands ? myLowerBand : constants.empty_series;

const myBasisPainted = paint(myBasisLine, { name: 'Trend Basis', color: 'gray', thickness: 1, forceUsePriceAxis: true });
const myUpperPainted = paint(myUpperLine, { name: 'Upper Band', color: myBullColor, thickness: 1, forceUsePriceAxis: true });
const myLowerPainted = paint(myLowerLine, { name: 'Lower Band', color: myBearColor, thickness: 1, forceUsePriceAxis: true });

fill(myBasisPainted, myUpperPainted, myBullColor, 0.12);
fill(myBasisPainted, myLowerPainted, myBearColor, 0.12);

// Persistent state color, mirrors Pine's "var color stateColor" logic.
// Starts gray, flips to bull/bear color on signal and holds until the
// opposite signal fires (no simulated position state available).
const myStateColor = for_every(myLongSignal, myFadeSignal, (_long, _fade, _prev) => {
	if (_long) return myBullColor;
	if (_fade) return myBearColor;
	return _prev || 'gray';
});

const myCandleColors = myShowCandles
	? for_every(myStateColor, myLongSignal, myFadeSignal, (_state, _long, _fade) => (_long || _fade) ? _state : null)
	: constants.empty_series;

color_candles(myCandleColors);

register_signal(myLongSignal, 'Long Signal');
register_signal(myFadeSignal, 'Fade Short Signal');
register_signal(myUptrend, 'Uptrend');
register_signal(myDowntrend, 'Downtrend');