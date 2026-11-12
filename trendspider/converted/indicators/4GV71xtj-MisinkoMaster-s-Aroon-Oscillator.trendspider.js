/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MisinkoMaster's Aroon Oscillator
 * Author       : MisinkoMaster
 * Source URL   : https://www.tradingview.com/script/4GV71xtj-MisinkoMaster-s-Aroon-Oscillator
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MisinkoMaster Special Aroon Oscillator_TV
 *
 * Deviations from the original: Reviewed AI draft; highestbars/lowestbars hand-rolled; recoloured price candles and
 *   glow lines not carried over.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MisinkoMaster Special Aroon Oscillator_TV', 'lower');
const mySrcName = input.select('Source', 'close', ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4']);
const myLength = input.number('Length', 28, { min: 2, max: 500 });
const mySmooth = input.number('Smooth', 14, { min: 2, max: 500 });
const mySrc = close.map((_c, _i) => {
	if (mySrcName === 'open') return open[_i];
	if (mySrcName === 'high') return high[_i];
	if (mySrcName === 'low') return low[_i];
	if (mySrcName === 'hl2') return (high[_i] + low[_i]) / 2;
	if (mySrcName === 'hlc3') return (high[_i] + low[_i] + _c) / 3;
	if (mySrcName === 'ohlc4') return (open[_i] + high[_i] + low[_i] + _c) / 4;
	return _c;
});
const myEmaSrc = ema(mySrc, mySmooth);
const mySource = mySrc.map((_s, _i) => myEmaSrc[_i] === null ? null : myEmaSrc[_i] * (1 - 2 / (1 + mySmooth)) + _s * 2 / (1 + mySmooth));
// ta.highestbars / ta.lowestbars over length + 1 bars (offset <= 0); ties resolve to the most recent bar
const myMao = mySource.map((_s, _i) => {
	if (_i < myLength) return null;
	let myHiIdx = -1, myLoIdx = -1, myHi = -Infinity, myLo = Infinity;
	for (let myK = _i - myLength; myK <= _i; myK += 1) {
		const myV = mySource[myK];
		if (myV === null) return null;
		if (myV >= myHi) { myHi = myV; myHiIdx = myK; }
		if (myV <= myLo) { myLo = myV; myLoIdx = myK; }
	}
	return 100 * ((myHiIdx - _i) + myLength) / myLength - 100 * ((myLoIdx - _i) + myLength) / myLength;
});
let myTrendState = 0;
const myTrend = myMao.map(_m => {
	if (_m !== null && _m > 0) myTrendState = 1;
	else if (_m !== null && _m < 0) myTrendState = -1;
	return myTrendState;
});
const myLineColor = myMao.map((_m, _i) => _m === 0 ? '#444b40' : (myTrend[_i] === 1 ? '#127005' : '#a30404'));
const myZero = series_of(0);
paint(myMao, { name: 'Special Aroon Oscillator', style: 'histogram', color: myLineColor, thickness: 3 });
paint(myZero, { name: 'Neutral Value', color: 'rgba(68,75,64,0.5)', thickness: 2 });
paint(horizontal_line(100), { name: 'Max Value', color: 'rgba(18,112,5,0.6)', thickness: 2 });
paint(horizontal_line(-100), { name: 'Min Value', color: 'rgba(163,4,4,0.6)', thickness: 2 });
color_cloud(myMao, myZero, 'rgba(4,243,112,0.3)', 'rgba(241,20,20,0.3)', 'Bullish Fill', 'Bearish Fill');
const myPrev = shift(myMao, 1);
register_signal(for_every(myMao, myPrev, (_m, _p) => _m !== null && _p !== null && _m > 0 && _p <= 0), 'Bullish Zero Cross');
register_signal(for_every(myMao, myPrev, (_m, _p) => _m !== null && _p !== null && _m < 0 && _p >= 0), 'Bearish Zero Cross');
register_signal(myTrend.map(_t => _t === 1), 'Bullish Trend');
register_signal(myTrend.map(_t => _t === -1), 'Bearish Trend');
