/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA 5/13 Crossover (Long & Short, No Plots)
 * Author       : dianargenti
 * Source URL   : https://www.tradingview.com/script/N18VdyZl-EMA-5-13-Strategy
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA 5 13 Crossover_TV
 *
 * The Pine original, in words: stop-and-reverse on the 5/13 EMA cross, 100 percent of equity
 *
 * Deviations from the original: The Pine has no plots; entry triangles are added so the signals can be seen.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged (each reverses); 100 percent of equity.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA 5 13 Crossover_TV', 'overlay');
const myFastLen = input.number('Fast EMA Length', 5, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 13, { min: 1, max: 500 });
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myFast = myEma(close, myFastLen), mySlow = myEma(close, mySlowLen);
const myOk = (_i) => _i > 0 && myFast[_i] !== null && mySlow[_i] !== null && myFast[_i - 1] !== null && mySlow[_i - 1] !== null;
const myLong = close.map((_c, _i) => myOk(_i) && myFast[_i] > mySlow[_i] && myFast[_i - 1] <= mySlow[_i - 1]);
const myShort = close.map((_c, _i) => myOk(_i) && myFast[_i] < mySlow[_i] && myFast[_i - 1] >= mySlow[_i - 1]);
// the Pine has no plots; the entry marks are an addition so the signals can be seen
paint(myLong.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Long Mark', style: 'labels_below', color: '#26A69A' });
paint(myShort.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Short Mark', style: 'labels_above', color: '#EF5350' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
