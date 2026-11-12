/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MA Cross + Relative Strength Screener
 * Author       : avdhesh_alstom
 * Source URL   : https://www.tradingview.com/script/s6tQyipL-MA-Cross-Relative-Strength-Screener
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MA Cross Plus RS Screener_TV
 *
 * Deviations from the original: NSE small-cap benchmark not available in TrendSpider: IWM/SPY/QQQ/DIA offered;
 *   Pine-exact flag/score logic; bgcolor, flag char and data-window plots not carried
 *   over; table via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MA Cross Plus RS Screener_TV', 'lower', { decimals: 2 });
// The Pine benchmark NSE:NIFTYSMLCAP250 is not available in TrendSpider: US index ETFs are offered (IWM = small caps).
const mySrcName = input.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myFastLen = input.number('Fast EMA Length', 10, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 40, { min: 1, max: 500 });
const myBench = input.select('RS Benchmark', 'IWM', ['IWM', 'SPY', 'QQQ', 'DIA']);
const myRsLength = input.number('RS Period', 123, { min: 1, max: 2000 });
const myRsThreshold = input.number('RS Threshold', 0, { min: -100, max: 100 });
const mySensitivity = input.number('Sensitivity', 8, { min: 0.1, max: 100 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myComp = await request.history(myBench, current.resolution);
assert(!myComp.error && myComp.close && myComp.close.length > 0, 'Could not fetch benchmark ' + myBench);
const myCompSrc = interpolate_sparse_series(land_points_onto_series(myComp.time, myComp.close, time, 'le'), 'constant');
const myFastMA = ema(mySrc, myFastLen);
const mySlowMA = ema(mySrc, mySlowLen);
const myRes = close.map((_c, _i) => {
	if (_i < myRsLength) return null;
	const myB0 = mySrc[_i - myRsLength], myC0 = myCompSrc[_i - myRsLength], myC1 = myCompSrc[_i];
	if (!myB0 || !myC0 || !myC1) return null;
	return mySrc[_i] / myB0 / (myC1 / myC0) - 1;
});
const myFlag = close.map((_c, _i) => {
	const myMa = myFastMA[_i] !== null && mySlowMA[_i] !== null && myFastMA[_i] > mySlowMA[_i];
	const myRs = myRes[_i] !== null && myRes[_i] > myRsThreshold;
	return (myMa && myRs) ? 3 : ((myMa !== myRs) ? 2 : 1);
});
const myScore = close.map((_c, _i) => {
	if (myFastMA[_i] === null || mySlowMA[_i] === null || mySlowMA[_i] === 0) return null;
	const myMaPct = (myFastMA[_i] - mySlowMA[_i]) / mySlowMA[_i] * 100;
	const myRsPct = myRes[_i] === null ? 0 : myRes[_i] * 100;
	const myExp = Math.exp(2 * ((myMaPct + myRsPct) / 2) / mySensitivity);
	return 100 * (myExp - 1) / (myExp + 1);
});
let mySince = 0;
const mySinceBear = myFlag.map(_f => { mySince = _f === 1 ? 0 : mySince + 1; return mySince; });
const myFlagColor = myFlag.map(_f => _f === 3 ? '#26A69A' : (_f === 2 ? '#FF9800' : '#EF5350'));
paint(myScore, { name: 'Composite Score', color: myFlagColor, thickness: 3 });
paint(horizontal_line(0), { name: 'Zero Line', color: 'gray' });
paint(horizontal_line(100), { name: 'Upper Bound', color: 'rgba(128,128,128,0.4)' });
paint(horizontal_line(-100), { name: 'Lower Bound', color: 'rgba(128,128,128,0.4)' });
const myLast = close.length - 1;
paint_overlay('RS Screener Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Flag', color: 'white', background_color: 'rgba(0,0,0,0.7)' }, { text: myFlag[myLast] === 3 ? 'BULLISH' : (myFlag[myLast] === 2 ? 'HOLD' : 'BEARISH'), color: myFlagColor[myLast], background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: 'Score', color: 'white', background_color: 'rgba(0,0,0,0.7)' }, { text: myScore[myLast] === null ? 'n/a' : myScore[myLast].toFixed(2), color: myFlagColor[myLast], background_color: 'rgba(0,0,0,0.7)' }] },
		{ cells: [{ text: 'Bars/Bearish', color: 'white', background_color: 'rgba(0,0,0,0.7)' }, { text: String(mySinceBear[myLast]), color: 'white', background_color: 'rgba(0,0,0,0.7)' }] }
	]
});
register_signal(myFlag.map(_f => _f === 3), 'Bullish Flag');
register_signal(myFlag.map(_f => _f === 2), 'Hold Flag');
register_signal(myFlag.map(_f => _f === 1), 'Bearish Flag');
