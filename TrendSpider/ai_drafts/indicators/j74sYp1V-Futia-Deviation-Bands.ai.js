describe_indicator('Futia Deviation Bands (200D SMA 48M SMA)', 'lower', { decimals: 1 });

// ── Inputs ──────────────────────────────────────────────────────────
const myC1Thresh = input.number('C1 % Below 200D SMA', -10.0, { max: 0, min: -100 });
const myC2Thresh = input.number('C2 % Below 48M SMA', -20.0, { max: 0, min: -100 });
const myUseConf = input.boolean('Use Confirmed Bars', true);

// ── Fetch Daily and Monthly data ────────────────────────────────────
const [myDailyData, myMonthlyData] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'M')
]);
assert(!myDailyData.error, 'Error fetching Daily data: ' + myDailyData.error);
assert(!myMonthlyData.error, 'Error fetching Monthly data: ' + myMonthlyData.error);

// Raw deviation series on their native (Daily/Monthly) timeframes
const myDailySma200 = sma(myDailyData.close, 200);
const myDev200dRawNative = for_every(myDailyData.close, myDailySma200, (_c, _s) => _s ? (_c / _s - 1) * 100 : null);

const myMonthlySma48 = sma(myMonthlyData.close, 48);
const myDev48mRawNative = for_every(myMonthlyData.close, myMonthlySma48, (_c, _s) => _s ? (_c / _s - 1) * 100 : null);

// Confirmed (previous bar) versions, to emulate Pine's lookahead_on with [1] offset,
// which effectively uses the prior completed HTF bar's value (no repaint)
const myDev200dConfNative = shift(myDev200dRawNative, 1);
const myDev48mConfNative = shift(myDev48mRawNative, 1);

// Choose raw vs confirmed, native resolution series
const myDev200dNativeChosen = myUseConf ? myDev200dConfNative : myDev200dRawNative;
const myDev48mNativeChosen = myUseConf ? myDev48mConfNative : myDev48mRawNative;

// Land the HTF values onto the current chart's candles and fill gaps with
// a constant interpolation (last known completed value), to avoid repainting
const myDev200dLanded = land_points_onto_series(myDailyData.time, myDev200dNativeChosen, time, 'le');
const myDev48mLanded = land_points_onto_series(myMonthlyData.time, myDev48mNativeChosen, time, 'le');
const myDev200d = interpolate_sparse_series(myDev200dLanded, 'constant');
const myDev48m = interpolate_sparse_series(myDev48mLanded, 'constant');

// ── Signal logic ────────────────────────────────────────────────────
const myCond1 = for_every(myDev200d, _d => _d !== null && _d <= myC1Thresh);
const myCond2 = for_every(myDev48m, _d => _d !== null && _d <= myC2Thresh);

const myCond1Prev = shift(myCond1, 1);
const myCond2Prev = shift(myCond2, 1);

const myCond1Trigger = for_every(myCond1, myCond1Prev, (_c, _p) => _c && !_p);
const myCond2Trigger = for_every(myCond2, myCond2Prev, (_c, _p) => _c && !_p);
const myBothActive = for_every(myCond1, myCond2, (_c1, _c2) => _c1 && _c2);

// ── Plots ───────────────────────────────────────────────────────────
paint(myDev200d, { name: 'Dev vs 200D SMA', color: '#00BCD4', thickness: 2 });
paint(myDev48m, { name: 'Dev vs 48M SMA', color: '#FF9800', thickness: 2 });

paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });
paint(horizontal_line(myC1Thresh), { name: 'C1 Threshold', color: '#00BCD4', style: 'dotted' });
paint(horizontal_line(myC2Thresh), { name: 'C2 Threshold', color: '#FF9800', style: 'dotted' });

// First-bar-of-signal markers (triangle up at bottom, approximated via labels_below)
const myC1Markers = for_every(myCond1Trigger, _t => _t ? myC1Thresh : null);
const myC2Markers = for_every(myCond2Trigger, _t => _t ? myC2Thresh : null);

paint(myC1Markers, { name: 'C1 Trigger', style: 'labels_below', color: '#00BCD4' });
paint(myC2Markers, { name: 'C2 Trigger', style: 'labels_below', color: '#FF9800' });

// Background regime shading approximated via candle coloring:
// red = both conditions, orange = C2 only, aqua = C1 only
const myRegimeColors = for_every(myCond1, myCond2, (_c1, _c2) => {
	if (_c1 && _c2) return 'rgba(255,0,0,0.35)';
	if (_c2) return 'rgba(255,152,0,0.25)';
	if (_c1) return 'rgba(0,188,212,0.2)';
	return null;
});
color_candles(myRegimeColors);

// ── Signals for scanner / alerts / strategy ─────────────────────────
register_signal(myCond1Trigger, 'Futia Condition 1');
register_signal(myCond2Trigger, 'Futia Condition 2');
register_signal(myBothActive, 'Futia C1 Plus C2');