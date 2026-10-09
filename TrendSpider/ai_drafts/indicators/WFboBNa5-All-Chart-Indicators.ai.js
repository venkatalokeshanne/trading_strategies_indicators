describe_indicator('All Chart Indicators', 'lower');

// ============ INPUTS ============
const stTab = input.tab('Supertrend');
const st1Row = stTab.row();
const i_atrLen1 = st1Row.number('ST 1 ATR Length', 44, { min: 1, max: 500 });
const i_stFactor1 = st1Row.number('ST 1 Multiplier', 4.4, { min: 0.1, max: 20, step: 0.1 });
const st2Row = stTab.row();
const i_atrLen2 = st2Row.number('ST 2 ATR Length', 44, { min: 1, max: 500 });
const i_stFactor2 = st2Row.number('ST 2 Multiplier', 5.0, { min: 0.1, max: 20, step: 0.1 });

const rsiTab = input.tab('RSI');
const i_rsiLen = rsiTab.number('RSI Length', 14, { min: 1, max: 200 });

const pivotTab = input.tab('Pivots');
const i_pivotSrc = pivotTab.select('Pivot Timeframe', 'Daily', ['Daily', 'Weekly', 'Monthly']);

// map pivot timeframe to TrendSpider resolution
const myPivotResolution = i_pivotSrc === 'Daily' ? 'D' : (i_pivotSrc === 'Weekly' ? 'W' : 'M');

// ============ 1) SUPERTREND #1 ============
const myST1 = supertrend(i_atrLen1, i_stFactor1, false);
// Supertrend direction: close above the line means uptrend (green), below means downtrend (red)
const myST1Color = for_every(close, myST1, (_c, _s) => _c >= _s ? '#26A69A' : '#EF5350');

// ============ 2) SUPERTREND #2 ============
const myST2 = supertrend(i_atrLen2, i_stFactor2, false);
const myST2Color = for_every(close, myST2, (_c, _s) => _c >= _s ? '#4DA3FF' : '#FFA726');

// ============ 3) VOLUME ============
const myVolumeColor = for_every(close, open, (_c, _o) => _c >= _o ? '#26A69A99' : '#EF535099');

// ============ 4) VWAP ============
const myVwap = vwap();

// ============ 5) RSI ============
const myRsi = rsi(close, i_rsiLen);

// ============ 6) PIVOT POINTS STANDARD (Classic) ============
const myPivotData = await request.history(current.ticker, myPivotResolution);
assert(!myPivotData.error, 'Error fetching pivot timeframe data: ' + myPivotData.error);

const myPivotHigh = pivot_high(myPivotData.high, 2, 2);
const myPivotLow = pivot_low(myPivotData.low, 2, 2);

const myPP = series_of(null);
const myR1 = series_of(null);
const myR2 = series_of(null);
const myR3 = series_of(null);
const myS1 = series_of(null);
const myS2 = series_of(null);
const myS3 = series_of(null);

// Pivot levels are only computed on bars where both a pivot high AND
// a pivot low confirm (mirrors "if not na(pivotHigh) and not na(pivotLow)")
for (let myIndex = 1; myIndex < myPivotData.time.length; myIndex += 1) {
	if (myPivotHigh[myIndex] !== null && myPivotLow[myIndex] !== null) {
		const myPrevClose = myPivotData.close[myIndex - 1];
		const myPrevHigh = myPivotData.high[myIndex - 1];
		const myPrevLow = myPivotData.low[myIndex - 1];

		const myPivotPoint = (myPrevHigh + myPrevLow + myPrevClose) / 3;
		myPP[myIndex] = myPivotPoint;
		myR1[myIndex] = 2 * myPivotPoint - myPrevLow;
		myS1[myIndex] = 2 * myPivotPoint - myPrevHigh;
		myR2[myIndex] = myPivotPoint + (myPrevHigh - myPrevLow);
		myS2[myIndex] = myPivotPoint - (myPrevHigh - myPrevLow);
		myR3[myIndex] = myPrevHigh + 2 * (myPivotPoint - myPrevLow);
		myS3[myIndex] = myPrevLow - 2 * (myPrevHigh - myPivotPoint);
	}
}

// land these sparse pivot timeframe values onto the chart's timeframe
// and hold the last known value (constant interpolation keeps it
// backtestable, same behavior as Pine's "var" persistence)
const myPPLanded = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myPP, time, 'le'), 'constant');
const myR1Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myR1, time, 'le'), 'constant');
const myR2Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myR2, time, 'le'), 'constant');
const myR3Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myR3, time, 'le'), 'constant');
const myS1Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myS1, time, 'le'), 'constant');
const myS2Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myS2, time, 'le'), 'constant');
const myS3Landed = interpolate_sparse_series(land_points_onto_series(myPivotData.time, myS3, time, 'le'), 'constant');

// ============ PAINT ============
paint(myST1, { name: 'ST1', color: myST1Color, thickness: 2, forceUsePriceAxis: true });
paint(myST2, { name: 'ST2', color: myST2Color, thickness: 2, forceUsePriceAxis: true });
paint(volume, { name: 'Volume', color: myVolumeColor, style: 'column' });
paint(myVwap, { name: 'VWAP', color: '#2962FF', thickness: 2, forceUsePriceAxis: true });

paint(myRsi, { name: 'RSI', color: '#8E24AA', thickness: 2 });
paint(horizontal_line(70), { name: 'Overbought', color: '#EF535080', style: 'dotted' });
paint(horizontal_line(30), { name: 'Oversold', color: '#26A69A80', style: 'dotted' });
paint(horizontal_line(50), { name: 'Mid', color: '#9E9E9E80', style: 'dotted' });

paint(myPPLanded, { name: 'PP', color: '#9E9E9E', thickness: 1, style: 'dotted', forceUsePriceAxis: true });
paint(myR1Landed, { name: 'R1', color: '#EF5350', thickness: 1, forceUsePriceAxis: true });
paint(myS1Landed, { name: 'S1', color: '#26A69A', thickness: 1, forceUsePriceAxis: true });
paint(myR2Landed, { name: 'R2', color: '#EF535099', thickness: 1, forceUsePriceAxis: true });
paint(myS2Landed, { name: 'S2', color: '#26A69A99', thickness: 1, forceUsePriceAxis: true });
paint(myR3Landed, { name: 'R3', color: '#EF535066', thickness: 1, forceUsePriceAxis: true });
paint(myS3Landed, { name: 'S3', color: '#26A69A66', thickness: 1, forceUsePriceAxis: true });

// ============ SIGNALS (for scanners/alerts/strategies) ============
const myRsiBullishCross = for_every(myRsi, (_r, _prev, _i) => _i > 0 && _r > 30 && myRsi[_i - 1] <= 30);
const myRsiBearishCross = for_every(myRsi, (_r, _prev, _i) => _i > 0 && _r < 70 && myRsi[_i - 1] >= 70);

register_signal(myRsiBullishCross, 'RSI Bullish Cross 30');
register_signal(myRsiBearishCross, 'RSI Bearish Cross 70');
register_signal(for_every(close, myST1, (_c, _s) => _c >= _s), 'Supertrend 1 Uptrend');
register_signal(for_every(close, myST2, (_c, _s) => _c >= _s), 'Supertrend 2 Uptrend');