describe_indicator('BTC Multi TF Momentum Signals', 'lower');

// NOTE: TrendSpider Custom JS API has no strategy/broker simulation
// engine (no strategy.entry, pyramiding, limit order fills, trailing
// stop fills, equity tracking). This indicator reproduces the Pine
// script SIGNAL LOGIC exactly (bullTrend, rsi15, stoch RSI cross,
// longCond, shortCond) using the same multi timeframe data, and
// exposes them as scannable/alertable signals. It also plots the
// ATR based Stop/TP/DCA reference levels computed at each signal bar
// (using close as a proxy for strategy.position_avg_price, since the
// actual average entry price depends on order fills we cannot
// simulate).

const myTab = input.tab('Settings');
const myRsiLen = myTab.number('RSI Length', 14, { min: 1, max: 100 });
const myStochLen = myTab.number('Stoch Length', 14, { min: 1, max: 100 });
const myAtrLen = myTab.number('ATR Length', 14, { min: 1, max: 100 });

const myLevelsRow = myTab.row();
const myOversold = myLevelsRow.number('Oversold', 20, { min: 1, max: 50 });
const myOverbought = myLevelsRow.number('Overbought', 80, { min: 50, max: 99 });

const myAtrRow = myTab.row();
const myStopATR = myAtrRow.number('Stop ATR', 1.5, { min: 0.1, max: 10 });
const myTpATR = myAtrRow.number('TP ATR', 1.0, { min: 0.1, max: 10 });

const myDcaRow = myTab.row();
const myDca1ATR = myDcaRow.number('DCA1 ATR', 0.5, { min: 0.1, max: 10 });
const myDca2ATR = myDcaRow.number('DCA2 ATR', 1.0, { min: 0.1, max: 10 });

// ----------------
// Fetch higher/lower timeframe data (bundled in parallel)
// ----------------

const [myData1h, myData15m, myData3m] = await Promise.all([
	request.history(current.ticker, '60'),
	request.history(current.ticker, '15'),
	request.history(current.ticker, '3')
]);

assert(!myData1h.error, `Error fetching 60min data: ${myData1h.error}`);
assert(!myData15m.error, `Error fetching 15min data: ${myData15m.error}`);
assert(!myData3m.error, `Error fetching 3min data: ${myData3m.error}`);

// ----------------
// 60m EMA200 trend
// ----------------

const myEma1hRaw = ema(myData1h.close, 200);
const myEma1hLanded = land_points_onto_series(myData1h.time, myEma1hRaw, time, 'ge');
const myEma1h = interpolate_sparse_series(myEma1hLanded, 'constant');

const myBullTrend = for_every(close, myEma1h, (_c, _e) => _e != null && _c > _e);
const myBearTrend = for_every(close, myEma1h, (_c, _e) => _e != null && _c < _e);

// ----------------
// 15m RSI
// ----------------

const myRsi15Raw = rsi(myData15m.close, myRsiLen);
const myRsi15Landed = land_points_onto_series(myData15m.time, myRsi15Raw, time, 'ge');
const myRsi15 = interpolate_sparse_series(myRsi15Landed, 'constant');

// ----------------
// 3m Stoch RSI (stochastic applied on RSI(3m))
// ----------------

const myRsi3Raw = rsi(myData3m.close, myRsiLen);
const myStochK3Raw = stochastic(myRsi3Raw, myRsi3Raw, myRsi3Raw, myStochLen);
const myStochD3Raw = sma(myStochK3Raw, 3);

const myKLanded = land_points_onto_series(myData3m.time, myStochK3Raw, time, 'ge');
const myDLanded = land_points_onto_series(myData3m.time, myStochD3Raw, time, 'ge');

const myK = interpolate_sparse_series(myKLanded, 'constant');
const myD = interpolate_sparse_series(myDLanded, 'constant');

const myKPrev = shift(myK, 1);
const myDPrev = shift(myD, 1);

const myCrossOver = for_every(myK, myD, myKPrev, myDPrev, (_k, _d, _kp, _dp) => _kp != null && _dp != null && _kp <= _dp && _k > _d);
const myCrossUnder = for_every(myK, myD, myKPrev, myDPrev, (_k, _d, _kp, _dp) => _kp != null && _dp != null && _kp >= _dp && _k < _d);

const myLongSignal = for_every(myCrossOver, myK, (_co, _k) => _co && _k < myOversold);
const myShortSignal = for_every(myCrossUnder, myK, (_cu, _k) => _cu && _k > myOverbought);

// ----------------
// Entry conditions
// ----------------

const myLongCond = for_every(myBullTrend, myRsi15, myLongSignal, (_bt, _r, _ls) => _bt && _r < 40 && _ls);
const myShortCond = for_every(myBearTrend, myRsi15, myShortSignal, (_bt, _r, _ss) => _bt && _r > 60 && _ss);

// ----------------
// ATR and reference levels (close used as proxy for position avg price)
// ----------------

const myAtr = atr(high, low, close, myAtrLen);

const myStopLong = sub(close, mult(myAtr, myStopATR));
const myTpLong = add(close, mult(myAtr, myTpATR));
const myStopShort = add(close, mult(myAtr, myStopATR));
const myTpShort = sub(close, mult(myAtr, myTpATR));

const myDca1Long = sub(close, mult(myAtr, myDca1ATR));
const myDca2Long = sub(close, mult(myAtr, myDca2ATR));
const myDca1Short = add(close, mult(myAtr, myDca1ATR));
const myDca2Short = add(close, mult(myAtr, myDca2ATR));

// Sparse levels only at signal bars
const myStopLongSeries = for_every(myLongCond, myStopLong, (_c, _v) => _c ? _v : null);
const myTpLongSeries = for_every(myLongCond, myTpLong, (_c, _v) => _c ? _v : null);
const myDca1LongSeries = for_every(myLongCond, myDca1Long, (_c, _v) => _c ? _v : null);
const myDca2LongSeries = for_every(myLongCond, myDca2Long, (_c, _v) => _c ? _v : null);

const myStopShortSeries = for_every(myShortCond, myStopShort, (_c, _v) => _c ? _v : null);
const myTpShortSeries = for_every(myShortCond, myTpShort, (_c, _v) => _c ? _v : null);
const myDca1ShortSeries = for_every(myShortCond, myDca1Short, (_c, _v) => _c ? _v : null);
const myDca2ShortSeries = for_every(myShortCond, myDca2Short, (_c, _v) => _c ? _v : null);

// ----------------
// Painting
// ----------------

const myLongMarks = for_every(myLongCond, _c => _c ? 1 : null);
const myShortMarks = for_every(myShortCond, _c => _c ? 1 : null);

paint(myLongMarks, { name: 'Long Signal', style: 'labels_below', color: 'green', thickness: 3, forceUsePriceAxis: true });
paint(myShortMarks, { name: 'Short Signal', style: 'labels_above', color: 'red', thickness: 3, forceUsePriceAxis: true });

paint(myStopLongSeries, { name: 'Stop Long', style: 'dotted', color: 'red', forceUsePriceAxis: true });
paint(myTpLongSeries, { name: 'TP Long', style: 'dotted', color: 'green', forceUsePriceAxis: true });
paint(myDca1LongSeries, { name: 'DCA1 Long', style: 'dotted', color: 'orange', forceUsePriceAxis: true });
paint(myDca2LongSeries, { name: 'DCA2 Long', style: 'dotted', color: 'orange', forceUsePriceAxis: true });

paint(myStopShortSeries, { name: 'Stop Short', style: 'dotted', color: 'red', forceUsePriceAxis: true });
paint(myTpShortSeries, { name: 'TP Short', style: 'dotted', color: 'green', forceUsePriceAxis: true });
paint(myDca1ShortSeries, { name: 'DCA1 Short', style: 'dotted', color: 'orange', forceUsePriceAxis: true });
paint(myDca2ShortSeries, { name: 'DCA2 Short', style: 'dotted', color: 'orange', forceUsePriceAxis: true });

// ----------------
// Signals for scanner/alerts/backtest
// ----------------

register_signal(myLongCond, 'Long Entry Signal');
register_signal(myShortCond, 'Short Entry Signal');
register_signal(myBullTrend, 'Bull Trend 1h');
register_signal(myBearTrend, 'Bear Trend 1h');