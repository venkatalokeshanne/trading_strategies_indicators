describe_indicator('NAS100 EMA Scalper', 'price');

// Inputs
const myScalpMode = input.boolean('Enable Scalping Mode (1m/5m)', true);

const myTab = input.tab('EMA Lengths');
const myEma5Len = myTab.number('EMA 5 Length', 5, { min: 1, max: 500 });
const myEma10Len = myTab.number('EMA 10 Length', 10, { min: 1, max: 500 });
const myEma20Len = myTab.number('EMA 20 Length', 20, { min: 1, max: 500 });
const myEma50Len = myTab.number('EMA 50 Length', 50, { min: 1, max: 500 });
const myEma200Len = myTab.number('EMA 200 Length', 200, { min: 1, max: 1000 });

const myRiskTab = input.tab('Risk (reference only)');
const myAtrLen = myRiskTab.number('ATR Length', 14, { min: 1, max: 500 });
const mySlMult = myRiskTab.number('SL Multiplier', 1.2, { min: 0.1, max: 20 });
const myTpMult = myRiskTab.number('TP Multiplier', 2.0, { min: 0.1, max: 20 });

// EMA calculations
const myEma5 = ema(close, myEma5Len);
const myEma10 = ema(close, myEma10Len);
const myEma20 = ema(close, myEma20Len);
const myEma50 = ema(close, myEma50Len);
const myEma200 = ema(close, myEma200Len);

// ATR, kept for reference / potential use in alerts/scanners (not used to plot SL/TP lines,
// since this is an indicator, not a strategy backtester)
const myAtr = atr(high, low, close, myAtrLen);

// Trend definition
const myTrendBull = for_every(myEma50, myEma200, (_e50, _e200) => _e50 > _e200);
const myTrendBear = for_every(myEma50, myEma200, (_e50, _e200) => _e50 < _e200);

// Faster momentum confirmation
const myFastBull = for_every(myEma5, myEma10, myEma20, (_e5, _e10, _e20) => _e5 > _e10 && _e10 > _e20);
const myFastBear = for_every(myEma5, myEma10, myEma20, (_e5, _e10, _e20) => _e5 < _e10 && _e10 < _e20);

// Candle momentum
const myStrongBullCandle = for_every(close, open, (_c, _o) => _c > _o);
const myStrongBearCandle = for_every(close, open, (_c, _o) => _c < _o);

// Crossover / crossunder of EMA10 vs EMA20
const myEma10Prev = shift(myEma10, 1);
const myEma20Prev = shift(myEma20, 1);

const myBullCross = for_every(myEma10, myEma20, myEma10Prev, myEma20Prev, (_e10, _e20, _e10p, _e20p) => _e10 > _e20 && _e10p <= _e20p);
const myBearCross = for_every(myEma10, myEma20, myEma10Prev, myEma20Prev, (_e10, _e20, _e10p, _e20p) => _e10 < _e20 && _e10p >= _e20p);

// Final conditions
const myLongCond = for_every(
	myTrendBull, myBullCross, myFastBull, myStrongBullCandle,
	(_trendBull, _bullCross, _fastBull, _strongBullCandle) =>
		_trendBull && _bullCross && (myScalpMode ? (_fastBull && _strongBullCandle) : true)
);

const myShortCond = for_every(
	myTrendBear, myBearCross, myFastBear, myStrongBearCandle,
	(_trendBear, _bearCross, _fastBear, _strongBearCandle) =>
		_trendBear && _bearCross && (myScalpMode ? (_fastBear && _strongBearCandle) : true)
);

// Plots of EMAs
const myLine5 = paint(myEma5, { name: 'EMA5', color: '#e53935', thickness: 1 });
const myLine10 = paint(myEma10, { name: 'EMA10', color: '#2979ff', thickness: 1 });
const myLine20 = paint(myEma20, { name: 'EMA20', color: '#fb8c00', thickness: 1 });
const myLine50 = paint(myEma50, { name: 'EMA50', color: '#43a047', thickness: 1 });
const myLine200 = paint(myEma200, { name: 'EMA200', color: '#9e9e9e', thickness: 1 });

// Fills (approximate the Pine fills)
fill(myLine10, myLine20, '#9e9e9e', 0.2);
fill(myLine50, myLine200, for_every(myTrendBull, _b => _b ? '#43a047' : '#e53935').at(-1) === '#43a047' ? '#43a047' : '#e53935', 0.15);

// Buy/Sell signal markers
const myBuyMarks = for_every(myLongCond, low, (_cond, _low) => _cond ? _low : null);
const mySellMarks = for_every(myShortCond, high, (_cond, _high) => _cond ? _high : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: '#26a69a' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: '#ef5350' });

// Signals for scanners/alerts/strategy tester
register_signal(myLongCond, 'Scalp BUY');
register_signal(myShortCond, 'Scalp SELL');