/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Hemant Gold Strategy
 * Author       : rupasgavane
 * Source URL   : https://www.tradingview.com/script/eyaf13E5-Hemant-Gold-Strategy
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Hemant Gold Strategy_TV
 *
 * The Pine original, in words: long when price sweeps the 10-bar low and closes back above it while above the
 *   EMA200; short on the mirror image; reverses; stop 1.5 ATR(14) and target 4.5 ATR
 *   from the average entry price; 0.01 percent commission
 *
 * Deviations from the original: ATR-based stop and target are not reproduced: they are not signals and the Tester
 *   only offers fixed percent or point stops.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged; initial capital 10000; commission 0.01 percent; ATR stop/target (1.5 and
 *   4.5 ATR) — approximate with a fixed percent stop and target.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Hemant Gold Strategy_TV', 'overlay');
const myEmaLen = input.number('EMA Length', 200, { min: 1, max: 1000 });
const myN = close.length;
let myAcc = null, myCnt = 0, mySum = 0;
const myK = 2 / (myEmaLen + 1);
const myEma = close.map(_c => { if (myAcc === null) { mySum += _c; myCnt += 1; if (myCnt === myEmaLen) myAcc = mySum / myEmaLen; return myAcc; } myAcc = myK * _c + (1 - myK) * myAcc; return myAcc; });
// ll[1] / hh[1]: lowest low / highest high of the 10 bars before this one
const myLl = low.map((_l, _i) => { if (_i < 10) return null; let myM = Infinity; for (let myJ = _i - 10; myJ < _i; myJ += 1) myM = Math.min(myM, low[myJ]); return myM; });
const myHh = high.map((_h, _i) => { if (_i < 10) return null; let myM = -Infinity; for (let myJ = _i - 10; myJ < _i; myJ += 1) myM = Math.max(myM, high[myJ]); return myM; });
const myBuy = close.map((_c, _i) => myLl[_i] !== null && myEma[_i] !== null && low[_i] < myLl[_i] && _c > myLl[_i] && _c > myEma[_i]);
const mySell = close.map((_c, _i) => myHh[_i] !== null && myEma[_i] !== null && high[_i] > myHh[_i] && _c < myHh[_i] && _c < myEma[_i]);
paint(myEma, { name: 'EMA 200', color: 'blue', thickness: 2 });
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
register_signal(myBuy, 'Long Entry');
register_signal(mySell, 'Short Entry');
