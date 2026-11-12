/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA9 + RSI50 First Break Strategy (Long Only)
 * Author       : Karthik3545
 * Source URL   : https://www.tradingview.com/script/V1frjvgM-KARTHIK-TENKASI-EMA9-RSI50-First-Break-Strategy-Long-Only
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA9 RSI50 First Break_TV
 *
 * The Pine original, in words: long on the first bar where close is above EMA9 and RSI14 is above 50 (not true the
 *   bar before); close the long when close falls below EMA9; 100 percent of equity
 *
 * Deviations from the original: Bar-colour highlight of the first signal replaced by the buy triangle; EMA and RSI
 *   hand-rolled Pine-style.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry signal emerged; exit Long
 *   Exit signal emerged; sizing 100 percent of equity.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA9 RSI50 First Break_TV', 'overlay');
const myEmaLen = input.number('EMA Length', 9, { min: 1, max: 500 });
const myRsiLen = input.number('RSI Length', 14, { min: 1, max: 500 });
const myN = close.length;
let myAcc = null, myCnt = 0, mySum = 0;
const myK = 2 / (myEmaLen + 1);
const myEma = close.map(_c => { if (myAcc === null) { mySum += _c; myCnt += 1; if (myCnt === myEmaLen) myAcc = mySum / myEmaLen; return myAcc; } myAcc = myK * _c + (1 - myK) * myAcc; return myAcc; });
// Pine ta.rsi: SMA-seeded RMA of gains and losses
let myUp = null, myDn = null, myC2 = 0, mySu = 0, mySd = 0;
const myRsi = close.map((_c, _i) => {
	if (_i === 0) return null;
	const myCh = _c - close[_i - 1], myG = Math.max(myCh, 0), myL = Math.max(-myCh, 0);
	if (myUp === null) { mySu += myG; mySd += myL; myC2 += 1; if (myC2 === myRsiLen) { myUp = mySu / myRsiLen; myDn = mySd / myRsiLen; } else return null; }
	else { myUp = (myUp * (myRsiLen - 1) + myG) / myRsiLen; myDn = (myDn * (myRsiLen - 1) + myL) / myRsiLen; }
	return myDn === 0 ? 100 : 100 - 100 / (1 + myUp / myDn);
});
const myCond = close.map((_c, _i) => myEma[_i] !== null && myRsi[_i] !== null && _c > myEma[_i] && myRsi[_i] > 50);
const myFirst = myCond.map((_f, _i) => _f && !(_i > 0 && myCond[_i - 1]));
const myExit = close.map((_c, _i) => myEma[_i] !== null && _c < myEma[_i]);
paint(myEma, { name: 'EMA 9', color: 'orange', thickness: 2 });
paint(myFirst.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(myExit.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Exit Mark', style: 'labels_above', color: 'red' });
register_signal(myFirst, 'Long Entry');
register_signal(myExit, 'Long Exit');
