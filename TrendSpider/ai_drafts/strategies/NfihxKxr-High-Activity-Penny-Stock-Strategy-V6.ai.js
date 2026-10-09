describe_indicator('High Activity Penny Stock Strategy V6', 'price');

// This indicator reproduces the entry signal logic (SuperTrend flip +
// volume filter + trend filter) from the Pine Script. TrendSpider
// Custom JS indicators cannot execute broker-style strategy orders
// (strategy.entry/exit, take profit/stop loss, position sizing). Those
// parts of the Pine script are not representable here; use the
// TrendSpider Strategy Tester (built on top of these signals) for
// backtesting trade management.

const coreTab = input.tab('Core Settings');
const myAtrPeriod = coreTab.number('Sensitivity (ATR Period)', 10, { min: 1, max: 100 });
const myMultiplier = coreTab.number('Aggression (Multiplier)', 2.0, { min: 0.1, max: 20 });

const filtersTab = input.tab('Filters');
const myUseVolFilter = filtersTab.boolean('Enable Volume Filter', true);
const myVolThreshold = filtersTab.number('Volume Multiplier', 1.2, { min: 0.1, max: 10 });
const myUseSmaFilter = filtersTab.boolean('Enable Trend Filter', true);
const mySmaLength = filtersTab.number('Trend Filter (SMA)', 50, { min: 1, max: 500 });

// --- Calculations ---
// Custom JS does not expose SuperTrend direction directly, so direction
// is derived the standard way: close above the SuperTrend line means an
// uptrend (direction = -1, matching Pine's convention), close below
// means a downtrend (direction = 1).
const mySupertrendLine = supertrend(myAtrPeriod, myMultiplier, false);
const myDirection = for_every(close, mySupertrendLine, (_c, _st) => (_c > _st ? -1 : 1));
const myPrevDirection = shift(myDirection, 1);

const myAvgVolume = sma(volume, 20);
const mySmaValue = sma(close, mySmaLength);

const myVolOk = for_every(volume, myAvgVolume, (_v, _av) => !myUseVolFilter || (_v > _av * myVolThreshold));
const myTrendOkBuy = for_every(close, mySmaValue, (_c, _s) => !myUseSmaFilter || (_c > _s));
const myTrendOkSell = for_every(close, mySmaValue, (_c, _s) => !myUseSmaFilter || (_c < _s));

// --- Signal Logic ---
const myBuySignal = for_every(myDirection, myPrevDirection, myVolOk, myTrendOkBuy,
	(_dir, _prevDir, _volOk, _trendOk) => (_dir < 0) && (_prevDir >= 0) && _volOk && _trendOk);

const mySellSignal = for_every(myDirection, myPrevDirection, myVolOk, myTrendOkSell,
	(_dir, _prevDir, _volOk, _trendOk) => (_dir > 0) && (_prevDir <= 0) && _volOk && _trendOk);

// --- Visuals ---
const mySmaToPaint = myUseSmaFilter ? mySmaValue : constants.empty_series;
paint(mySmaToPaint, { name: 'TrendFilter', color: '#4DA3FF', thickness: 2 });

const myBuyMarks = for_every(myBuySignal, _b => (_b ? true : null));
const mySellMarks = for_every(mySellSignal, _s => (_s ? true : null));

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// --- Scanner / Alert / Strategy Tester signals ---
register_signal(myBuySignal, 'Buy Signal');
register_signal(mySellSignal, 'Sell Signal');