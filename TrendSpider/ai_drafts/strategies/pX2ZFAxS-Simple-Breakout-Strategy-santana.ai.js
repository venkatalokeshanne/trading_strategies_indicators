describe_indicator('Simple Breakout Strategy (Pine conversion)', 'price');

// Lookback length and volume multiplier, as in Pine inputs
const myLength = input.number('Lookback', 20, { min: 1, max: 500 });
const myVolMult = input.number('Volume Multiplier', 1.5, { min: 0.1, max: 10, step: 0.1 });

// === MOVING AVERAGES (for crossover signals) ===
const mySma14 = sma(close, 14);
const mySma28 = sma(close, 28);

// crossover / crossunder of sma14 vs sma28, replicating ta.crossover/ta.crossunder
const myLongCondition = for_every(mySma14, mySma28, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast > _slow && mySma14[_i - 1] <= mySma28[_i - 1];
});

const myShortCondition = for_every(mySma14, mySma28, (_fast, _slow, _prev, _i) => {
	if (_i === 0) return false;
	return _fast < _slow && mySma14[_i - 1] >= mySma28[_i - 1];
});

// === TREND FILTER ===
const myEma50 = ema(close, 50);
const myTrendOk = for_every(close, myEma50, (_c, _e) => _c > _e);

// === RANGE (SIMPLIFIED COMPRESSION) ===
const myHighestHigh = highest(high, myLength);
const myLowestLow = lowest(low, myLength);

// === BREAKOUT === (close > highestHigh[1], i.e. previous bar's highest high)
const myHighestHighShifted = shift(myHighestHigh, 1);
const myBreakout = for_every(close, myHighestHighShifted, (_c, _hh) => _hh !== null && _c > _hh);

// === VOLUME FILTER ===
const myVolSma20 = sma(volume, 20);
const myVolOk = for_every(volume, myVolSma20, (_v, _vsma) => _v > _vsma * myVolMult);

// === EXIT LEVELS (reference only, informational) ===
// Note: these are computed per-bar as in the Pine script, but there is no
// real strategy/backtest engine here - see warning below.
const myStopLoss = mult(close, 0.97);
const myTakeProfit = mult(close, 1.06);

// === PLOTS ===
paint(myEma50, { name: 'EMA50', color: '#FFA500', thickness: 2 });
paint(myHighestHigh, { name: 'HighestHigh', color: '#2ca599', thickness: 1 });
paint(myLowestLow, { name: 'LowestLow', color: '#ee5451', thickness: 1 });

// === SIGNALS FOR SCANNER/ALERTS/STRATEGY TESTER ===
register_signal(myLongCondition, 'Long Entry SMA Crossover');
register_signal(myShortCondition, 'Short Entry SMA Crossunder');
register_signal(myBreakout, 'Breakout Above Highest High');
register_signal(myVolOk, 'Volume Filter OK');
register_signal(myTrendOk, 'Trend Filter OK');