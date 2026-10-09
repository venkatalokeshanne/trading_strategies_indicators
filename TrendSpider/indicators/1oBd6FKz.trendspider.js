/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Kyokutan-Ashi
 * Author       : ALT_analyst
 * Source URL   : https://www.tradingview.com/script/1oBd6FKz
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Kyokutan Ashi_TV
 *
 * Deviations from the original: TrendSpider cannot draw custom candles: anti-candle OHLC painted as four
 *   colour-coded lines; request.security of the standard ticker not needed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Kyokutan Ashi_TV', 'price');
const myAnchorTab = input.tab('Anchor and Base');
const myAnchorType = myAnchorTab.select('Anchor Point', 'Open', ['Open', 'Close', 'HL2']);
const myHaMode = myAnchorTab.select('HA Open Calc', 'Traditional', ['Traditional', 'Simplified']);
const myScaleTab = input.tab('Construction and Scale');
const myCalcMode = myScaleTab.select('Wick Calculation', 'Max/Min', ['Max/Min', 'Strict']);
const myMultiplier = myScaleTab.number('Deviation Multiplier', 1.0, { min: 0.1, max: 50, step: 0.1 });
const myHaClose = close.map((_c, _i) => (open[_i] + high[_i] + low[_i] + _c) / 4);
let myPrevHaOpen = null;
const myHaOpen = close.map((_c, _i) => {
	if (myHaMode === 'Traditional') {
		myPrevHaOpen = (myPrevHaOpen === null) ? (open[_i] + _c) / 2 : (myPrevHaOpen + myHaClose[_i - 1]) / 2;
		return myPrevHaOpen;
	}
	return _i === 0 ? null : (open[_i - 1] + close[_i - 1]) / 2;
});
const myOhlc = close.map((_c, _i) => {
	if (myHaOpen[_i] === null) return null;
	const myHaHigh = Math.max(high[_i], myHaOpen[_i], myHaClose[_i]);
	const myHaLow = Math.min(low[_i], myHaOpen[_i], myHaClose[_i]);
	const myRawO = (open[_i] - myHaOpen[_i]) * myMultiplier;
	const myRawC = (_c - myHaClose[_i]) * myMultiplier;
	const myRawH = (high[_i] - myHaHigh) * myMultiplier;
	const myRawL = (low[_i] - myHaLow) * myMultiplier;
	const myAnchor = myAnchorType === 'Open' ? open[_i] : (myAnchorType === 'Close' ? _c : (high[_i] + low[_i]) / 2);
	const myAntiO = myAnchor + myRawO;
	const myAntiC = myAnchor + myRawC;
	const myAntiH = myCalcMode === 'Max/Min' ? myAnchor + Math.max(myRawO, myRawC, myRawH, myRawL) : Math.max(myAntiO, myAntiC, myAnchor + myRawH, myAnchor + myRawL);
	const myAntiL = myCalcMode === 'Max/Min' ? myAnchor + Math.min(myRawO, myRawC, myRawH, myRawL) : Math.min(myAntiO, myAntiC, myAnchor + myRawH, myAnchor + myRawL);
	return [myAntiO, myAntiH, myAntiL, myAntiC];
});
const myPart = (_k) => myOhlc.map(_a => _a === null ? null : _a[_k]);
const myColor = myOhlc.map(_a => _a === null ? null : (_a[3] >= _a[0] ? 'green' : 'red'));
// TrendSpider cannot draw custom candles: the anti-candle OHLC are painted as four lines
paint(myPart(0), { name: 'KA Open', color: myColor, thickness: 1 });
paint(myPart(1), { name: 'KA High', color: myColor, thickness: 1 });
paint(myPart(2), { name: 'KA Low', color: myColor, thickness: 1 });
paint(myPart(3), { name: 'KA Close', color: myColor, thickness: 2 });
register_signal(myColor.map(_c => _c === 'green'), 'KA Bullish Candle');
register_signal(myColor.map(_c => _c === 'red'), 'KA Bearish Candle');
