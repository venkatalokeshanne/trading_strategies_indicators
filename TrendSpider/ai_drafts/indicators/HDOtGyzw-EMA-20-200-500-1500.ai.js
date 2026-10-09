describe_indicator('EMA 20/200/500/1500', 'price');

// Reproduces the Pine Script EMA lengths exactly: 20, 200, 500, 1500
const myEma20 = ema(close, 20);
const myEma200 = ema(close, 200);
const myEma500 = ema(close, 500);
const myEma1500 = ema(close, 1500);

paint(myEma20, { name: 'EMA20', color: 'blue', thickness: 1 });
paint(myEma200, { name: 'EMA200', color: 'red', thickness: 1 });
paint(myEma500, { name: 'EMA500', color: 'gold', thickness: 1 });
paint(myEma1500, { name: 'EMA1500', color: 'orange', thickness: 1 });

// Signals for scanner / alert / strategy usage: bullish/bearish
// crossovers between the fast (20) and the other EMAs, plus a
// simple trend-alignment signal.
const myCrossUp200 = for_every(myEma20, myEma200, (_fast, _slow) => _fast > _slow);
const myCrossDown200 = for_every(myEma20, myEma200, (_fast, _slow) => _fast < _slow);
const myCrossUp500 = for_every(myEma20, myEma500, (_fast, _slow) => _fast > _slow);
const myCrossDown500 = for_every(myEma20, myEma500, (_fast, _slow) => _fast < _slow);
const myCrossUp1500 = for_every(myEma20, myEma1500, (_fast, _slow) => _fast > _slow);
const myCrossDown1500 = for_every(myEma20, myEma1500, (_fast, _slow) => _fast < _slow);
const myBullTrend = for_every(myEma20, myEma200, myEma500, myEma1500, (_e20, _e200, _e500, _e1500) => _e20 > _e200 && _e200 > _e500 && _e500 > _e1500);
const myBearTrend = for_every(myEma20, myEma200, myEma500, myEma1500, (_e20, _e200, _e500, _e1500) => _e20 < _e200 && _e200 < _e500 && _e500 < _e1500);

register_signal(myCrossUp200, 'EMA20 Above EMA200');
register_signal(myCrossDown200, 'EMA20 Below EMA200');
register_signal(myCrossUp500, 'EMA20 Above EMA500');
register_signal(myCrossDown500, 'EMA20 Below EMA500');
register_signal(myCrossUp1500, 'EMA20 Above EMA1500');
register_signal(myCrossDown1500, 'EMA20 Below EMA1500');
register_signal(myBullTrend, 'Bullish Stacked Trend');
register_signal(myBearTrend, 'Bearish Stacked Trend');