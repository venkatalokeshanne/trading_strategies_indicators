/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : TEST - Verificacion Ordenes
 * Author       : gjcb85
 * Source URL   : https://www.tradingview.com/script/NWIwEuKt
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : TEST Verificacion Ordenes_TV
 *
 * The Pine original, in words: stop-and-reverse on the 20/50 EMA cross; 10000 percent of equity sizing, 0.01
 *   percent commission, orders on bar close
 *
 * Deviations from the original: Pine fills on the bar close; the Tester fills on the next open. Entry triangles
 *   kept.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged (each reverses); commission 0.01 percent; initial capital 1000000; the huge
 *   percent-of-equity sizing is not copied.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('TEST Verificacion Ordenes_TV', 'overlay');
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myE20 = myEma(close, 20), myE50 = myEma(close, 50);
const myOk = (_i) => _i > 0 && myE20[_i] !== null && myE50[_i] !== null && myE20[_i - 1] !== null && myE50[_i - 1] !== null;
const myLong = close.map((_c, _i) => myOk(_i) && myE20[_i] > myE50[_i] && myE20[_i - 1] <= myE50[_i - 1]);
const myShort = close.map((_c, _i) => myOk(_i) && myE20[_i] < myE50[_i] && myE20[_i - 1] >= myE50[_i - 1]);
paint(myE20, { name: 'EMA 20', color: 'yellow', thickness: 2 });
paint(myE50, { name: 'EMA 50', color: 'blue', thickness: 2 });
paint(myLong.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Long Mark', style: 'labels_below', color: 'lime' });
paint(myShort.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Short Mark', style: 'labels_above', color: 'red' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
