/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Quantified Relative Volume - Overlay
 * Author       : Canonius
 * Source URL   : https://www.tradingview.com/script/vDom4cSE-Quantified-Relative-Volume-Overlay
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Quantified Relative Volume Overlay_TV
 *
 * Deviations from the original: ta.relativeVolume re-implemented by hand (cumulative volume by bar position in day
 *   vs previous 10 days); exclusion only for fx.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Quantified Relative Volume Overlay_TV', 'price');
const myVolumeRatio = input.number('Volume Ratio', 3.0, { min: 0.1, max: 50 });
const myShowBarcolor = input.boolean('Color Signal Candles', true);
const myLongColor = input.color('Long Signal Color', '#00FF00');
const myShortColor = input.color('Short Signal Color', '#FF0000');
const myShowArrows = input.boolean('Show Arrows', false);
const myShowLong = input.boolean('Show Long Signals', true);
const myShowShort = input.boolean('Show Short Signals', false);
// ta.relativeVolume(10, '1D', true): cumulative volume since the day's start versus the average
// cumulative volume at the same bar position of the previous 10 days (bar position within the day).
const myDayKey = time.map(_t => { const myX = time_of(_t); return myX.month * 100 + myX.dayOfMonth; });
const myCum = [];
const myPos = [];
const myDayOf = [];
let myDay = -1;
for (let myI = 0; myI < close.length; myI += 1) {
	if (myI === 0 || myDayKey[myI] !== myDayKey[myI - 1]) { myDay += 1; myCum.push([]); }
	const myArr = myCum[myDay];
	myArr.push((myArr.length ? myArr[myArr.length - 1] : 0) + volume[myI]);
	myPos.push(myArr.length - 1);
	myDayOf.push(myDay);
}
const myRvol = close.map((_c, _i) => {
	const myD = myDayOf[_i];
	let mySum = 0, myN = 0;
	for (let myK = Math.max(0, myD - 10); myK < myD; myK += 1) {
		if (myCum[myK].length > myPos[_i]) { mySum += myCum[myK][myPos[_i]]; myN += 1; }
	}
	if (myD < 10 || myN < 5 || mySum <= 0) return null;
	return myCum[myD][myPos[_i]] / (mySum / myN);
});
const myExcluded = current.assetType === 'fx';
const myHigh = myRvol.map(_r => _r !== null && _r > myVolumeRatio);
const myLongSignal = myHigh.map((_h, _i) => _h && close[_i] > open[_i] && !myExcluded);
const myShortSignal = myHigh.map((_h, _i) => _h && close[_i] < open[_i] && !myExcluded);
color_candles(myLongSignal.map((_l, _i) => (myShowLong && myShowBarcolor && _l) ? myLongColor : ((myShowShort && myShowBarcolor && myShortSignal[_i]) ? myShortColor : null)));
paint(myLongSignal.map(_l => (myShowLong && myShowArrows && _l) ? constants.icons.triangle_up : null), { name: 'Long Signal Mark', style: 'labels_below', color: '#00FF00' });
paint(myShortSignal.map(_s => (myShowShort && myShowArrows && _s) ? constants.icons.triangle_down : null), { name: 'Short Signal Mark', style: 'labels_above', color: '#FF0000' });
register_signal(myLongSignal, 'QRVOL Long Signal');
register_signal(myShortSignal, 'QRVOL Short Signal');
