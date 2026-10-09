describe_indicator('Albtrader NQ Beast - Supertrend MACD RSI', 'price');

// Supertrend inputs
const myStFactor = input.number('Supertrend Factor', 3.0, { min: 1, max: 20 });
const myStPeriod = input.number('Supertrend Period', 10, { min: 1, max: 100 });

// MACD inputs
const myMacdFast = input.number('MACD Fast', 12, { min: 1, max: 100 });
const myMacdSlow = input.number('MACD Slow', 26, { min: 1, max: 200 });
const myMacdSig = input.number('MACD Signal', 9, { min: 1, max: 100 });

// RSI inputs
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiOB = input.number('RSI Overbought', 70, { min: 1, max: 99 });
const myRsiOS = input.number('RSI Oversold', 30, { min: 1, max: 99 });

// EMA bias and ATR inputs
const myEmaLen = input.number('EMA Bias Length', 200, { min: 1, max: 500 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 100 });
const myRrRatio = input.number('Risk Reward Ratio', 2.0, { min: 1, max: 10 });

// === INDICATORS ===
// Supertrend: built-in returns the Supertrend line only. Direction is derived
// by comparing Close vs the Supertrend line, which is the standard definition
// (bullish/uptrend when Close is above the line, bearish when below).
const mySupertrendLine = supertrend(myStPeriod, myStFactor, false);
const myDirectionIsUp = for_every(close, mySupertrendLine, (_c, _st) => _c > _st);

const myMacdFastEma = ema(close, myMacdFast);
const myMacdSlowEma = ema(close, myMacdSlow);
const myMacdLine = sub(myMacdFastEma, myMacdSlowEma);
const myMacdSignalLine = ema(myMacdLine, myMacdSig);

const myRsiLine = rsi(close, myRsiLen);
const myEmaBias = ema(close, myEmaLen);
const myAtrLine = atr(high, low, close, myAtrLen);

// Crossover / crossunder of MACD vs Signal
const myMacdBull = for_every(myMacdLine, myMacdSignalLine, (_m, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _m > _s && myMacdLine[_i - 1] <= myMacdSignalLine[_i - 1];
});

const myMacdBear = for_every(myMacdLine, myMacdSignalLine, (_m, _s, _prev, _i) => {
	if (_i === 0) return false;
	return _m < _s && myMacdLine[_i - 1] >= myMacdSignalLine[_i - 1];
});

// === CONDITIONS ===
const myLongCond = for_every(
	myDirectionIsUp, myMacdBull, myRsiLine, close, myEmaBias,
	(_up, _bull, _rsi, _c, _ema) => _up && _bull && _rsi > myRsiOS && _c > _ema
);

const myShortCond = for_every(
	myDirectionIsUp, myMacdBear, myRsiLine, close, myEmaBias,
	(_up, _bear, _rsi, _c, _ema) => !_up && _bear && _rsi < myRsiOB && _c < _ema
);

// Supertrend trailing exit flips (approximation of strategy.close conditions)
const myLongTrailExit = for_every(myDirectionIsUp, (_up, _prev, _i) => {
	if (_i === 0) return false;
	return !_up && myDirectionIsUp[_i - 1];
});

const myShortTrailExit = for_every(myDirectionIsUp, (_up, _prev, _i) => {
	if (_i === 0) return false;
	return _up && !myDirectionIsUp[_i - 1];
});

// Supertrend line colored by direction
const mySupertrendColor = for_every(myDirectionIsUp, _up => _up ? '#26A69A' : '#EF5350');
paint(mySupertrendLine, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });

paint(myEmaBias, { name: 'EMA Bias', color: '#FFA726', thickness: 1 });

// Buy / Sell shapes
const myBuyMarks = for_every(myLongCond, low, (_cond, _l) => _cond ? _l : null);
const mySellMarks = for_every(myShortCond, high, (_cond, _h) => _cond ? _h : null);

paint(myBuyMarks, { name: 'Buy Signal', style: 'labels_below', color: '#26A69A', thickness: 3 });
paint(mySellMarks, { name: 'Sell Signal', style: 'labels_above', color: '#EF5350', thickness: 3 });

// === SIGNALS FOR SCANNERS, ALERTS AND STRATEGY ===
register_signal(myLongCond, 'Long Entry');
register_signal(myShortCond, 'Short Entry');
register_signal(myLongTrailExit, 'Supertrend Trail Exit Long');
register_signal(myShortTrailExit, 'Supertrend Trail Exit Short');