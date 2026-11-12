/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Futia Deviation Bands (200D SMA / 48M SMA)
 * Author       : BY_Tse
 * Source URL   : https://www.tradingview.com/script/j74sYp1V-Futia-Deviation-Bands
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Futia Deviation Bands_TV
 *
 * Deviations from the original: Reviewed AI draft; both modes use the previous completed D/M bar (no look-ahead), so
 *   the confirmed-bars input is dropped; background colouring not available; threshold
 *   lines not dashed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Futia Deviation Bands_TV', 'lower', { decimals: 1 });
const myC1Thresh = input.number('C1 % below 200D SMA', -10.0, { max: 0, min: -100 });
const myC2Thresh = input.number('C2 % below 48M SMA', -20.0, { max: 0, min: -100 });
const [myDaily, myMonthly] = await Promise.all([
	request.history(current.ticker, 'D'),
	request.history(current.ticker, 'M')
]);
assert(!myDaily.error, 'Error fetching Daily data: ' + myDaily.error);
assert(!myMonthly.error, 'Error fetching Monthly data: ' + myMonthly.error);
const myDev = (_data, _n) => {
	const myMa = sma(_data.close, _n);
	return _data.close.map((_c, _k) => myMa[_k] ? (_c / myMa[_k] - 1) * 100 : null);
};
// Pine's confirmed mode ([1] with lookahead_on) = previous COMPLETED higher-timeframe bar; the same
// one-bar lag is applied in both modes so history never sees a bar's final value at its open (L23).
const myLand = (_data, _vals) => interpolate_sparse_series(land_points_onto_series(_data.time, _vals.map((_v, _k) => _k ? _vals[_k - 1] : null), time, 'le'), 'constant');
const myDev200d = myLand(myDaily, myDev(myDaily, 200));
const myDev48m = myLand(myMonthly, myDev(myMonthly, 48));
const myCond1 = myDev200d.map(_d => _d !== null && _d <= myC1Thresh);
const myCond2 = myDev48m.map(_d => _d !== null && _d <= myC2Thresh);
const myTrig1 = myCond1.map((_c, _i) => _c && !(_i > 0 && myCond1[_i - 1]));
const myTrig2 = myCond2.map((_c, _i) => _c && !(_i > 0 && myCond2[_i - 1]));
paint(myDev200d, { name: 'Dev vs 200D SMA', color: '#00BCD4', thickness: 2 });
paint(myDev48m, { name: 'Dev vs 48M SMA', color: '#FF9800', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero', color: 'gray' });
paint(horizontal_line(myC1Thresh), { name: 'C1 Threshold', color: '#00BCD4' });
paint(horizontal_line(myC2Thresh), { name: 'C2 Threshold', color: '#FF9800' });
paint(myTrig1.map(_t => _t ? myC1Thresh : null), { name: 'C1 Trigger', style: 'dotted', marker: 'triangle', color: '#00BCD4' });
paint(myTrig2.map(_t => _t ? myC2Thresh : null), { name: 'C2 Trigger', style: 'dotted', marker: 'triangle', color: '#FF9800' });
register_signal(myTrig1, 'Futia Condition 1');
register_signal(myTrig2, 'Futia Condition 2');
register_signal(myCond1.map((_c, _i) => _c && myCond2[_i]), 'Futia C1 Plus C2');
