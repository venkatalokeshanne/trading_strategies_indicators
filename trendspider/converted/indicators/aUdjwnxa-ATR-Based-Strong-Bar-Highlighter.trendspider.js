/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Strong Bar Highlighter
 * Author       : sukyu
 * Source URL   : https://www.tradingview.com/script/aUdjwnxa-ATR-Based-Strong-Bar-Highlighter
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Strong Bar Highlighter_TV
 *
 * Deviations from the original: Pine-exact ATR; candle colours fixed at the Pine defaults.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Strong Bar Highlighter_TV', 'price');
const myAtrTab = input.tab('ATR Filter');
const myAtrLen = myAtrTab.number('ATR Lookback', 20, { min: 1, max: 200 });
const myAtrMult = myAtrTab.number('Min Bar Size xATR', 1.2, { min: 0.1, max: 5.0, step: 0.1 });
const myCloseTab = input.tab('Close Position');
const myBullClosePct = myCloseTab.number('Bull Close Thresh', 0.60, { min: 0.5, max: 1.0, step: 0.05 });
const myBearClosePct = myCloseTab.number('Bear Close Thresh', 0.40, { min: 0.0, max: 0.5, step: 0.05 });
const myBodyTab = input.tab('Body Size Filter');
const myBodyPct = myBodyTab.number('Min Body Size', 0.50, { min: 0.0, max: 1.0, step: 0.05 });
const myBullColor = 'rgba(0, 0, 255, 0.4)';
const myBearColor = 'rgba(255, 0, 0, 0.4)';
// pine-parity: ta.atr = SMA-seeded RMA of true range
const myTr = high.map((_h, _i) => _i === 0 ? _h - low[0] : Math.max(_h - low[_i], Math.abs(_h - close[_i - 1]), Math.abs(low[_i] - close[_i - 1])));
let myAcc = null, mySeen = 0, mySeed = 0;
const myAtrVal = myTr.map(_v => {
	if (myAcc === null) { mySeed += _v; mySeen += 1; if (mySeen === myAtrLen) myAcc = mySeed / myAtrLen; return myAcc; }
	myAcc = (myAcc * (myAtrLen - 1) + _v) / myAtrLen; return myAcc;
});
const myStrong = (_bull) => close.map((_c, _i) => {
	const myRange = high[_i] - low[_i];
	if (myAtrVal[_i] === null || myRange < myAtrVal[_i] * myAtrMult) return false;
	const myPos = myRange > 0 ? (_c - low[_i]) / myRange : 0.5;
	const myBody = myRange > 0 ? Math.abs(_c - open[_i]) / myRange : 0.0;
	if (myBody < myBodyPct) return false;
	return _bull ? (_c >= open[_i] && myPos >= myBullClosePct) : (_c < open[_i] && myPos <= myBearClosePct);
});
const myIsStrongBull = myStrong(true);
const myIsStrongBear = myStrong(false);
color_candles(myIsStrongBull.map((_b, _i) => _b ? myBullColor : (myIsStrongBear[_i] ? myBearColor : null)));
register_signal(myIsStrongBull, 'Strong Bull Bar');
register_signal(myIsStrongBear, 'Strong Bear Bar');
