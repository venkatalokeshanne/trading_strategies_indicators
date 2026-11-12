/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : WMA + RSI Filtreli Scalp
 * Author       : boztilkiserhan
 * Source URL   : https://www.tradingview.com/script/XF2gEG0c
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : WMA RSI Filter Scalp_TV
 *
 * The Pine original, in words: long when WMA9 crosses above WMA21 with close above both and RSI14 above 50; short
 *   on the mirror image; reverses; 100 percent of equity
 *
 * Deviations from the original: The Pine title mentions EMD/Supertrend but the code only uses WMA and RSI; converted
 *   as coded. WMA and RSI hand-rolled Pine-style.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged (each reverses); 100 percent of equity; initial capital 10000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('WMA RSI Filter Scalp_TV', 'overlay');
const myFastLen = input.number('Fast WMA', 9, { min: 1, max: 200 });
const mySlowLen = input.number('Slow WMA', 21, { min: 1, max: 200 });
const myRsiLen = input.number('RSI Period', 14, { min: 1, max: 200 });
// Pine ta.wma: weights n..1 (newest heaviest)
const myWma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = 0; myK < _n; myK += 1) myS += _s[_i - myK] * (_n - myK); return myS / (_n * (_n + 1) / 2); });
let myUp = null, myDn = null, myCnt = 0, mySu = 0, mySd = 0;
const myRsi = close.map((_c, _i) => {
	if (_i === 0) return null;
	const myCh = _c - close[_i - 1], myG = Math.max(myCh, 0), myL = Math.max(-myCh, 0);
	if (myUp === null) { mySu += myG; mySd += myL; myCnt += 1; if (myCnt === myRsiLen) { myUp = mySu / myRsiLen; myDn = mySd / myRsiLen; } else return null; }
	else { myUp = (myUp * (myRsiLen - 1) + myG) / myRsiLen; myDn = (myDn * (myRsiLen - 1) + myL) / myRsiLen; }
	return myDn === 0 ? 100 : 100 - 100 / (1 + myUp / myDn);
});
const myF = myWma(close, myFastLen), myS = myWma(close, mySlowLen);
const myOk = (_i) => _i > 0 && myF[_i] !== null && myS[_i] !== null && myF[_i - 1] !== null && myS[_i - 1] !== null && myRsi[_i] !== null;
const myLong = close.map((_c, _i) => myOk(_i) && myF[_i] > myS[_i] && myF[_i - 1] <= myS[_i - 1] && _c > myF[_i] && _c > myS[_i] && myRsi[_i] > 50);
const myShort = close.map((_c, _i) => myOk(_i) && myF[_i] < myS[_i] && myF[_i - 1] >= myS[_i - 1] && _c < myF[_i] && _c < myS[_i] && myRsi[_i] < 50);
paint(myF, { name: 'Fast WMA', color: 'blue' });
paint(myS, { name: 'Slow WMA', color: 'orange' });
paint(myLong.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Long Mark', style: 'labels_below', color: 'green' });
paint(myShort.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Short Mark', style: 'labels_above', color: 'red' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
