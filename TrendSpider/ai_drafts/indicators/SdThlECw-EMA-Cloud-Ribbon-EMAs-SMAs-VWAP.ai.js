describe_indicator('EMA Cloud Ribbon + SMAs + VWAP', 'price');

// ───────────── EMA Ribbon inputs ─────────────
const emaTab = input.tab('EMA Ribbon');
const row1 = emaTab.row();
const myShowEma1 = row1.boolean('Show EMA 1', true);
const myLen1 = row1.number('Length 1', 9, { min: 1, max: 1000 });
const row2 = emaTab.row();
const myShowEma2 = row2.boolean('Show EMA 2', true);
const myLen2 = row2.number('Length 2', 15, { min: 1, max: 1000 });
const row3 = emaTab.row();
const myShowEma3 = row3.boolean('Show EMA 3', true);
const myLen3 = row3.number('Length 3', 30, { min: 1, max: 1000 });
const row4 = emaTab.row();
const myShowEma4 = row4.boolean('Show EMA 4', true);
const myLen4 = row4.number('Length 4', 65, { min: 1, max: 1000 });
const row5 = emaTab.row();
const myShowEma5 = row5.boolean('Show EMA 5', true);
const myLen5 = row5.number('Length 5', 200, { min: 1, max: 1000 });
const mySrcName = emaTab.select('Source', 'close', constants.price_source_options);
const mySrc = market[mySrcName];

// ───────────── Cloud fill inputs ─────────────
const cloudTab = input.tab('Cloud Fill');
const myShowCloud = cloudTab.boolean('Show cloud fills', true);

// ───────────── VWAP inputs ─────────────
const vwapTab = input.tab('VWAP');
const myShowVwap = vwapTab.boolean('Show VWAP', true);

// ───────────── SMA inputs ─────────────
const smaTab = input.tab('Moving Averages (SMA)');
const smaRow1 = smaTab.row();
const myShowSma1 = smaRow1.boolean('Show SMA 1', true);
const mySmaLen1 = smaRow1.number('Length 1', 20, { min: 1, max: 1000 });
const smaRow2 = smaTab.row();
const myShowSma2 = smaRow2.boolean('Show SMA 2', true);
const mySmaLen2 = smaRow2.number('Length 2', 50, { min: 1, max: 1000 });
const smaRow3 = smaTab.row();
const myShowSma3 = smaRow3.boolean('Show SMA 3', true);
const mySmaLen3 = smaRow3.number('Length 3', 100, { min: 1, max: 1000 });
const smaRow4 = smaTab.row();
const myShowSma4 = smaRow4.boolean('Show SMA 4', true);
const mySmaLen4 = smaRow4.number('Length 4', 200, { min: 1, max: 1000 });

// ═══════════════ EMA RIBBON ═══════════════
const myEma1 = ema(mySrc, myLen1);
const myEma2 = ema(mySrc, myLen2);
const myEma3 = ema(mySrc, myLen3);
const myEma4 = ema(mySrc, myLen4);
const myEma5 = ema(mySrc, myLen5);

const myEma1Line = paint(myShowEma1 ? myEma1 : constants.empty_series, { name: 'EMA1', color: '#2962ff', thickness: 1 });
const myEma2Line = paint(myShowEma2 ? myEma2 : constants.empty_series, { name: 'EMA2', color: '#26a69a', thickness: 1 });
const myEma3Line = paint(myShowEma3 ? myEma3 : constants.empty_series, { name: 'EMA3', color: '#ff9800', thickness: 1 });
paint(myShowEma4 ? myEma4 : constants.empty_series, { name: 'EMA4', color: '#787b86', thickness: 1 });
paint(myShowEma5 ? myEma5 : constants.empty_series, { name: 'EMA5', color: '#ef5350', thickness: 2 });

// Cloud fills between EMA1-EMA2 and EMA2-EMA3, colored by bullish/bearish relationship.
// `fill()` only accepts a single flat color (string), so it cannot be used here with
// a per-candle dynamic color array - that is what threw the "color must be a string" error.
// Switched to `color_cloud()`, which is built specifically to color the band between two
// series differently depending on which one is above the other at each candle.
const myCloudColorBull = '#2ca599';
const myCloudColorBear = '#ee5451';

if (myShowCloud) {
	color_cloud(myEma1, myEma2, myCloudColorBull, myCloudColorBear, 'Cloud12Bull', 'Cloud12Bear', 0.25);
	color_cloud(myEma2, myEma3, myCloudColorBull, myCloudColorBear, 'Cloud23Bull', 'Cloud23Bear', 0.2);
}

// ═══════════════ VWAP (session anchored) ═══════════════
// Built via cumulative price*volume and cumulative volume, resetting at each new session,
// since the built-in vwap() function does not auto-reset per session like Pine's ta.vwap.
const mySessionIds = time.map(_t => bar_at(_t).session);
const mySessionChanged = mySessionIds.map((_s, _i) => _i === 0 || _s !== mySessionIds[_i - 1]);
const myPV = mult(hlc3, volume);
const myCumPV = for_every(myPV, mySessionChanged, (_pv, _changed, _prev) => _changed ? _pv : _prev + _pv);
const myCumVol = for_every(volume, mySessionChanged, (_v, _changed, _prev) => _changed ? _v : _prev + _v);
const myVwapVal = div(myCumPV, myCumVol);

paint(myShowVwap ? myVwapVal : constants.empty_series, { name: 'VWAP', color: 'purple', thickness: 2 });

// ═══════════════ DAILY SMAs ═══════════════
const myDailyData = await request.history(current.ticker, 'D');
assert(!myDailyData.error, `Error fetching daily data: "${myDailyData.error}"`);

const mySma1Daily = sma(myDailyData.close, mySmaLen1);
const mySma2Daily = sma(myDailyData.close, mySmaLen2);
const mySma3Daily = sma(myDailyData.close, mySmaLen3);
const mySma4Daily = sma(myDailyData.close, mySmaLen4);

// Land daily values onto the current chart's candles and keep them constant until the next
// daily bar arrives (mirrors request.security with lookahead_off, no forward-looking data).
const mySma1 = interpolate_sparse_series(land_points_onto_series(myDailyData.time, mySma1Daily, time, 'ge'), 'constant');
const mySma2 = interpolate_sparse_series(land_points_onto_series(myDailyData.time, mySma2Daily, time, 'ge'), 'constant');
const mySma3 = interpolate_sparse_series(land_points_onto_series(myDailyData.time, mySma3Daily, time, 'ge'), 'constant');
const mySma4 = interpolate_sparse_series(land_points_onto_series(myDailyData.time, mySma4Daily, time, 'ge'), 'constant');

paint(myShowSma1 ? mySma1 : constants.empty_series, { name: 'SMA1', color: '#00bcd4', thickness: 1 });
paint(myShowSma2 ? mySma2 : constants.empty_series, { name: 'SMA2', color: '#ffc107', thickness: 1 });
paint(myShowSma3 ? mySma3 : constants.empty_series, { name: 'SMA3', color: '#4caf50', thickness: 1 });
paint(myShowSma4 ? mySma4 : constants.empty_series, { name: 'SMA4', color: '#f44336', thickness: 2 });

// ═══════════════ SIGNALS (for scanners/alerts/strategies) ═══════════════
const myBullishCross = for_every(myEma1, myEma5, (_e1, _e5, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e1 > _e5 && myEma1[_idx - 1] <= myEma5[_idx - 1];
});
const myBearishCross = for_every(myEma1, myEma5, (_e1, _e5, _prev, _idx) => {
	if (_idx === 0) return false;
	return _e1 < _e5 && myEma1[_idx - 1] >= myEma5[_idx - 1];
});

register_signal(myBullishCross, 'Bullish EMA1 crosses above EMA5');
register_signal(myBearishCross, 'Bearish EMA1 crosses below EMA5');