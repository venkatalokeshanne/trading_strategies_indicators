describe_indicator('EMA Distance MACD (50W / 200W)', 'lower');

// ───────────────────────────── Inputs ─────────────────────────────
const emaTab = input.tab('EMA Lengths');
const myEmaLenRow = emaTab.row();
const mySlowLen = myEmaLenRow.number('Slow EMA Length (weekly bars)', 200, { min: 10, max: 500 });
const myFastLen = myEmaLenRow.number('Fast EMA Length (weekly bars)', 50, { min: 5, max: 500 });
const myAvoidRepaint = emaTab.boolean('Avoid Repaint (lag 1 confirmed weekly bar)', true);

// ───────────────────────────── Weekly calc ─────────────────────────────
const myWeeklyData = await request.history(current.ticker, 'W');
assert(!myWeeklyData.error, `Error fetching weekly data: "${myWeeklyData.error}"`);

const myEmaSlow = ema(myWeeklyData.close, mySlowLen);
const myEmaFast = ema(myWeeklyData.close, myFastLen);

const myPctSlow = mult(div(sub(myWeeklyData.close, myEmaSlow), myEmaSlow), 100);
const myPctFast = mult(div(sub(myWeeklyData.close, myEmaFast), myEmaFast), 100);

// avoidRepaint = true means we use the previous (already confirmed) weekly
// value, which is a shift of 1 on the weekly series itself (not the chart).
const myOffset = myAvoidRepaint ? 1 : 0;
const myPctSlowOffset = shift(myPctSlow, myOffset);
const myPctFastOffset = shift(myPctFast, myOffset);

// Land weekly values onto the current chart's time series. "le" picks the
// most recent weekly point that is less-or-equal to the chart candle time,
// and "constant" interpolation keeps this non-repainting/backtestable.
const myLine1Landed = land_points_onto_series(myWeeklyData.time, myPctSlowOffset, time, 'le');
const myLine2Landed = land_points_onto_series(myWeeklyData.time, myPctFastOffset, time, 'le');

const myLine1 = interpolate_sparse_series(myLine1Landed, 'constant');
const myLine2 = interpolate_sparse_series(myLine2Landed, 'constant');

const myHist = sub(myLine1, myLine2);
const myHistPrev = shift(myHist, 1);

// Dynamic histogram color: strengthening vs weakening within same regime
const myHistColor = for_every(myHist, myHistPrev, (_hist, _prevHist) => {
	if (_hist === null || _prevHist === null) return null;
	if (_hist >= 0) {
		return _hist >= _prevHist ? '#26A69A' : 'rgba(38,166,154,0.4)';
	}
	else {
		return _hist <= _prevHist ? '#EF5350' : 'rgba(239,83,80,0.4)';
	}
});

// ───────────────────────────── Plots ─────────────────────────────
paint(myHist, { name: 'Histogram', style: 'column', color: myHistColor });
paint(myLine1, { name: 'Line1 200W Pct Distance', color: '#FF6D00', thickness: 2 });
paint(myLine2, { name: 'Line2 50W Pct Distance', color: '#2962FF', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero', color: 'gray', style: 'dotted' });

// ───────────────────────────── Signals ─────────────────────────────
const myBullishShift = for_every(myHist, myHistPrev, (_hist, _prevHist) => _hist !== null && _prevHist !== null && _hist >= 0 && _prevHist < 0);
const myBearishShift = for_every(myHist, myHistPrev, (_hist, _prevHist) => _hist !== null && _prevHist !== null && _hist <= 0 && _prevHist > 0);

register_signal(myBullishShift, 'Bullish Regime Shift');
register_signal(myBearishShift, 'Bearish Regime Shift');

// ───────────────────────────── Info overlay ─────────────────────────────
const myLastLine1 = myLine1.length ? myLine1[myLine1.length - 1] : null;
const myLastLine2 = myLine2.length ? myLine2[myLine2.length - 1] : null;
const myLastHist = myHist.length ? myHist[myHist.length - 1] : null;
const myRegimeText = myLastHist !== null && myLastHist >= 0 ? 'Short-term running HOT vs long-term' : 'Short-term running COLD vs long-term';
const myRegimeColor = myLastHist !== null && myLastHist >= 0 ? '#26A69A' : '#EF5350';

paint_overlay('EmaDistanceInfoTable', { position: 'top_right' }, {
	rows: [{
		cells: [{ text: current.ticker, color: 'white' }]
	}, {
		cells: [{ text: `200W: ${myLastLine1 !== null ? myLastLine1.toFixed(2) : 'n/a'}%`, color: '#FF6D00' }]
	}, {
		cells: [{ text: `50W: ${myLastLine2 !== null ? myLastLine2.toFixed(2) : 'n/a'}%`, color: '#2962FF' }]
	}, {
		cells: [{ text: myRegimeText, color: myRegimeColor }]
	}]
});