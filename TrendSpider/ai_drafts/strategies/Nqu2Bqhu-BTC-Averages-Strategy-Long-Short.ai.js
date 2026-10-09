describe_indicator('BTC Averages Strategy - Long and Short', 'price');

// Inputs matching Pine script parameters
const myFastLen = input.number('Fast MA Period', 3, { min: 1, max: 1000 });
const mySlowLen = input.number('Slow MA Period', 48, { min: 1, max: 1000 });
const myTrendLen = input.number('Trend MA Period', 168, { min: 1, max: 2000 });

const myMaFast = sma(close, myFastLen);
const myMaSlow = sma(close, mySlowLen);
const myMaTrend = sma(close, myTrendLen);

// Entry / exit conditions, replicated exactly from the Pine script
const myLongEntry = for_every(myMaFast, myMaSlow, close, myMaTrend, (_f, _s, _c, _t) => _f > _s && _c > _t);
const myLongExit = for_every(myMaFast, myMaSlow, (_f, _s) => _f < _s);

const myShortEntry = for_every(myMaFast, myMaSlow, close, myMaTrend, (_f, _s, _c, _t) => _f < _s && _c < _t);
const myShortExit = for_every(myMaFast, myMaSlow, (_f, _s) => _f > _s);

// Background coloring based on trend (close vs trend MA)
const myCandleColors = for_every(close, myMaTrend, (_c, _t) => _c > _t ? 'rgba(0,180,0,0.1)' : 'rgba(200,0,0,0.1)');
color_candles(myCandleColors);

// Visuals: the 3 moving averages
paint(myMaFast, { name: 'Fast MA', color: '#2962FF', thickness: 1 });
paint(myMaSlow, { name: 'Slow MA', color: '#FF9800', thickness: 1 });
paint(myMaTrend, { name: 'Trend MA', color: '#E0E0E0', thickness: 2 });

// Signals for use in Scanners, Alerts and Strategy Tester
register_signal(myLongEntry, 'Long Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortEntry, 'Short Entry');
register_signal(myShortExit, 'Short Exit');