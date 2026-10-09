describe_indicator('BTC Trend Strategy V2 Signals', 'price');

// NOTE: TrendSpider custom indicators cannot place orders, manage
// position size, or implement broker-level trailing stops like a
// Pine Script `strategy()`. This script reproduces the exact signal
// logic (trend filters, entry/exit conditions) as an indicator with
// register_signal() outputs so it can be used in Scanners, Alerts
// and the Strategy Tester (entries/exits only, no position sizing).

const myTab = input.tab('Trend');
const myHtfTf = myTab.select('Higher Timeframe', '240', constants.time_frames);
const myHtfEmaLen = myTab.number('HTF EMA Length', 200, { min: 1, max: 1000 });
const myFastLen = myTab.number('Fast EMA', 21, { min: 1, max: 500 });
const mySlowLen = myTab.number('Slow EMA', 55, { min: 1, max: 1000 });

const myRsiTab = input.tab('RSI / ATR / ADX');
const myRsiLen = myRsiTab.number('RSI Length', 14, { min: 1, max: 200 });
const myRsiLongMin = myRsiTab.number('RSI Long Min', 55, { min: 0, max: 100 });
const myRsiShortMax = myRsiTab.number('RSI Short Max', 45, { min: 0, max: 100 });
const myAtrLen = myRsiTab.number('ATR Length', 14, { min: 1, max: 200 });
const myStopAtr = myRsiTab.number('Stop ATR', 1.8, { min: 0, max: 20, step: 0.1 });
const myTrailAtr = myRsiTab.number('Trailing ATR', 1.5, { min: 0, max: 20, step: 0.1 });
const myAdxLen = myRsiTab.number('ADX Length', 14, { min: 1, max: 200 });
const myAdxMin = myRsiTab.number('Min Trend Strength', 20, { min: 0, max: 100 });

const myVisTab = input.tab('Visuals');
const myShowMAs = myVisTab.boolean('Show Moving Averages', true);

// ───────────── CALCULATIONS ─────────────
const myFastEma = ema(close, myFastLen);
const mySlowEma = ema(close, mySlowLen);
const myRsiVal = rsi(close, myRsiLen);
const myAtrVal = atr(high, low, close, myAtrLen);

const myAdxObject = indicators.adx(myAdxLen);
const myPlusDI = myAdxObject.dmiPlus;
const myMinusDI = myAdxObject.dmiMinus;
const myAdxVal = myAdxObject.adx;

// HTF EMA, requested from the higher time frame and landed onto this chart
const myHtfData = await request.history(current.ticker, myHtfTf);
assert(!myHtfData.error, 'Error fetching HTF data: ' + myHtfData.error);
const myHtfEmaRaw = ema(myHtfData.close, myHtfEmaLen);
const myHtfEmaLanded = land_points_onto_series(myHtfData.time, myHtfEmaRaw, time, 'ge');
const myHtfEma = interpolate_sparse_series(myHtfEmaLanded, 'constant');

// Trend
const myBullTrend = for_every(close, myHtfEma, myFastEma, mySlowEma, (_c, _h, _f, _s) => _c > _h && _f > _s);
const myBearTrend = for_every(close, myHtfEma, myFastEma, mySlowEma, (_c, _h, _f, _s) => _c < _h && _f < _s);

// Filters
const myStrongTrend = for_every(myAdxVal, _a => _a > myAdxMin);
const myAtrSma20 = sma(myAtrVal, 20);
const myHighVol = for_every(myAtrVal, myAtrSma20, (_a, _s) => _a > _s);

// Smart entries (pullback based)
const myLongCondition = for_every(
	myBullTrend, myStrongTrend, myHighVol, myPlusDI, myMinusDI, low, close, myFastEma, myRsiVal,
	(_bull, _strong, _vol, _pdi, _mdi, _lo, _cl, _fast, _rsi) =>
		_bull && _strong && _vol && _pdi > _mdi && _lo <= _fast && _cl > _fast && _rsi > myRsiLongMin
);

const myShortCondition = for_every(
	myBearTrend, myStrongTrend, myHighVol, myPlusDI, myMinusDI, high, close, myFastEma, myRsiVal,
	(_bear, _strong, _vol, _pdi, _mdi, _hi, _cl, _fast, _rsi) =>
		_bear && _strong && _vol && _mdi > _pdi && _hi >= _fast && _cl < _fast && _rsi < myRsiShortMax
);

// ───────────── RISK MANAGEMENT (reference values only) ─────────────
// Position sizing and equity are not available inside a custom
// indicator; stop/trailing distances below are provided as reference
// series only (useful for alerts/labels), not as actual order management.
const myStopDist = mult(myAtrVal, myStopAtr);
const myTrailDist = mult(myAtrVal, myTrailAtr);

// ───────────── EXIT SIGNALS ─────────────
// Emergency close signals (approximation of strategy.close logic)
const myCloseLongSignal = myBearTrend;
const myCloseShortSignal = myBullTrend;

// ───────────── VISUALS ─────────────
paint(myShowMAs ? myFastEma : constants.empty_series, { name: 'FastEMA', color: '#26A69A', thickness: 2 });
paint(myShowMAs ? mySlowEma : constants.empty_series, { name: 'SlowEMA', color: '#FF9800', thickness: 2 });
paint(myShowMAs ? myHtfEma : constants.empty_series, { name: 'HTFEMA', color: '#9C27B0', thickness: 2 });

const myBuyMarks = for_every(myLongCondition, _l => _l ? 1 : null);
const mySellMarks = for_every(myShortCondition, _s => _s ? 1 : null);

paint(myBuyMarks, { name: 'Buy', style: 'labels_below', color: 'green' });
paint(mySellMarks, { name: 'Sell', style: 'labels_above', color: 'red' });

// ───────────── SIGNALS (for Scanners / Alerts / Strategy Tester) ─────────────
register_signal(myLongCondition, 'Long Entry');
register_signal(myShortCondition, 'Short Entry');
register_signal(myCloseLongSignal, 'Close Long');
register_signal(myCloseShortSignal, 'Close Short');
register_signal(myBullTrend, 'Bull Trend');
register_signal(myBearTrend, 'Bear Trend');