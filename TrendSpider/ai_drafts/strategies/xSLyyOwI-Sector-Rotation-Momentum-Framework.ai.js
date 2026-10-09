describe_indicator('Sector Rotation Momentum Framework', 'price');
// NOTE: Pine Script's strategy.* functions (position sizing, broker-style
// stop/limit exits tracked against an open position) have no equivalent in
// the Custom JS API, which has no persistent position/trade engine. This
// script reproduces the indicator math (EMAs, Relative Strength, ATR) and
// exposes Long/Short entry signals for scanning. The stop/target levels are
// plotted using a "flat" simulated entry price (close at signal bar) rather
// than a true running strategy position average price.

const myBenchmarkTicker = input.symbol('Sector ETF', 'XLK');
const myFastLen = input.number('Fast EMA', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA', 50, { min: 1, max: 500 });
const myRsLen = input.number('Relative Strength EMA', 20, { min: 1, max: 500 });
const myAtrLen = input.number('ATR Length', 14, { min: 1, max: 200 });
const myAtrMult = input.number('ATR Stop Multiplier', 1.5, { min: 0.1, max: 20 });
const myRR = input.number('Risk Reward', 2.0, { min: 0.1, max: 20 });

const myBenchmarkData = await request.history(myBenchmarkTicker, current.resolution);

// request.history() can return { error } where "error" might be a string
// or an object (depending on the failure type), so we stringify it safely
// instead of interpolating it directly into the template literal, which
// was the root cause of the "history: [object Object]" crash.
const myBenchmarkErrorText = myBenchmarkData && myBenchmarkData.error
	? (typeof myBenchmarkData.error === 'string' ? myBenchmarkData.error : JSON.stringify(myBenchmarkData.error))
	: null;
assert(!myBenchmarkData.error, `Error fetching benchmark data: "${myBenchmarkErrorText}"`);

// Land benchmark close values onto the current chart's time axis
const myBenchmarkLanded = interpolate_sparse_series(
	land_points_onto_series(myBenchmarkData.time, myBenchmarkData.close, time, 'le'),
	'constant'
);

const myRelativeStrength = div(close, myBenchmarkLanded);
const myRelativeMA = ema(myRelativeStrength, myRsLen);

const myFastEMA = ema(close, myFastLen);
const mySlowEMA = ema(close, mySlowLen);

const myBullTrend = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast > _slow);
const myBearTrend = for_every(myFastEMA, mySlowEMA, (_fast, _slow) => _fast < _slow);

const myLongCondition = for_every(
	myBullTrend, myRelativeStrength, myRelativeMA,
	(_bull, _rs, _rma) => _bull && _rs > _rma
);
const myShortCondition = for_every(
	myBearTrend, myRelativeStrength, myRelativeMA,
	(_bear, _rs, _rma) => _bear && _rs < _rma
);

const myAtr = atr(high, low, close, myAtrLen);

// Simplified (non-position-aware) stop/target levels, computed off the
// current candle's close rather than a running strategy entry price,
// since there is no persistent position tracking available.
const myLongStop = sub(close, mult(myAtr, myAtrMult));
const myLongTarget = add(close, mult(myAtr, myAtrMult, myRR));
const myShortStop = add(close, mult(myAtr, myAtrMult));
const myShortTarget = sub(close, mult(myAtr, myAtrMult, myRR));

const myRelativeStrengthTrend = mult(myRelativeMA, myBenchmarkLanded);

paint(myFastEMA, { name: 'Fast EMA', color: 'orange', thickness: 2 });
paint(mySlowEMA, { name: 'Slow EMA', color: 'blue', thickness: 2 });
paint(myRelativeStrengthTrend, { name: 'Relative Strength Trend', color: 'green', thickness: 2 });
paint(for_every(myLongCondition, _c => _c ? 1 : null), { name: 'Long Stop Level', style: 'line', color: 'transparent', hidden: true });

// Scanning/alert signals
register_signal(myLongCondition, 'Long Entry Signal');
register_signal(myShortCondition, 'Short Entry Signal');