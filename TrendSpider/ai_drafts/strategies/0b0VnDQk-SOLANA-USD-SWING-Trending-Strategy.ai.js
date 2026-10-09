describe_indicator('SOL Intraday Trend and ADX Filter', 'price');

// NOTE: this is a best-effort conversion from Pine Script.
// TrendSpider Custom JS has no strategy/backtest engine (no
// strategy.entry/strategy.exit), so trade execution and the
// trailing stop-loss logic are NOT reproduced. Instead this
// script exposes Long/Short entry conditions as signals usable
// in Scanners, Alerts and the Strategy Tester visual script tool.
// Also, the built-in supertrend() function only returns the
// Supertrend line, not its direction flag, so direction is
// approximated as "close above supertrend => uptrend", which is
// mathematically equivalent to Pine's direction < 0 condition.
// Finally, Pine's adx() uses separate DI Length and ADX Smoothing
// parameters; the built-in indicators.adx() only accepts a single
// period, so dilen is used as that single period (an approximation).

const myTab = input.tab('Settings');

const stGroup = myTab.group('Supertrend');
const myAtrPeriod = stGroup.number('Supertrend ATR Length', 10, { min: 1, max: 100 });
const myFactor = stGroup.number('Supertrend Factor', 3.0, { min: 0.1, max: 20, step: 0.1 });

const adxGroup = myTab.group('ADX Filter');
const myAdxLen = adxGroup.number('ADX Smoothing', 14, { min: 1, max: 100 });
const myDiLen = adxGroup.number('DI Length', 14, { min: 1, max: 100 });
const myAdxThreshold = adxGroup.number('ADX Threshold', 25, { min: 1, max: 100 });

// --- Heikin Ashi data, fetched on the same ticker/resolution ---
const myHaData = await request.history(current.ticker, current.resolution, { chart_type: 'heikinashi' });
assert(!myHaData.error, `Error fetching Heikin Ashi data: "${myHaData.error}"`);

const myHaCloseLanded = land_points_onto_series(myHaData.time, myHaData.close, time, 'eq');
const myHaOpenLanded = land_points_onto_series(myHaData.time, myHaData.open, time, 'eq');

const myHaClose = interpolate_sparse_series(myHaCloseLanded, 'constant');
const myHaOpen = interpolate_sparse_series(myHaOpenLanded, 'constant');

const myHaBullish = for_every(myHaClose, myHaOpen, (_c, _o) => _c != null && _o != null && _c > _o);
const myHaBearish = for_every(myHaClose, myHaOpen, (_c, _o) => _c != null && _o != null && _c < _o);

// --- Supertrend ---
const mySupertrend = supertrend(myAtrPeriod, myFactor, false);
// direction < 0 (bullish) in Pine corresponds to close being above the Supertrend line
const myBullishTrend = for_every(close, mySupertrend, (_c, _s) => _c > _s);
const myBearishTrend = for_every(close, mySupertrend, (_c, _s) => _c < _s);

// --- ADX ---
const myAdxObject = indicators.adx(myDiLen);
const myAdx = myAdxObject.adx;
const myIsTrending = for_every(myAdx, _a => _a > myAdxThreshold);

// --- Entry conditions ---
const myLongCondition = for_every(myBullishTrend, myIsTrending, myHaBullish, (_bt, _tr, _hb) => _bt && _tr && _hb);
const myShortCondition = for_every(myBearishTrend, myIsTrending, myHaBearish, (_bt, _tr, _hb) => _bt && _tr && _hb);

register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myIsTrending, 'Market Is Trending');

// --- Visuals ---
const mySupertrendColor = for_every(myBullishTrend, _bt => _bt ? '#26A69A' : '#EF5350');
paint(mySupertrend, { name: 'Supertrend', color: mySupertrendColor, thickness: 2 });