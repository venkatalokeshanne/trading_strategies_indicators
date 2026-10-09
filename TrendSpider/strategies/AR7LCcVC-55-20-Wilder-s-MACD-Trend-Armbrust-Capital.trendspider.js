/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 55/20 Wilder's MACD Trend
 * Author       : ArmbrustCapital
 * Source URL   : https://www.tradingview.com/script/AR7LCcVC-55-20-Wilder-s-MACD-Trend-Armbrust-Capital
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 55 20 Wilders MACD Trend_TV
 *
 * The Pine original, in words: stop-and-reverse: long when RMA(close,20) crosses above RMA(close,55), short when it
 *   crosses below; the signal length input is unused in the Pine
 *
 * Deviations from the original: Not run in the Strategy Tester. The unused signal-length input is dropped.
 * Not carried over: Strategy Tester settings (set by hand): Entry MA2CrossLE Long Entry / MA2CrossSE
 *   Short Entry signal emerged; each entry reverses the position (no exit signals);
 *   default sizing.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('55 20 Wilders MACD Trend_TV', 'overlay');
const myFastLen = input.number('Fast Length', 20, { min: 1, max: 500 });
const mySlowLen = input.number('Slow Length', 55, { min: 1, max: 500 });
// Pine ta.rma: seeded with the SMA of the first length values
const myRma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; return _s.map(_v => { if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = (myAcc * (_n - 1) + _v) / _n; return myAcc; }); };
const myFast = myRma(close, myFastLen), mySlow = myRma(close, mySlowLen);
const myOk = (_i) => _i > 0 && myFast[_i] !== null && mySlow[_i] !== null && myFast[_i - 1] !== null && mySlow[_i - 1] !== null;
const myLong = close.map((_c, _i) => myOk(_i) && myFast[_i] > mySlow[_i] && myFast[_i - 1] <= mySlow[_i - 1]);
const myShort = close.map((_c, _i) => myOk(_i) && myFast[_i] < mySlow[_i] && myFast[_i - 1] >= mySlow[_i - 1]);
paint(myFast, { name: 'Fast MA', color: '#2962FF', thickness: 2 });
paint(mySlow, { name: 'Slow MA', color: '#FF6D00', thickness: 2 });
register_signal(myLong, 'MA2CrossLE Long Entry');
register_signal(myShort, 'MA2CrossSE Short Entry');
