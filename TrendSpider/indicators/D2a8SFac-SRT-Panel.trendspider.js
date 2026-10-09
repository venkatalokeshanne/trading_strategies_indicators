/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : SRT Panel
 * Author       : siddace
 * Source URL   : https://www.tradingview.com/script/D2a8SFac-SRT-Panel
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : SRT Panel_TV
 *
 * Deviations from the original: Reviewed AI draft; panel via paint_overlay shows last-bar values; India VIX shows
 *   N/A if INDIAVIX is not in TrendSpider; colour/position inputs dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('SRT Panel_TV', 'price');
const mySma = sma(close, 124);
const mySrt = div(close, mySma);
// India VIX daily close; shows N/A when the symbol is not available in TrendSpider
let myVix = null;
try {
	const myVixData = await request.history('INDIAVIX', 'D');
	if (myVixData && !myVixData.error && myVixData.close.length) myVix = myVixData.close[myVixData.close.length - 1];
} catch (myError) {
	myVix = null;
}
const myLast = (_s) => _s[_s.length - 1];
const myFormat = (_v) => (_v === null || _v === undefined || isNaN(_v)) ? 'N/A' : _v.toFixed(2);
const myRow = (_label, _value) => ({ cells: [
	{ text: _label, color: 'white', background_color: '#00d47c' },
	{ text: _value, color: 'black', background_color: 'white' }
] });
paint_overlay('SRT Panel', { position: 'top_right' }, {
	rows: [
		myRow('Current Level', myFormat(myLast(close))),
		myRow('SMA 124', myFormat(myLast(mySma))),
		myRow('SRT Value', myFormat(myLast(mySrt))),
		myRow('India VIX', myFormat(myVix))
	]
});
register_signal(for_every(mySrt, _s => _s !== null && _s > 1), 'SRT Above One');
register_signal(for_every(mySrt, _s => _s !== null && _s < 1), 'SRT Below One');
