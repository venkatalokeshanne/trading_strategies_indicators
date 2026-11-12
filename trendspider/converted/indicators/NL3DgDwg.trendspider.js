/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Whale Absorption & Liquidity Zones
 * Author       : trunkxpert
 * Source URL   : https://www.tradingview.com/script/NL3DgDwg
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Whale Absorption Liquidity Zones_TV
 *
 * Deviations from the original: Reviewed AI draft; pivots hand-rolled and confirmed 5 bars late; liquidity lines are
 *   step lines of the latest pivot (Pine draws a line per pivot); labels on the last 15
 *   pivots; WHALE BUY/SELL text as icons.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Whale Absorption Liquidity Zones_TV', 'price');
const myVolMaLength = input.number('Volume MA Length', 20, { min: 1, max: 500 });
const myVolMultiplier = input.number('Whale Volume Mult', 1.5, { min: 0.1, max: 10, step: 0.1 });
const myLookback = input.number('Pivot Lookback', 20, { min: 5, max: 200 });
const myRight = 5;
const myAvgVol = sma(volume, myVolMaLength);
const myHighVol = close.map((_c, _i) => myAvgVol[_i] !== null && volume[_i] > myAvgVol[_i] * myVolMultiplier);
const myBuyAbs = close.map((_c, _i) => myHighVol[_i] && _c > low[_i] + (high[_i] - low[_i]) * 0.6 && _c > open[_i]);
const mySellAbs = close.map((_c, _i) => myHighVol[_i] && _c < low[_i] + (high[_i] - low[_i]) * 0.4 && _c < open[_i]);
color_candles(close.map((_c, _i) => myBuyAbs[_i] ? '#00ff08' : (mySellAbs[_i] ? '#ff0055' : null)));
paint(myBuyAbs.map(_b => _b ? constants.icons.triangle_up : null), { name: 'Whale Buy', style: 'labels_below', color: 'green' });
paint(mySellAbs.map(_s => _s ? constants.icons.triangle_down : null), { name: 'Whale Sell', style: 'labels_above', color: 'red' });
// ta.pivothigh/pivotlow(left=lookback, right=5): reported on the confirmation bar, 5 bars after the pivot
const myPivot = (_src, _isHigh) => _src.map((_v, _i) => {
	const myP = _i - myRight;
	if (myP - myLookback < 0) return null;
	for (let myK = myP - myLookback; myK <= _i; myK += 1) {
		if (myK === myP) continue;
		if (_isHigh ? (myK < myP ? !(_src[myP] > _src[myK]) : !(_src[myP] >= _src[myK])) : (myK < myP ? !(_src[myP] < _src[myK]) : !(_src[myP] <= _src[myK]))) return null;
	}
	return _src[myP];
});
const myPh = myPivot(high, true);
const myPl = myPivot(low, false);
const mySellZone = interpolate_sparse_series(myPh, 'constant');
const myBuyZone = interpolate_sparse_series(myPl, 'constant');
const mySellPainted = paint(mySellZone, { name: 'Liquidity Sell Stops', color: 'red', thickness: 1 });
const myBuyPainted = paint(myBuyZone, { name: 'Liquidity Buy Stops', color: 'green', thickness: 1 });
const myPhIdx = [];
const myPlIdx = [];
myPh.forEach((_v, _i) => { if (_v !== null) myPhIdx.push(_i); });
myPl.forEach((_v, _i) => { if (_v !== null) myPlIdx.push(_i); });
myPhIdx.slice(-15).forEach(_i => paint_label_at_line(mySellPainted, _i, 'LIQUIDEZ SELL STOPS', { color: 'red' }));
myPlIdx.slice(-15).forEach(_i => paint_label_at_line(myBuyPainted, _i, 'LIQUIDEZ BUY STOPS', { color: 'green' }));
const myLast = close.length - 1;
const myWhale = myBuyAbs[myLast] || mySellAbs[myLast];
paint_overlay('Whale Dashboard', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'Volume Status:', color: 'white', background_color: '#222222' }, { text: myHighVol[myLast] ? 'HIGH' : 'NORMAL', color: 'white', background_color: myHighVol[myLast] ? 'red' : 'green' }] },
		{ cells: [{ text: 'Whale Presence:', color: 'white', background_color: '#222222' }, { text: myWhale ? 'DETECTED' : 'NONE', color: 'white', background_color: myWhale ? 'orange' : 'gray' }] }
	]
});
register_signal(myBuyAbs, 'Whale Buy Absorption');
register_signal(mySellAbs, 'Whale Sell Absorption');
register_signal(myHighVol, 'High Volume');
