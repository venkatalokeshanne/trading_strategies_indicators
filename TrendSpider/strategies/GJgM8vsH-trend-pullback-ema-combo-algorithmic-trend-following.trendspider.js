/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Trend Pullback EMA50 EMA200
 * Author       : MyStrategyHub
 * Source URL   : https://www.tradingview.com/script/GJgM8vsH-trend-pullback-ema-combo-algorithmic-trend-following
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Trend Pullback EMA50 EMA200_TV
 *
 * The Pine original, in words: long when price is above EMA200 but below EMA50 and the WaveTrend (9,12) line
 *   crosses above its 3-bar SMA; short on the mirror image; reversing entries; 10
 *   percent of equity, 0.05 percent commission, 1 tick slippage, orders on bar close
 *
 * Deviations from the original: Pine fills on the bar close (process_orders_on_close); the Tester fills on the next
 *   open. EMAs hand-rolled SMA-seeded.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged (reversing); sizing 10 percent of equity; commission 0.05 percent; slippage
 *   1 tick; initial capital 100000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Trend Pullback EMA50 EMA200_TV', 'overlay');
const myEma = (_s, _n) => { let myAcc = null, myCnt = 0, mySum = 0; const myK = 2 / (_n + 1); return _s.map(_v => { if (_v === null) return null; if (myAcc === null) { mySum += _v; myCnt += 1; if (myCnt === _n) myAcc = mySum / _n; return myAcc; } myAcc = myK * _v + (1 - myK) * myAcc; return myAcc; }); };
const mySma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) { if (_s[myK] === null) return null; myS += _s[myK]; } return myS / _n; });
const myE50 = myEma(close, 50), myE200 = myEma(close, 200);
// WaveTrend: esa = ema(close, 9), d = ema(|close - esa|, 9), ci = (close - esa) / (0.015 d), wt1 = ema(ci, 12), wt2 = sma(wt1, 3)
const myEsa = myEma(close, 9);
const myD = myEma(close.map((_c, _i) => myEsa[_i] === null ? null : Math.abs(_c - myEsa[_i])), 9);
const myCi = close.map((_c, _i) => (myEsa[_i] === null || myD[_i] === null || myD[_i] === 0) ? null : (_c - myEsa[_i]) / (0.015 * myD[_i]));
const myWt1 = myEma(myCi, 12), myWt2 = mySma(myWt1, 3);
const myOk = (_i) => _i > 0 && myWt1[_i] !== null && myWt2[_i] !== null && myWt1[_i - 1] !== null && myWt2[_i - 1] !== null && myE50[_i] !== null && myE200[_i] !== null;
const myXUp = close.map((_c, _i) => myOk(_i) && myWt1[_i] > myWt2[_i] && myWt1[_i - 1] <= myWt2[_i - 1]);
const myXDn = close.map((_c, _i) => myOk(_i) && myWt1[_i] < myWt2[_i] && myWt1[_i - 1] >= myWt2[_i - 1]);
const myLong = close.map((_c, _i) => myXUp[_i] && _c > myE200[_i] && _c < myE50[_i]);
const myShort = close.map((_c, _i) => myXDn[_i] && _c < myE200[_i] && _c > myE50[_i]);
paint(myE50, { name: 'EMA 50', color: 'blue' });
paint(myE200, { name: 'EMA 200', color: 'red' });
register_signal(myLong, 'Long Entry');
register_signal(myShort, 'Short Entry');
