describe_indicator('HTF EMA Pullback Strategy', 'price');

// ───────────────────────── Inputs ─────────────────────────
const mainTab = input.tab('Main');
const tfHTF = mainTab.select('Higher Timeframe', 'D', constants.time_frames);
const emaRow = mainTab.row();
const myLenShort = emaRow.number('Short EMA Length', 9, { min: 1, max: 200 });
const myLenLong = emaRow.number('Long EMA Length', 21, { min: 2, max: 400 });
const myUseHTFFilter = mainTab.boolean('Use HTF EMA Filter', true);

const pullbackTab = input.tab('Pullback & Confirmation');
const myPullbackLookback = pullbackTab.number('Pullback Lookback Bars', 6, { min: 1, max: 100 });
// shortened title to satisfy input() name length limit
const myPullbackTolPct = pullbackTab.number('Pullback Tolerance %', 0.20, { min: 0, max: 10, step: 0.05 });
const myRequireCandle = pullbackTab.boolean('Require Candle Confirmation', true);
const myRequireMACD = pullbackTab.boolean('Require MACD Improvement', true);
const macdGroup = pullbackTab.group('MACD');
const macdRow = macdGroup.row();
const myMacdFast = macdRow.number('MACD Fast', 12, { min: 1, max: 100 });
const myMacdSlow = macdRow.number('MACD Slow', 26, { min: 1, max: 200 });
const myMacdSig = macdRow.number('MACD Signal', 9, { min: 1, max: 100 });

const riskTab = input.tab('Risk & Targets');
const myUseRRTarget = riskTab.boolean('Use R:R Target', true);
const myRRMultiple = riskTab.number('Take Profit R Multiple', 1.5, { min: 0.5, max: 20, step: 0.1 });
const pivotRow = riskTab.row();
const myLbL = pivotRow.number('Pivot Left Bars', 2, { min: 1, max: 50 });
const myLbR = pivotRow.number('Pivot Right Bars', 2, { min: 1, max: 50 });

// ───────────────────────── HTF Direction Filter ─────────────────────────
const myHTFData = await request.history(current.ticker, tfHTF);
assert(!myHTFData.error, `Error fetching HTF data: "${myHTFData.error}"`);

const myEmaShortHTFRaw = ema(myHTFData.close, myLenShort);
const myEmaLongHTFRaw = ema(myHTFData.close, myLenLong);

// Land HTF EMAs onto the current chart's time axis (non-repainting: use already-closed HTF bars)
const myEmaShortHTF = interpolate_sparse_series(
	land_points_onto_series(myHTFData.time, myEmaShortHTFRaw, time, 'ge'),
	'constant'
);
const myEmaLongHTF = interpolate_sparse_series(
	land_points_onto_series(myHTFData.time, myEmaLongHTFRaw, time, 'ge'),
	'constant'
);

const myUpTrendHTF = for_every(myEmaShortHTF, myEmaLongHTF, (_s, _l) => _s != null && _l != null && _s > _l);
const myDownTrendHTF = for_every(myEmaShortHTF, myEmaLongHTF, (_s, _l) => _s != null && _l != null && _s < _l);

// ───────────────────────── LTF signals ─────────────────────────
const myEmaShort = ema(close, myLenShort);
const myEmaLong = ema(close, myLenLong);

const myTol = myPullbackTolPct * 0.01;
const myDistRatio = for_every(low, myEmaShort, (_l, _e) => Math.abs(_l - _e) / _e);
const myLowestDist = lowest(myDistRatio, myPullbackLookback);
const myTouchedShortEMA = for_every(myLowestDist, _d => _d <= myTol);

const myOpenPrev = shift(open, 1);
const myClosePrev = shift(close, 1);

const myBullEngulf = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _op, _cp) =>
	_c > _o && _o <= _cp && _op > _cp && _c >= _op);

const myBearEngulf = for_every(close, open, myOpenPrev, myClosePrev, (_c, _o, _op, _cp) =>
	_c < _o && _o >= _cp && _op < _cp && _c <= _op);

const myLowerWickPct = for_every(low, open, close, high, (_l, _o, _c, _h) =>
	(_l < _o ? (_o - _l) : (_c - _l)) / (_h - _l + 1e-10));

// upper wick percent, computed with full tuple (high, open, close, low)
const myUpperWickPctFixed = for_every(high, open, close, low, (_h, _o, _c, _l) =>
	(_h > _o ? (_h - _o) : (_h - _c)) / (_h - _l + 1e-10));

const myLongLowerWick = for_every(myLowerWickPct, _w => _w > 0.4);
const myLongUpperWick = for_every(myUpperWickPctFixed, _w => _w > 0.4);

const myCandleOKLong = myRequireCandle
	? for_every(myBullEngulf, myLongLowerWick, (_b, _w) => _b || _w)
	: for_every(close, () => true);

const myCandleOKShort = myRequireCandle
	? for_every(myBearEngulf, myLongUpperWick, (_b, _w) => _b || _w)
	: for_every(close, () => true);

const myMacd = sub(ema(close, myMacdFast), ema(close, myMacdSlow));
const myMacdSigLine = ema(myMacd, myMacdSig);
const myHist = sub(myMacd, myMacdSigLine);
const myHistPrev = shift(myHist, 1);

const myMacdOKLong = myRequireMACD
	? for_every(myHist, myHistPrev, (_h, _hp) => _h > _hp)
	: for_every(close, () => true);

const myMacdOKShort = myRequireMACD
	? for_every(myHist, myHistPrev, (_h, _hp) => _h < _hp)
	: for_every(close, () => true);

const myCloseAboveShort = for_every(close, myEmaShort, (_c, _e) => _c > _e);
const myCloseBelowShort = for_every(close, myEmaShort, (_c, _e) => _c < _e);

const myLongAllowed = myUseHTFFilter ? myUpTrendHTF : for_every(close, () => true);
const myShortAllowed = myUseHTFFilter ? myDownTrendHTF : for_every(close, () => true);

const myLongSetup = for_every(
	myLongAllowed, myTouchedShortEMA, myCandleOKLong, myMacdOKLong, myCloseAboveShort,
	(_a, _b, _c, _d, _e) => _a && _b && _c && _d && _e);

const myShortSetup = for_every(
	myShortAllowed, myTouchedShortEMA, myCandleOKShort, myMacdOKShort, myCloseBelowShort,
	(_a, _b, _c, _d, _e) => _a && _b && _c && _d && _e);

// ───────────────────────── Stop (pivot) & Targets ─────────────────────────
const myPivotLow = pivot_low(low, myLbL, myLbR);
const myPivotHigh = pivot_high(high, myLbL, myLbR);

const myLongSL = for_every(myPivotLow, (_p, _prev) => _p != null ? _p : (_prev != null ? _prev : null));
const myShortSL = for_every(myPivotHigh, (_p, _prev) => _p != null ? _p : (_prev != null ? _prev : null));

const myLongStop = myLongSL;
const myShortStop = myShortSL;

const myLongTP = for_every(myLongStop, close, (_stop, _c) =>
	(myUseRRTarget && _stop != null) ? _c + (_c - _stop) * myRRMultiple : null);

const myShortTP = for_every(myShortStop, close, (_stop, _c) =>
	(myUseRRTarget && _stop != null) ? _c - (_stop - _c) * myRRMultiple : null);

// ───────────────────────── Entry conditions ─────────────────────────
const myLongEntry = for_every(myLongSetup, myLongStop, close, (_set, _stop, _c) =>
	_set && _stop != null && _c > _stop);

const myShortEntry = for_every(myShortSetup, myShortStop, close, (_set, _stop, _c) =>
	_set && _stop != null && _c < _stop);

// ───────────────────────── Signals (for scanners/alerts/backtests) ─────────────────────────
register_signal(myLongSetup, 'Long Setup');
register_signal(myShortSetup, 'Short Setup');
register_signal(myLongEntry, 'Long Entry');
register_signal(myShortEntry, 'Short Entry');

// ───────────────────────── Visuals ─────────────────────────
paint(myEmaShort, { name: 'EMAShort', color: '#009688', thickness: 2 });
paint(myEmaLong, { name: 'EMALong', color: '#FF9800', thickness: 2 });

const myLongMarker = for_every(myLongSetup, low, (_s, _l) => _s ? _l : null);
const myShortMarker = for_every(myShortSetup, high, (_s, _h) => _s ? _h : null);

paint(myLongMarker, { name: 'LongSetup', style: 'labels_below', color: '#009688' });
paint(myShortMarker, { name: 'ShortSetup', style: 'labels_above', color: '#FF9800' });

// Approximation: TP lines are only meaningful while a position is open.
// Without a strategy/position engine, we show the TP whenever its
// corresponding setup fires and R:R target is enabled.
const myLongTPPlot = for_every(myLongSetup, myLongTP, (_s, _tp) => (_s && myUseRRTarget) ? _tp : null);
const myShortTPPlot = for_every(myShortSetup, myShortTP, (_s, _tp) => (_s && myUseRRTarget) ? _tp : null);

paint(myLongTPPlot, { name: 'LongTP', color: '#009688', style: 'dotted', thickness: 1 });
paint(myShortTPPlot, { name: 'ShortTP', color: '#FF9800', style: 'dotted', thickness: 1 });