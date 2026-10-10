// ── Dynamic Volatility Bull Bear Threshold ────────────────
describe_indicator('Dynamic Volatility Bull Bear Threshold Antonx0.8', 'price');

// ── Inputs ──────────────────────────────────────────────
const myTab = input.tab('Settings');
// Shortened title to satisfy input name length limit
const myLookback = myTab.number('Lookback (bars)', 252, { min: 30, max: 500 });
const myN = myTab.number('Vol multiple N (0.8 to 2.5)', 1.2, { min: 0.5, max: 4.0, step: 0.1 });
const myMaLen = myTab.number('Bull confirm MA period', 200, { min: 50, max: 400, step: 10 });
const myRow = myTab.row();
const myShowFixed = myRow.boolean('Overlay fixed 20 percent line', true);
const myShowMA = myRow.boolean('Show confirm MA', true);
const myShowTable = myTab.boolean('Show info table', true);

// ── Annualized volatility, auto adjusted to chart timeframe ──
// Pine's timeframe.isintraday / isweekly / ismonthly are approximated
// using current.resolution: numeric strings are intraday minutes,
// 'D' is daily, 'W' is weekly, 'M' is monthly. Anything else defaults to 252.
const myResolution = current.resolution;
const myIsIntraday = !isNaN(Number(myResolution));
let myBarsPerYear = 252;

if (myIsIntraday) {
	myBarsPerYear = Math.round(252.0 * 390.0 / Number(myResolution));
}
else if (myResolution === 'W') {
	myBarsPerYear = 52;
}
else if (myResolution === 'M') {
	myBarsPerYear = 12;
}

const myRet = sub(div(close, shift(close, 1)), 1);
const mySigmaAnRaw = mult(stdev(myRet, myLookback), Math.sqrt(myBarsPerYear));

// ── Rolling high and dynamic bear level ─────────────────
const myHH = highest(high, myLookback);

// Drawdown threshold = N * sigma, clamped between 5% and 60%
const myDdThresh = for_every(mySigmaAnRaw, _s => Math.min(0.6, Math.max(0.05, myN * _s)));
const myBearDyn = for_every(myHH, myDdThresh, (_hh, _dd) => _hh * (1 - _dd));
const myBearFix = mult(myHH, 0.8);
const mySmaLong = sma(close, myMaLen);

// ── State logic ─────────────────────────────────────────
const myInBear = for_every(close, myBearDyn, (_c, _b) => _c < _b);
const myAboveMA = for_every(close, mySmaLong, (_c, _m) => _c > _m);
const myInBull = for_every(myInBear, myAboveMA, (_ib, _am) => !_ib && _am);

// State-change markers, computed by comparing current state to previous bar
const myBearTrigger = for_every(myInBear, shift(myInBear, 1), (_cur, _prev) => Boolean(_cur) && !_prev);
const myBullConfirm = for_every(myInBull, shift(myInBull, 1), (_cur, _prev) => Boolean(_cur) && !_prev);
const myBelowFix = for_every(close, myBearFix, (_c, _f) => _c < _f);
const myEarlyWarn = for_every(myBelowFix, shift(myBelowFix, 1), (_cur, _prev) => Boolean(_cur) && !_prev);

// ── Background shading equivalent (candle coloring, light tint) ──
const myCandleColors = for_every(myInBear, myInBull, (_ib, _ibull) => {
	if (_ib) return 'rgba(239,83,80,0.18)';
	if (_ibull) return 'rgba(38,166,154,0.15)';
	return 'rgba(255,215,0,0.12)';
});
color_candles(myCandleColors);

// ── Main plots ───────────────────────────────────────────
paint(myHH, { name: 'Rolling High', color: 'gray', thickness: 1, style: 'line' });
paint(myBearDyn, { name: 'Dynamic Bear', color: '#EF5350', thickness: 2, style: 'line' });
paint(myShowFixed ? myBearFix : series_of(null), { name: 'Fixed Twenty Percent Line', color: '#FFA726', thickness: 1, style: 'line' });
paint(myShowMA ? mySmaLong : series_of(null), { name: 'Confirm MA', color: '#42A5F5', thickness: 1, style: 'line' });

// ── State-change markers (shapes equivalent) ──────────────
const myBearTriggerMarks = for_every(myBearTrigger, high, (_t, _h) => _t ? _h : null);
const myBullConfirmMarks = for_every(myBullConfirm, low, (_t, _l) => _t ? _l : null);
const myEarlyWarnMarks = for_every(myEarlyWarn, high, (_t, _h) => _t ? _h : null);

paint(myBearTriggerMarks, { name: 'Bear Dynamic Trigger', style: 'labels_above', color: 'red' });
paint(myBullConfirmMarks, { name: 'Bull Confirm Mark', style: 'labels_below', color: 'green' });
paint(myEarlyWarnMarks, { name: 'Twenty Percent Line Alert', style: 'labels_above', color: 'orange' });

// ── Scanning and strategy signals ─────────────────────────
register_signal(myBearTrigger, 'Bear (Dynamic)');
register_signal(myEarlyWarn, '20% Drawdown');
register_signal(myBullConfirm, 'Bull Confirm');
register_signal(myInBear, 'In Bear State');
register_signal(myInBull, 'In Bull State');

// ── Info table (approximation of the Pine table) ──────────
const myLastIndex = close.length - 1;
const mySigmaLast = mySigmaAnRaw[myLastIndex];
const myDdLast = myDdThresh[myLastIndex];
const myHHLast = myHH[myLastIndex];
const myBearDynLast = myBearDyn[myLastIndex];
const myLevelRatio = myHHLast ? (myBearDynLast / myHHLast) * 100 : null;
const myStatusText = myInBear[myLastIndex] ? 'Bear' : (myInBull[myLastIndex] ? 'Bull' : 'Recovering');

paint_overlay('DynVolInfoTable', { position: 'top_right' }, {
	rows: myShowTable ? [
		{ cells: [{ text: 'Indicator' }, { text: 'Dynamic Vol Bull Bear' }] },
		{ cells: [{ text: 'Ann. Vol' }, { text: (mySigmaLast != null ? (mySigmaLast * 100).toFixed(2) : 'N/A') + '%' }] },
		{ cells: [{ text: 'N' }, { text: String(myN) }] },
		{ cells: [{ text: 'Dyn Drawdown' }, { text: (myDdLast != null ? (myDdLast * 100).toFixed(2) : 'N/A') + '%' }] },
		{ cells: [{ text: 'Level/High' }, { text: (myLevelRatio != null ? myLevelRatio.toFixed(2) : 'N/A') + '%' }] },
		{ cells: [{ text: 'Status' }, { text: myStatusText }] }
	] : []
});