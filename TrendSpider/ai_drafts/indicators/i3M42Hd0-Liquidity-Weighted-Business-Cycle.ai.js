describe_indicator('Liquidity Weighted Business Cycle Approx', 'lower');

// NOTE: this indicator approximates "TechDev style" Liquidity-Weighted
// Business Cycle from a Pine Script. TrendSpider Custom JS API does not
// have access to TradingView's ECONOMICS:USM2/CNM2/EUM2/JPM2/GBM2 series,
// nor to FX pairs or futures symbols the exact way Pine does. This is a
// best-effort reconstruction, not an exact 1:1 port. See flagged warnings.

const myTab = input.tab('Settings');

const myRow1 = myTab.row();
const myRsiLength = myRow1.number('RSI Length Copper Gold', 14, { min: 5, max: 50 });
const mySmaLength = myRow1.number('Liquidity SMA Length', 60, { min: 20, max: 500 });

const myRow2 = myTab.row();
const myUseRelativeL = myRow2.boolean('Use Relative Liquidity', true);
const myShowZeroLine = myRow2.boolean('Show Zero Line', true);

const myScaleFactor = myTab.number('Scale Factor', 0.0001, { min: 0.000001, max: 1, step: 0.00001 });

// ─────────────────────────────────────────────────────────────
// 1. Approximate Global Liquidity using US M2 (FRED) only.
//    CN/EU/JP/GB M2 and FX conversion from the Pine script are
//    not available as data sources in this API, so "global_m2"
//    here is really just US M2. This changes absolute scale and
//    some dynamics versus the original Pine script.
//
//    request.fred_series() can throw / reject the promise (not
//    just return an { error } object) when the series label does
//    not match the platform's own FRED catalog exactly. Since we
//    cannot enumerate that catalog from code, and we previously
//    hit a "no_data" failure, we now wrap the call in try/catch
//    so a bad or unavailable label never crashes the whole
//    indicator; we fall back to a neutral liquidity factor of 1.
// ─────────────────────────────────────────────────────────────
let myM2Data = null;
let myM2FetchFailed = false;

try {
	myM2Data = await request.fred_series('M2 Money Stock, M2SL mo');
	myM2FetchFailed = !myM2Data || !!myM2Data.error || !myM2Data.series || myM2Data.series.length === 0;
}
catch (myM2Error) {
	myM2FetchFailed = true;
}

let myGlobalM2 = series_of(1);

if (!myM2FetchFailed) {
	const myM2Timestamps = myM2Data.series.map(_point => _point[0]);
	const myM2Values = myM2Data.series.map(_point => _point[1]);
	const myM2Landed = land_points_onto_series(myM2Timestamps, myM2Values, time, 'le');
	myGlobalM2 = interpolate_sparse_series(myM2Landed, 'constant');
}

// ─────────────────────────────────────────────────────────────
// 2. Liquidity factor
// ─────────────────────────────────────────────────────────────
const myLiquidityRelative = div(myGlobalM2, sma(myGlobalM2, mySmaLength));
const myLiquidity = myUseRelativeL ? myLiquidityRelative : myGlobalM2;

// ─────────────────────────────────────────────────────────────
// 3. Copper / Gold RSI
//    Using continuous futures symbols; actual symbol coverage
//    depends on the data vendor behind request.history(). Also
//    wrapped defensively, falling back to a neutral RSI of 50
//    (no bias) rather than crashing the indicator.
// ─────────────────────────────────────────────────────────────
let myCopperData = { error: true };
let myGoldData = { error: true };

try {
	[myCopperData, myGoldData] = await Promise.all([
		request.history('HG1!', current.resolution),
		request.history('GC1!', current.resolution)
	]);
}
catch (myCommodityError) {
	myCopperData = { error: true };
	myGoldData = { error: true };
}

const myCommodityFetchFailed = !myCopperData || !!myCopperData.error || !myGoldData || !!myGoldData.error;
let myRsiCuAu = series_of(50);

if (!myCommodityFetchFailed) {
	const myCopperLanded = interpolate_sparse_series(land_points_onto_series(myCopperData.time, myCopperData.close, time, 'le'), 'constant');
	const myGoldLanded = interpolate_sparse_series(land_points_onto_series(myGoldData.time, myGoldData.close, time, 'le'), 'constant');
	const myCuAuRatio = div(myCopperLanded, myGoldLanded);
	myRsiCuAu = rsi(myCuAuRatio, myRsiLength);
}

// ─────────────────────────────────────────────────────────────
// 4. Final Business Cycle value
// ─────────────────────────────────────────────────────────────
const myBcRaw = mult(myLiquidity, sub(myRsiCuAu, 50));
const myBc = mult(myBcRaw, myScaleFactor);

const myHistColor = for_every(myBc, _bcValue => _bcValue >= 0 ? 'red' : 'teal');

paint(myBc, { name: 'Business Cycle', style: 'column', color: myHistColor, thickness: 4 });
paint(myBc, { name: 'BC Line', color: 'white', thickness: 1 });

const myZeroLine = myShowZeroLine ? horizontal_line(0) : series_of(null);
paint(myZeroLine, { name: 'Zero Line', color: 'gray', style: 'dotted' });

register_signal(for_every(myBc, _bcValue => _bcValue > 0), 'Business Cycle Positive');
register_signal(for_every(myBc, _bcValue => _bcValue < 0), 'Business Cycle Negative');