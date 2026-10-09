describe_indicator('EMA DMI MACD RSI Strategy', 'price');

// This script reproduces the Pine Script strategy logic for signal
// generation purposes. Since Custom JS indicators cannot place actual
// trades, the BUY/SELL signals are exposed as register_signal() outputs
// so they can be used in Scanners, Alerts and the Strategy Tester.
// ATR based stop/limit exit levels are plotted as reference lines only.

const myRsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const myAdxLength = input.number('DMI/ADX Length', 14, { min: 1, max: 100 });
const myAtrLength = input.number('ATR Length', 14, { min: 1, max: 100 });
const myHtfResolution = input.text('Higher Timeframe', '60');
const myAtrStopMult = input.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 10 });
const myAtrLimitMult = input.number('ATR Limit Multiplier', 3, { min: 0.1, max: 10 });

// EMAs
const myEma5 = ema(close, 5);
const myEma13 = ema(close, 13);
const myEma26 = ema(close, 26);
const myEma200 = ema(close, 200);

// RSI
const myRsiValue = rsi(close, myRsiLength);

// MACD (12, 26, 9), computed manually since there is no built-in macd()
const myMacdFast = ema(close, 12);
const myMacdSlow = ema(close, 26);
const myMacdLine = sub(myMacdFast, myMacdSlow);
const myMacdSignalLine = ema(myMacdLine, 9);

// DMI / ADX
const myAdxObject = indicators.adx(myAdxLength);
const myPlusDI = myAdxObject.dmiPlus;
const myMinusDI = myAdxObject.dmiMinus;
const myAdxValue = myAdxObject.adx;

// Volume
const myVolumeMa = sma(volume, 20);
const myHighVolume = for_every(volume, myVolumeMa, (_v, _vma) => _v > _vma);

// Higher Timeframe EMA (50), landed onto the current chart's candles
const myHtfData = await request.history(current.ticker, myHtfResolution);
assert(!myHtfData.error, "Error fetching higher timeframe data: " + myHtfData.error);
const myHtfEma = ema(myHtfData.close, 50);
const myHtfEmaLanded = land_points_onto_series(myHtfData.time, myHtfEma, time, 'le');
const myHtfEmaSeries = interpolate_sparse_series(myHtfEmaLanded, 'constant');

// ATR
const myAtrValue = atr(high, low, close, myAtrLength);

// Buy / Sell conditions, evaluated per candle
const myBuySignal = for_every(
	myEma5, myEma13, myEma26, close, myMacdLine, myMacdSignalLine, myRsiValue, myPlusDI, myMinusDI, myAdxValue, myHighVolume, myEma200, myHtfEmaSeries,
	(_e5, _e13, _e26, _c, _macd, _signal, _rsi, _plusDi, _minusDi, _adx, _highVol, _e200, _htf) =>
		_e5 > _e13 && _e13 > _e26 && _c > _e200 && _macd > _signal && _rsi > 55 && _plusDi > _minusDi && _adx > 20 && _highVol && _c > _htf
);

const mySellSignal = for_every(
	myEma5, myEma13, myEma26, close, myMacdLine, myMacdSignalLine, myRsiValue, myPlusDI, myMinusDI, myAdxValue, myHighVolume, myEma200, myHtfEmaSeries,
	(_e5, _e13, _e26, _c, _macd, _signal, _rsi, _plusDi, _minusDi, _adx, _highVol, _e200, _htf) =>
		_e5 < _e13 && _e13 < _e26 && _c < _e200 && _macd < _signal && _rsi < 45 && _minusDi > _plusDi && _adx > 20 && _highVol && _c < _htf
);

// ATR based exit levels (reference lines, not actual trade execution)
const myBuyStopLevel = sub(close, mult(myAtrValue, myAtrStopMult));
const myBuyLimitLevel = add(close, mult(myAtrValue, myAtrLimitMult));
const mySellStopLevel = add(close, mult(myAtrValue, myAtrStopMult));
const mySellLimitLevel = sub(close, mult(myAtrValue, myAtrLimitMult));

// Plots
paint(myEma5, { name: 'EMA5', color: 'green', thickness: 1 });
paint(myEma13, { name: 'EMA13', color: 'orange', thickness: 1 });
paint(myEma26, { name: 'EMA26', color: 'red', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: 'blue', thickness: 1 });

const myBuyMarks = for_every(myBuySignal, low, (_b, _l) => _b ? _l : null);
const mySellMarks = for_every(mySellSignal, high, (_s, _h) => _s ? _h : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

paint(myBuyStopLevel, { name: 'Buy Stop Level', color: 'silver', style: 'dotted' });
paint(myBuyLimitLevel, { name: 'Buy Limit Level', color: 'silver', style: 'dotted' });
paint(mySellStopLevel, { name: 'Sell Stop Level', color: 'gray', style: 'dotted' });
paint(mySellLimitLevel, { name: 'Sell Limit Level', color: 'gray', style: 'dotted' });

// Signals for Scanners, Alerts and Strategy Tester
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');