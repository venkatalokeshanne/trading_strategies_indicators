/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : The Island MTF 
 * Author       : SergioAdams85
 * Source URL   : https://www.tradingview.com/script/a9BmX6CA-The-Island-4H-MTF
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : The Island 4H MTF_TV
 *
 * Deviations from the original: Signal placed on the first chart bar of the new HTF bar (Pine offset=-1 not
 *   possible); triangle size input dropped; HTF chosen from a list
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('The Island 4H MTF_TV', 'price');
const myHtfRes = input.select('Higher Timeframe', '240', ['60', '120', '240', 'D', 'W']);
const myHtf = await request.history(current.ticker, myHtfRes);
assert(!myHtf.error, 'Error fetching higher timeframe data: ' + myHtf.error);
// Pine: curr = previous completed HTF bar, prev = the one before; the signal fires on the first chart bar of a new HTF bar
// (the Pine plots it one bar earlier with offset=-1; here it is placed on the first bar of the new HTF bar, no look-ahead)
const myBull = myHtf.close.map((_c, _k) => {
	if (_k < 2) return null;
	const myCurrLow = myHtf.low[_k - 1], myCurrClose = myHtf.close[_k - 1], myPrevLow = myHtf.low[_k - 2], myPrevHigh = myHtf.high[_k - 2];
	return (myCurrLow < myPrevLow && myCurrClose > myPrevHigh) ? 1 : null;
});
const myBear = myHtf.close.map((_c, _k) => {
	if (_k < 2) return null;
	const myCurrHigh = myHtf.high[_k - 1], myCurrClose = myHtf.close[_k - 1], myPrevLow = myHtf.low[_k - 2], myPrevHigh = myHtf.high[_k - 2];
	return (myCurrHigh > myPrevHigh && myCurrClose < myPrevLow) ? 1 : null;
});
const myBuy = land_points_onto_series(myHtf.time, myBull, time, 'ge').map(_v => _v === 1);
const mySell = land_points_onto_series(myHtf.time, myBear, time, 'ge').map(_v => _v === 1);
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
register_signal(myBuy, 'Buy Signal (Bullish Outside Bar)');
register_signal(mySell, 'Sell Signal (Bearish Outside Bar)');
