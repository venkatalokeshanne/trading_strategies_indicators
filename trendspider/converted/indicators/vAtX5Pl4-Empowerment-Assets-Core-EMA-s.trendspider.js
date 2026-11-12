/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Empowerment Assets Core v1
 * Author       : MoneyDailysniper
 * Source URL   : https://www.tradingview.com/script/vAtX5Pl4-Empowerment-Assets-Core-EMA-s
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Empowerment Assets Core v1_TV
 *
 * Deviations from the original: Reviewed AI draft; VWAP resets per calendar day; bgcolor replaced by high-low bands;
 *   dashboard via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Empowerment Assets Core v1_TV', 'price');
const myShowEma = input.boolean('Show EMAs', true);
const myShowVwap = input.boolean('Show VWAP', true);
const myShowLabels = input.boolean('Show EMA Labels', true);
const myEma5 = ema(close, 5);
const myEma10 = ema(close, 10);
const myEma20 = ema(close, 20);
const myEma50 = ema(close, 50);
const myEma90 = ema(close, 90);
// ta.vwap(close): resets every session (here: calendar day, exchange time)
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
let mySV = 0, myV = 0;
const myVwap = close.map((_c, _i) => {
	if (_i === 0 || myDayKey[_i] !== myDayKey[_i - 1]) { mySV = 0; myV = 0; }
	mySV += _c * volume[_i]; myV += volume[_i];
	return myV > 0 ? mySV / myV : null;
});
const myGate = (_s, _show) => _s.map(_v => _show ? _v : null);
const myP5 = paint(myGate(myEma5, myShowEma), { name: 'EMA 5', color: 'lime', thickness: 2 });
const myP10 = paint(myGate(myEma10, myShowEma), { name: 'EMA 10', color: 'aqua', thickness: 2 });
const myP20 = paint(myGate(myEma20, myShowEma), { name: 'EMA 20', color: 'yellow', thickness: 2 });
const myP50 = paint(myGate(myEma50, myShowEma), { name: 'EMA 50', color: 'orange', thickness: 2 });
const myP90 = paint(myGate(myEma90, myShowEma), { name: 'EMA 90', color: 'red', thickness: 2 });
const myPV = paint(myGate(myVwap, myShowVwap), { name: 'VWAP', color: 'fuchsia', thickness: 2 });
const myLast = close.length - 1;
if (myShowLabels) {
	paint_label_at_line(myP5, myLast, 'EMA 5', { color: 'lime' });
	paint_label_at_line(myP10, myLast, 'EMA 10', { color: 'aqua' });
	paint_label_at_line(myP20, myLast, 'EMA 20', { color: 'yellow' });
	paint_label_at_line(myP50, myLast, 'EMA 50', { color: 'orange' });
	paint_label_at_line(myP90, myLast, 'EMA 90', { color: 'red' });
	paint_label_at_line(myPV, myLast, 'VWAP', { color: 'purple' });
}
const myNn = (_a) => _a !== null && _a !== undefined;
const myBull = close.map((_c, _i) => [myEma5[_i], myEma10[_i], myEma20[_i], myEma50[_i], myEma90[_i], myVwap[_i]].every(myNn) && _c > myEma5[_i] && myEma5[_i] > myEma10[_i] && myEma10[_i] > myEma20[_i] && myEma20[_i] > myEma50[_i] && myEma50[_i] > myEma90[_i] && _c > myVwap[_i]);
const myBear = close.map((_c, _i) => [myEma5[_i], myEma10[_i], myEma20[_i], myEma50[_i], myEma90[_i], myVwap[_i]].every(myNn) && _c < myEma5[_i] && myEma5[_i] < myEma10[_i] && myEma10[_i] < myEma20[_i] && myEma20[_i] < myEma50[_i] && myEma50[_i] < myEma90[_i] && _c < myVwap[_i]);
// bgcolor is not available: bull/bear shading as a band over each bar's high-low range
color_cloud(high.map((_v, _i) => myBull[_i] ? _v : null), low.map((_v, _i) => myBull[_i] ? _v : null), 'rgba(0,160,0,0.3)', 'rgba(0,160,0,0.3)', 'Bull Up', 'Bull Dn');
color_cloud(high.map((_v, _i) => myBear[_i] ? _v : null), low.map((_v, _i) => myBear[_i] ? _v : null), 'rgba(220,0,0,0.3)', 'rgba(220,0,0,0.3)', 'Bear Up', 'Bear Dn');
const myFmt = (_v) => myNn(_v) ? _v.toFixed(4) : 'n/a';
const myRow = (_a, _b) => ({ cells: [{ text: _a, color: 'white', background_color: '#222222' }, { text: _b, color: 'white', background_color: '#222222' }] });
paint_overlay('Empowerment Dashboard', { position: 'top_right' }, {
	rows: [
		myRow('EMPOWERMENT', 'ASSETS'),
		myRow('Trend', myBull[myLast] ? 'BULLISH' : (myBear[myLast] ? 'BEARISH' : 'NEUTRAL')),
		myRow('Price', myFmt(close[myLast])),
		myRow('EMA 5', myFmt(myEma5[myLast])),
		myRow('EMA 10', myFmt(myEma10[myLast])),
		myRow('EMA 20', myFmt(myEma20[myLast])),
		myRow('VWAP', (myNn(myVwap[myLast]) && close[myLast] > myVwap[myLast]) ? 'ABOVE' : 'BELOW')
	]
});
register_signal(myBull, 'Bull Trend');
register_signal(myBear, 'Bear Trend');
