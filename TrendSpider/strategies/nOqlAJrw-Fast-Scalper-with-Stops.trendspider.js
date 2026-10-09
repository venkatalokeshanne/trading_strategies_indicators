/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Fast Scalper with Stops
 * Author       : stevenygabbyperez
 * Source URL   : https://www.tradingview.com/script/nOqlAJrw-Fast-Scalper-with-Stops
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Fast Scalper with Stops_TV
 *
 * The Pine original, in words: identical Pine source to SL3hUrJG (Fast Scalper with Stops)
 *
 * Deviations from the original: Duplicate of SL3hUrJG; shares the same saved TrendSpider script. Not run in the
 *   Strategy Tester.
 * Not carried over: Strategy Tester settings (set by hand): same as SL3hUrJG.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Fast Scalper with Stops_TV', 'overlay');
const myFastLen = input.number('Fast EMA Length', 5, { min: 1, max: 200 });
const mySlowLen = input.number('Slow EMA Length', 13, { min: 1, max: 200 });
// Pine ta.ema: seeded with the SMA of the first length values
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const myFast = myEma(close, myFastLen), mySlow = myEma(close, mySlowLen);
const myLong = close.map((_c, _i) => _i > 0 && myFast[_i] !== null && mySlow[_i] !== null && myFast[_i - 1] !== null && mySlow[_i - 1] !== null && myFast[_i] > mySlow[_i] && myFast[_i - 1] <= mySlow[_i - 1]);
const myShort = close.map((_c, _i) => _i > 0 && myFast[_i] !== null && mySlow[_i] !== null && myFast[_i - 1] !== null && mySlow[_i - 1] !== null && myFast[_i] < mySlow[_i] && myFast[_i - 1] >= mySlow[_i - 1]);
paint(myFast, { name: 'Fast EMA', color: '#2962FF' });
paint(mySlow, { name: 'Slow EMA', color: '#EF5350' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
