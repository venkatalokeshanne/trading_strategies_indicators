/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : SMA(4)/SMA(30)
 * Author       : madereel
 * Source URL   : https://www.tradingview.com/script/KW2v4SNI-SMA-4-SMA-30
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : SMA 4 30 Crossover_TV
 *
 * The Pine original, in words: go long when SMA(4) crosses above SMA(30) and close the long when it crosses below;
 *   100 percent of equity; orders on bar close
 *
 * Deviations from the original: Pine fills on the bar close (process_orders_on_close); the Tester fills on the next
 *   open.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry signal emerged; exit Long
 *   Exit signal emerged; sizing 100 percent of equity; initial capital 100000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('SMA 4 30 Crossover_TV', 'overlay');
const mySma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) myS += _s[myK]; return myS / _n; });
const myS = mySma(close, 4), myL = mySma(close, 30);
const myOk = (_i) => _i > 0 && myS[_i] !== null && myL[_i] !== null && myS[_i - 1] !== null && myL[_i - 1] !== null;
const myBuy = close.map((_c, _i) => myOk(_i) && myS[_i] > myL[_i] && myS[_i - 1] <= myL[_i - 1]);
const mySell = close.map((_c, _i) => myOk(_i) && myS[_i] < myL[_i] && myS[_i - 1] >= myL[_i - 1]);
paint(myS, { name: 'SMA 4', color: 'white' });
paint(myL, { name: 'SMA 30', color: 'yellow' });
paint(myBuy.map(_f => _f ? constants.icons.triangle_up : null), { name: 'Buy Mark', style: 'labels_below', color: 'green' });
paint(mySell.map(_f => _f ? constants.icons.triangle_down : null), { name: 'Sell Mark', style: 'labels_above', color: 'red' });
register_signal(myBuy, 'Long Entry');
register_signal(mySell, 'Long Exit');
