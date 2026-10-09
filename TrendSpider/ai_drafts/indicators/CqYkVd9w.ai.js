describe_indicator('Multi EMA', 'price', { decimals: 2 });

// Direct translation of the Pine Script: 7 EMAs on Close,
// same lengths, same price source, plotted on the price axis.
const myEma5 = ema(close, 5);
const myEma10 = ema(close, 10);
const myEma20 = ema(close, 20);
const myEma30 = ema(close, 30);
const myEma60 = ema(close, 60);
const myEma90 = ema(close, 90);
const myEma180 = ema(close, 180);

paint(myEma5, { name: 'EMA5', color: 'red', thickness: 1 });
paint(myEma10, { name: 'EMA10', color: 'orange', thickness: 1 });
paint(myEma20, { name: 'EMA20', color: 'aqua', thickness: 1 });
paint(myEma30, { name: 'EMA30', color: 'blue', thickness: 1 });
paint(myEma60, { name: 'EMA60', color: 'purple', thickness: 1 });
paint(myEma90, { name: 'EMA90', color: 'fuchsia', thickness: 1 });
paint(myEma180, { name: 'EMA180', color: 'teal', thickness: 1 });

// Signals for scanning/alerts/strategy: bullish/bearish crosses
// of fast EMA(5) vs slower EMAs, since the original Pine script
// had no explicit signal logic (plot-only indicator).
const myCross5over20 = for_every(myEma5, myEma20, (_fast, _slow, _prev, _i) => _i > 0 && _fast > _slow);
const myCross5under20 = for_every(myEma5, myEma20, (_fast, _slow, _prev, _i) => _i > 0 && _fast < _slow);
const myCross10over30 = for_every(myEma10, myEma30, (_fast, _slow, _prev, _i) => _i > 0 && _fast > _slow);
const myCross10under30 = for_every(myEma10, myEma30, (_fast, _slow, _prev, _i) => _i > 0 && _fast < _slow);
const myCross20over60 = for_every(myEma20, myEma60, (_fast, _slow, _prev, _i) => _i > 0 && _fast > _slow);
const myCross20under60 = for_every(myEma20, myEma60, (_fast, _slow, _prev, _i) => _i > 0 && _fast < _slow);

register_signal(myCross5over20, 'EMA5 above EMA20');
register_signal(myCross5under20, 'EMA5 below EMA20');
register_signal(myCross10over30, 'EMA10 above EMA30');
register_signal(myCross10under30, 'EMA10 below EMA30');
register_signal(myCross20over60, 'EMA20 above EMA60');
register_signal(myCross20under60, 'EMA20 below EMA60');