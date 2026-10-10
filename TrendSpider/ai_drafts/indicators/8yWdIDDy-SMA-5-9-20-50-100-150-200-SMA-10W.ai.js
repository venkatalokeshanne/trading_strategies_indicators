// Converted from TradingView Pine Script. Overlay indicator with
// 5/9/20/50/100/150/200 daily SMAs plus a 10-week SMA, and an optional
// info overlay (ADR%, ATR, LoD distance). Scanning/strategy signals are
// exposed via register_signal() for crosses and price vs SMA relations.
describe_indicator('Medias Moviles 5 9 20 50 100 150 200 plus SMA10W', 'price');

// ───────────────────────────── General inputs ─────────────────────────────
const myGeneralTab = input.tab('General');
const myShowEmptyRow = myGeneralTab.boolean('Show Empty Row (Avoid overlapping)', false);

const myAdrGroup = myGeneralTab.group('ADR Percent Settings');
const myShowAdrp = myAdrGroup.boolean('Show ADR Percent', true);
const myAdrpLen = myAdrGroup.number('ADR Percent Length', 20, { min: 1, max: 200 });

const myAtrGroup = myGeneralTab.group('ATR Settings');
const myShowAtr = myAtrGroup.boolean('Show ATR', false);
const myAtrLen = myAtrGroup.number('ATR Length', 14, { min: 1, max: 200 });

const myLodGroup = myGeneralTab.group('LoD Dist Settings');
const myShowLodDist = myLodGroup.boolean('Show LoD Dist', true);

// ───────────────────────────── Daily SMAs ─────────────────────────────────
const mySma5 = sma(close, 5);
const mySma9 = sma(close, 9);
const mySma20 = sma(close, 20);
const mySma50 = sma(close, 50);
const mySma100 = sma(close, 100);
const mySma150 = sma(close, 150);
const mySma200 = sma(close, 200);

paint(mySma5, { name: 'SMA5', color: '#00e5ff', thickness: 2 });
paint(mySma9, { name: 'SMA9', color: '#2ecc71', thickness: 2 });
paint(mySma20, { name: 'SMA20', color: '#f4d03f', thickness: 2 });
paint(mySma50, { name: 'SMA50', color: '#f39c12', thickness: 2 });
paint(mySma100, { name: 'SMA100', color: '#e74c3c', thickness: 2 });
paint(mySma150, { name: 'SMA150', color: '#3498db', thickness: 2 });
paint(mySma200, { name: 'SMA200', color: '#c0392b', thickness: 2 });

// ───────────────────────────── Weekly SMA(10) ──────────────────────────────
// request.security(..., 'W', ta.sma(close,10), lookahead_on) is reproduced
// here using request.history + land_points_onto_series. Note: lookahead_on
// in Pine means "future looking" repainting behavior that is not safe for
// backtesting; we instead use the constant-interpolation (non-repainting)
// equivalent, which is the closest safe approximation available here.
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);
const mySma10Weekly = sma(myWeeklyData.close, 10);
const mySma10WeeklyLanded = land_points_onto_series(myWeeklyData.time, mySma10Weekly, time, 'ge');
const mySma10WeeklyFinal = interpolate_sparse_series(mySma10WeeklyLanded, 'constant');

paint(mySma10WeeklyFinal, { name: 'SMA10W', color: '#ffffff', thickness: 4, style: 'dotted' });

// ───────────────────────────── Daily stats (ADR%, ATR, LoD dist) ──────────
// Pine uses [1] + lookahead_on on a Daily security call to get the prior
// completed daily bar's value, both on history and real time (no repaint).
// We approximate this using the Daily history's second-to-last candle
// (last fully closed daily bar), landed onto the current timeframe.
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const myHighLowRatio = for_every(myDailyData.high, myDailyData.low, (_h, _l) => _l !== 0 ? _h / _l : null);
const myAdrRatioSeries = sma(myHighLowRatio, myAdrpLen);
const myAtrSeries = atr(myDailyData.high, myDailyData.low, myDailyData.close, myAtrLen);

// Shift by 1 to emulate Pine's [1] (prior completed daily bar)
const myAdrRatioShifted = shift(myAdrRatioSeries, 1);
const myAtrShifted = shift(myAtrSeries, 1);

const myAdrpDaily = for_every(myAdrRatioShifted, _r => _r === null ? null : 100 * (_r - 1));

const myAdrpLanded = land_points_onto_series(myDailyData.time, myAdrpDaily, time, 'ge');
const myAdrpFinal = interpolate_sparse_series(myAdrpLanded, 'constant');

const myAtrLanded = land_points_onto_series(myDailyData.time, myAtrShifted, time, 'ge');
const myAtrFinal = interpolate_sparse_series(myAtrLanded, 'constant');

// LoD distance: 100 * (RTH close - RTH low) / RTH low. Pine computes this
// from a regular-session-only daily ticker that updates intrabar in real
// time. We can only use completed daily candles here, so this becomes the
// "distance from today's close to today's low" of the last completed daily
// bar, landed onto the current timeframe (an approximation of the live
// intrabar value).
const myLodDistDaily = for_every(myDailyData.close, myDailyData.low, (_c, _l) => (_l === null || _l === 0) ? null : 100 * (_c - _l) / _l);
const myLodDistLanded = land_points_onto_series(myDailyData.time, myLodDistDaily, time, 'ge');
const myLodDistFinal = interpolate_sparse_series(myLodDistLanded, 'constant');

// ───────────────────────────── Info overlay (table) ───────────────────────
const myLastIndex = close.length - 1;
const myAdrpValue = myAdrpFinal[myLastIndex];
const myAtrValue = myAtrFinal[myLastIndex];
const myLodDistValue = myLodDistFinal[myLastIndex];

const myFormat = (_v, _suffix) => (_v === null || _v === undefined || isNaN(_v)) ? 'n/a' : (Math.round(_v * 100) / 100).toFixed(2) + _suffix;

const myTableRows = [];

if (myShowEmptyRow) {
	myTableRows.push({ cells: [{ text: '' }, { text: '' }] });
}
if (myShowAdrp) {
	myTableRows.push({ cells: [{ text: 'ADR Percent', color: '#00e5ff' }, { text: myFormat(myAdrpValue, '%'), color: '#00e5ff' }] });
}
if (myShowAtr) {
	myTableRows.push({ cells: [{ text: 'ATR', color: '#f39c12' }, { text: myFormat(myAtrValue, ''), color: '#f39c12' }] });
}
if (myShowLodDist) {
	myTableRows.push({ cells: [{ text: 'LoD Dist', color: '#e74c3c' }, { text: myFormat(myLodDistValue, '%'), color: '#e74c3c' }] });
}

paint_overlay('InfoTable', { position: 'top_right' }, { rows: myTableRows });

// ───────────────────────────── Scan/Strategy signals ───────────────────────
const myCloseAboveSma5 = for_every(close, mySma5, (_c, _s) => _c > _s);
const myCloseAboveSma20 = for_every(close, mySma20, (_c, _s) => _c > _s);
const myCloseAboveSma50 = for_every(close, mySma50, (_c, _s) => _c > _s);
const myCloseAboveSma200 = for_every(close, mySma200, (_c, _s) => _c > _s);
const myCloseAboveSma10w = for_every(close, mySma10WeeklyFinal, (_c, _s) => _s !== null && _c > _s);

const myGoldenCross5020 = for_every(mySma20, mySma50, (_s20, _s50, _prev, _idx) => {
	if (_idx < 1) return false;
	return mySma20[_idx - 1] <= mySma50[_idx - 1] && _s20 > _s50;
});

const myDeathCross5020 = for_every(mySma20, mySma50, (_s20, _s50, _prev, _idx) => {
	if (_idx < 1) return false;
	return mySma20[_idx - 1] >= mySma50[_idx - 1] && _s20 < _s50;
});

const myGoldenCross50200 = for_every(mySma50, mySma200, (_s50, _s200, _prev, _idx) => {
	if (_idx < 1) return false;
	return mySma50[_idx - 1] <= mySma200[_idx - 1] && _s50 > _s200;
});

const myDeathCross50200 = for_every(mySma50, mySma200, (_s50, _s200, _prev, _idx) => {
	if (_idx < 1) return false;
	return mySma50[_idx - 1] >= mySma200[_idx - 1] && _s50 < _s200;
});

register_signal(myCloseAboveSma5, 'Close Above SMA5');
register_signal(myCloseAboveSma20, 'Close Above SMA20');
register_signal(myCloseAboveSma50, 'Close Above SMA50');
register_signal(myCloseAboveSma200, 'Close Above SMA200');
register_signal(myCloseAboveSma10w, 'Close Above SMA10W');
register_signal(myGoldenCross5020, 'Golden Cross SMA20 SMA50');
register_signal(myDeathCross5020, 'Death Cross SMA20 SMA50');
register_signal(myGoldenCross50200, 'Golden Cross SMA50 SMA200');
register_signal(myDeathCross50200, 'Death Cross SMA50 SMA200');