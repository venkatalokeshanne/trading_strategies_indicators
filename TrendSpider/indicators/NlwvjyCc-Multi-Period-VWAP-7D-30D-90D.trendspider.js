/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Rolling Multi-Day VWAP
 * Author       : DarthTraderCrypto
 * Source URL   : https://www.tradingview.com/script/NlwvjyCc-Multi-Period-VWAP-7D-30D-90D
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Rolling Multi-Day VWAP_TV
 *
 * Deviations from the original: ta.vwma on 30-minute bars landed one completed 30m bar later (no look-ahead); labels
 *   only on the last bar
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Rolling Multi-Day VWAP_TV', 'price');
const myLen7 = input.number('Short-Term Days', 7, { min: 1, max: 200 });
const myLen30 = input.number('Medium-Term Days', 30, { min: 1, max: 400 });
const myLen90 = input.number('Long-Term Days', 90, { min: 1, max: 800 });
const myShow7 = input.boolean('Show Short-Term', true);
const myShow30 = input.boolean('Show Medium-Term', true);
const myShow90 = input.boolean('Show Long-Term', true);
const mySrcType = input.select('Price Source', 'hlc3', ['hlc3', 'close', 'ohlc4']);
// the Pine runs ta.vwma(src, days * 48) on 30-minute bars
const myD = await request.history(current.ticker, '30');
assert(!myD.error, 'Error fetching 30m data: ' + myD.error);
const mySrc = myD.close.map((_c, _i) => mySrcType === 'close' ? _c : (mySrcType === 'ohlc4' ? (myD.open[_i] + myD.high[_i] + myD.low[_i] + _c) / 4 : (myD.high[_i] + myD.low[_i] + _c) / 3));
const myPv = [0], myV = [0];
mySrc.forEach((_s, _i) => { myPv.push(myPv[_i] + _s * myD.volume[_i]); myV.push(myV[_i] + myD.volume[_i]); });
const myVwma = (_n) => {
	const myA = mySrc.map((_s, _i) => (_i < _n - 1 || myV[_i + 1] - myV[_i + 1 - _n] <= 0) ? null : (myPv[_i + 1] - myPv[_i + 1 - _n]) / (myV[_i + 1] - myV[_i + 1 - _n]));
	// value of the last completed 30m bar, shown from the open of the next one
	return interpolate_sparse_series(land_points_onto_series(myD.time, myA.map((_v, _k) => _k ? myA[_k - 1] : null), time, 'ge'), 'constant');
};
const myV7 = myVwma(myLen7 * 48), myV30 = myVwma(myLen30 * 48), myV90 = myVwma(myLen90 * 48);
const myGate = (_s, _f) => _f ? _s : _s.map(() => null);
const myP7 = paint(myGate(myV7, myShow7), { name: '7D VWAP', color: 'yellow', thickness: 2 });
const myP30 = paint(myGate(myV30, myShow30), { name: '30D VWAP', color: 'orange', thickness: 2 });
const myP90 = paint(myGate(myV90, myShow90), { name: '90D VWAP', color: 'red', thickness: 2 });
const myLast = close.length - 1;
if (myShow7 && myV7[myLast] !== null) paint_label_at_line(myP7, myLast, myLen7 + 'D VWAP: ' + myV7[myLast].toFixed(2), { color: 'yellow' });
if (myShow30 && myV30[myLast] !== null) paint_label_at_line(myP30, myLast, myLen30 + 'D VWAP: ' + myV30[myLast].toFixed(2), { color: 'orange' });
if (myShow90 && myV90[myLast] !== null) paint_label_at_line(myP90, myLast, myLen90 + 'D VWAP: ' + myV90[myLast].toFixed(2), { color: 'red' });
register_signal(close.map((_c, _i) => myV7[_i] !== null && _c > myV7[_i]), 'Close Above Short VWAP');
register_signal(close.map((_c, _i) => myV30[_i] !== null && _c > myV30[_i]), 'Close Above Medium VWAP');
register_signal(close.map((_c, _i) => myV90[_i] !== null && _c > myV90[_i]), 'Close Above Long VWAP');
