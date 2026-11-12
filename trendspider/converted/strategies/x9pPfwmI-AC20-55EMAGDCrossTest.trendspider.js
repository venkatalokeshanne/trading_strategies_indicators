/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 黃金20/55均線翻轉策略 (v6 繁體中文版)
 * Author       : acgoldgogo
 * Source URL   : https://www.tradingview.com/script/x9pPfwmI-AC20-55EMAGDCrossTest
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Gold 20 55 EMA Cross_TV
 *
 * The Pine original, in words: stop-and-reverse on the 20/55 EMA cross: long on the golden cross, short on the
 *   death cross; 5000 cash per trade on 10000 capital
 *
 * Deviations from the original: Chinese labels and alert texts dropped; EMAs hand-rolled SMA-seeded.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged (each reverses); fixed 5000 cash per trade; initial capital 10000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Gold 20 55 EMA Cross_TV', 'overlay');
const myFastLen = input.number('Fast EMA Length', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow EMA Length', 55, { min: 1, max: 500 });
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myFast = myEma(close, myFastLen), mySlow = myEma(close, mySlowLen);
const myOk = (_i) => _i > 0 && myFast[_i] !== null && mySlow[_i] !== null && myFast[_i - 1] !== null && mySlow[_i - 1] !== null;
const myGold = close.map((_c, _i) => myOk(_i) && myFast[_i] > mySlow[_i] && myFast[_i - 1] <= mySlow[_i - 1]);
const myDeath = close.map((_c, _i) => myOk(_i) && myFast[_i] < mySlow[_i] && myFast[_i - 1] >= mySlow[_i - 1]);
paint(myFast, { name: 'Fast EMA', color: 'purple', thickness: 2 });
paint(mySlow, { name: 'Slow EMA', color: 'yellow', thickness: 2 });
paint(myGold.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Gold Cross Mark', style: 'labels_below', color: 'green' });
paint(myDeath.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Death Cross Mark', style: 'labels_above', color: 'red' });
register_signal(myGold, 'Long Entry');
register_signal(myDeath, 'Short Entry');
