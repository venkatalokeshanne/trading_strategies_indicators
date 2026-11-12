/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kloom VWAP Bands
 * Author       : Kloom
 * Source URL   : https://www.tradingview.com/script/X8PbMqYA-Kloom-VWAP-Bands-Anchored-VWAP-with-St-Dev-Bands
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kloom VWAP Bands_TV
 *
 * Deviations from the original: Reviewed AI draft; anchors by exchange-time day/week/month; fills as clouds;
 *   deviation table via paint_overlay.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kloom VWAP Bands_TV', 'price');
const myAnchor = input.select('Anchor period', 'Session', ['Session', 'Week', 'Month']);
const mySrcName = input.select('Source', 'hlc3', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myShow1 = input.boolean('Show band 1', true);
const myMult1 = input.number('Band 1 mult', 1.0, { min: 0.1, max: 5, step: 0.25 });
const myShow2 = input.boolean('Show band 2', true);
const myMult2 = input.number('Band 2 mult', 2.0, { min: 0.1, max: 5, step: 0.25 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
// anchor key per bar (exchange time): day, Monday-aligned week, or month
const myKey = time.map(_t => {
	const myX = time_of(_t);
	if (myAnchor === 'Week') return Math.floor((Math.floor(_t / 86400) - 4) / 7);
	if (myAnchor === 'Month') return myX.month;
	return myX.month * 100 + myX.dayOfMonth;
});
const myVwap = series_of(null);
const myDev = series_of(null);
let mySumPV = 0, mySumV = 0, mySumPV2 = 0;
for (let myI = 0; myI < close.length; myI += 1) {
	if (myI === 0 || myKey[myI] !== myKey[myI - 1]) { mySumPV = 0; mySumV = 0; mySumPV2 = 0; }
	const myVol = volume[myI] || 0;
	mySumPV += mySrc[myI] * myVol; mySumV += myVol; mySumPV2 += mySrc[myI] * mySrc[myI] * myVol;
	if (mySumV > 0) {
		const myV = mySumPV / mySumV;
		myVwap[myI] = myV;
		myDev[myI] = Math.sqrt(Math.max(mySumPV2 / mySumV - myV * myV, 0));
	}
}
const myBand = (_m, _sign, _show) => myVwap.map((_v, _i) => (_v === null || !_show) ? null : _v + _sign * _m * myDev[_i]);
const myU1 = myBand(myMult1, 1, myShow1), myL1 = myBand(myMult1, -1, myShow1);
const myU2 = myBand(myMult2, 1, myShow2), myL2 = myBand(myMult2, -1, myShow2);
paint(myVwap, { name: 'VWAP', color: '#00BCD4', thickness: 2 });
paint(myU1, { name: 'Upper 1', color: 'rgba(0,128,128,0.6)' });
paint(myL1, { name: 'Lower 1', color: 'rgba(0,128,128,0.6)' });
paint(myU2, { name: 'Upper 2', color: 'rgba(255,152,0,0.6)' });
paint(myL2, { name: 'Lower 2', color: 'rgba(255,152,0,0.6)' });
color_cloud(myU1, myL1, 'rgba(0,128,128,0.08)', 'rgba(0,128,128,0.08)', 'Band 1 Up', 'Band 1 Dn');
color_cloud(myU2, myL2, 'rgba(255,152,0,0.06)', 'rgba(255,152,0,0.06)', 'Band 2 Up', 'Band 2 Dn');
const myLast = close.length - 1;
const myDevText = (myDev[myLast] !== null && myDev[myLast] > 0) ? ((close[myLast] - myVwap[myLast]) / myDev[myLast]).toFixed(2) + ' sigma' : 'na';
paint_overlay('Kloom VWAP Table', { position: 'top_right' }, {
	rows: [
		{ cells: [{ text: 'VWAP', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myVwap[myLast] === null ? 'na' : myVwap[myLast].toFixed(4), color: 'white', background_color: 'rgba(0,0,0,0.6)' }] },
		{ cells: [{ text: 'Deviation', color: 'white', background_color: 'rgba(0,0,0,0.8)' }, { text: myDevText, color: 'white', background_color: 'rgba(0,0,0,0.6)' }] }
	]
});
const myPrevClose = shift(close, 1);
const myPrevVwap = shift(myVwap, 1);
register_signal(close.map((_c, _i) => myU1[_i] !== null && _c > myU1[_i]), 'Close Above Band 1');
register_signal(close.map((_c, _i) => myL1[_i] !== null && _c < myL1[_i]), 'Close Below Band 1');
register_signal(close.map((_c, _i) => myU2[_i] !== null && _c > myU2[_i]), 'Close Above Band 2');
register_signal(close.map((_c, _i) => myL2[_i] !== null && _c < myL2[_i]), 'Close Below Band 2');
register_signal(for_every(close, myVwap, myPrevClose, myPrevVwap, (_c, _v, _pc, _pv) => _v !== null && _pv !== null && _c > _v && _pc <= _pv), 'Cross Above VWAP');
register_signal(for_every(close, myVwap, myPrevClose, myPrevVwap, (_c, _v, _pc, _pv) => _v !== null && _pv !== null && _c < _v && _pc >= _pv), 'Cross Below VWAP');
