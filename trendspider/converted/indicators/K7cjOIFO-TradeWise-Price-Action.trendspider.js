/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : TradeWise Price Action
 * Author       : deepakthangaraj10
 * Source URL   : https://www.tradingview.com/script/K7cjOIFO-TradeWise-Price-Action
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : TradeWise Price Action_TV
 *
 * Deviations from the original: Entry/stop/target levels and labels are drawn only for the latest signal, 25 bars to
 *   the right, as in the Pine (earlier signals keep no lines); stop distance clamped to
 *   the dollar min/max
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('TradeWise Price Action_TV', 'price');
const mySwingLen = input.number('Swing Lookback', 10, { min: 1, max: 200 });
const myMinSl = input.number('Min SL ($)', 3.0, { min: 0, max: 1000 });
const myMaxSl = input.number('Max SL ($)', 7.0, { min: 0, max: 1000 });
const myRr1 = 1.0, myRr2 = 1.5, myRr3 = 2.0;
const myN = close.length;
// highest/lowest of the previous swingLen bars (swingHigh[1] in the Pine)
const myPrevHigh = high.map((_h, _i) => { if (_i < mySwingLen) return null; let myM = -Infinity; for (let myK = _i - mySwingLen; myK < _i; myK += 1) myM = Math.max(myM, high[myK]); return myM; });
const myPrevLow = low.map((_l, _i) => { if (_i < mySwingLen) return null; let myM = Infinity; for (let myK = _i - mySwingLen; myK < _i; myK += 1) myM = Math.min(myM, low[myK]); return myM; });
const myBuy = close.map((_c, _i) => myPrevLow[_i] !== null && low[_i] < myPrevLow[_i] && _c > open[_i] && _c > myPrevLow[_i]);
const mySell = close.map((_c, _i) => myPrevHigh[_i] !== null && high[_i] > myPrevHigh[_i] && _c < open[_i] && _c < myPrevHigh[_i]);
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'lime' });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
// the Pine keeps only the latest signal's entry / stop / three targets, drawn 25 bars to the right
let myLastI = -1, myLastBuy = false;
for (let myI = 0; myI < myN; myI += 1) { if (myBuy[myI]) { myLastI = myI; myLastBuy = true; } if (mySell[myI]) { myLastI = myI; myLastBuy = false; } }
const myLevel = (_v) => close.map((_c, _i) => (myLastI >= 0 && _i >= myLastI && _i <= myLastI + 25) ? _v : null);
let myE = null, mySl = null, myT1 = null, myT2 = null, myT3 = null;
if (myLastI >= 0) {
	myE = close[myLastI];
	const myDist = Math.max(myMinSl, Math.min(myLastBuy ? close[myLastI] - low[myLastI] : high[myLastI] - close[myLastI], myMaxSl));
	const myDir = myLastBuy ? 1 : -1;
	mySl = myE - myDir * myDist; myT1 = myE + myDir * myDist * myRr1; myT2 = myE + myDir * myDist * myRr2; myT3 = myE + myDir * myDist * myRr3;
}
const myEnd = myLastI >= 0 ? Math.min(myN - 1, myLastI + 25) : -1;
const myPe = paint(myLevel(myE), { name: 'Entry', color: 'blue', thickness: 2 });
const myPs = paint(myLevel(mySl), { name: 'Stop Loss', color: 'red', thickness: 2 });
const myP1 = paint(myLevel(myT1), { name: 'Target 1', color: 'green', thickness: 2 });
const myP2 = paint(myLevel(myT2), { name: 'Target 2', color: 'green', thickness: 2 });
const myP3 = paint(myLevel(myT3), { name: 'Target 3', color: 'green', thickness: 2 });
if (myEnd >= 0) {
	paint_label_at_line(myPe, myEnd, 'ENTRY ' + myE.toFixed(2), { color: 'blue' });
	paint_label_at_line(myPs, myEnd, 'SL ' + mySl.toFixed(2), { color: 'red' });
	paint_label_at_line(myP1, myEnd, 'TP1 ' + myT1.toFixed(2), { color: 'green' });
	paint_label_at_line(myP2, myEnd, 'TP2 ' + myT2.toFixed(2), { color: 'green' });
	paint_label_at_line(myP3, myEnd, 'TP3 ' + myT3.toFixed(2), { color: 'green' });
}
register_signal(myBuy, 'Buy Signal');
register_signal(mySell, 'Sell Signal');
