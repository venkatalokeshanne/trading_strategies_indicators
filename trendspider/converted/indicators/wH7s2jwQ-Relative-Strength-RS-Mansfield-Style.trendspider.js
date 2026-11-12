/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Relative Strength (RS)
 * Author       : r87_84
 * Source URL   : https://www.tradingview.com/script/wH7s2jwQ-Relative-Strength-RS-Mansfield-Style
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Relative Strength RS_TV
 *
 * Deviations from the original: SP:SPX is not available in TrendSpider: SPY/QQQ/IWM/DIA offered; timeframe input
 *   dropped; thresholds not dotted.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Relative Strength RS_TV', 'lower');
// The Pine default benchmark SP:SPX is not available in TrendSpider, so US index ETFs are offered.
const myBench = input.select('Comparative Symbol', 'SPY', ['SPY', 'QQQ', 'IWM', 'DIA']);
const myPeriod = input.number('Period', 50, { min: 1, max: 2000 });
const myShowMa = input.boolean('Show Moving Average', false);
const myMaPeriod = input.number('MA Period', 10, { min: 1, max: 2000 });
const myUpper = input.number('Upper Threshold', 10.0, { min: -1000, max: 1000, step: 1.0 });
const myLower = input.number('Lower Threshold', -10.0, { min: -1000, max: 1000, step: 1.0 });
const myShowThresh = input.boolean('Show Threshold Lines', true);
const myData = await request.history(myBench, current.resolution);
assert(!myData.error && myData.close && myData.close.length > 0, 'Could not fetch comparative symbol ' + myBench);
const myBenchClose = interpolate_sparse_series(land_points_onto_series(myData.time, myData.close, time, 'le'), 'constant');
const myRatio = close.map((_c, _i) => (myBenchClose[_i] === null || myBenchClose[_i] === 0) ? null : _c / myBenchClose[_i]);
const mySmaOf = (_s, _n) => _s.map((_v, _i) => {
	if (_i < _n - 1) return null;
	let mySum = 0;
	for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; mySum += _s[myK]; }
	return mySum / _n;
});
const myBase = mySmaOf(myRatio, myPeriod);
const myRs = myRatio.map((_r, _i) => (_r === null || myBase[_i] === null || myBase[_i] === 0) ? null : (_r / myBase[_i] - 1) * 100);
const mySignal = mySmaOf(myRs, myMaPeriod);
paint(myRs, { name: 'RS', color: 'blue', thickness: 2 });
paint(mySignal.map(_v => myShowMa ? _v : null), { name: 'Signal MA', color: 'gray', thickness: 1 });
paint(horizontal_line(0), { name: 'Zero', color: 'gray' });
paint(myShowThresh ? horizontal_line(myUpper) : close.map(() => null), { name: 'Upper Threshold', color: 'rgba(0,160,0,0.6)' });
paint(myShowThresh ? horizontal_line(myLower) : close.map(() => null), { name: 'Lower Threshold', color: 'rgba(220,0,0,0.6)' });
const myPrev = shift(myRs, 1);
const myCross = (_lvl, _up) => for_every(myRs, myPrev, (_r, _p) => _r !== null && _p !== null && (_up ? (_p <= _lvl && _r > _lvl) : (_p >= _lvl && _r < _lvl)));
register_signal(myCross(0, true), 'RS Crossed Above Zero');
register_signal(myCross(0, false), 'RS Crossed Below Zero');
register_signal(myCross(myUpper, true), 'RS Crossed Above Upper');
register_signal(myCross(myLower, false), 'RS Crossed Below Lower');
