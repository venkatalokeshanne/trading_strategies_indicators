/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : BTC Averages Strategy - Long & Short
 * Author       : rsouzaeverton
 * Source URL   : https://www.tradingview.com/script/Nqu2Bqhu-BTC-Averages-Strategy-Long-Short
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (signals)
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : BTC Averages Strategy_TV
 *
 * The Pine original, in words: long when the 3 SMA is above the 48 SMA and close is above the 168 SMA, close the
 *   long when fast falls below slow; short when fast is below slow and close below the
 *   trend SMA, close the short when fast rises above slow; 99 percent of equity, 0.05
 *   percent commission
 *
 * Deviations from the original: Not run in the Strategy Tester. Trend background drawn as high-low bands.
 * Not carried over: Strategy Tester settings (set by hand): Entry Long Entry / Short Entry signal
 *   emerged; exit Long Exit / Short Exit signal emerged; sizing 99 percent of equity;
 *   commission 0.05 percent; initial capital 10000.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('BTC Averages Strategy_TV', 'overlay');
const myFastLen = input.number('Fast MA Period', 3, { min: 1, max: 1000 });
const mySlowLen = input.number('Slow MA Period', 48, { min: 1, max: 1000 });
const myTrendLen = input.number('Trend MA Period', 168, { min: 1, max: 2000 });
const mySma = (_s, _n) => _s.map((_v, _i) => { if (_i < _n - 1) return null; let myS = 0; for (let myK = _i - _n + 1; myK <= _i; myK += 1) myS += _s[myK]; return myS / _n; });
const myF = mySma(close, myFastLen), myS = mySma(close, mySlowLen), myT = mySma(close, myTrendLen);
const myOk = (_i) => myF[_i] !== null && myS[_i] !== null && myT[_i] !== null;
const myLongEntry = close.map((_c, _i) => myOk(_i) && myF[_i] > myS[_i] && _c > myT[_i]);
const myLongExit = close.map((_c, _i) => myOk(_i) && myF[_i] < myS[_i]);
const myShortEntry = close.map((_c, _i) => myOk(_i) && myF[_i] < myS[_i] && _c < myT[_i]);
const myShortExit = close.map((_c, _i) => myOk(_i) && myF[_i] > myS[_i]);
paint(myF, { name: 'Fast MA', color: '#2962FF' });
paint(myS, { name: 'Slow MA', color: '#FF9800' });
paint(myT, { name: 'Trend MA', color: '#E0E0E0', thickness: 2 });
// bgcolor trend tint as high-low bands
const myUp = close.map((_c, _i) => myT[_i] !== null && _c > myT[_i]), myDn = close.map((_c, _i) => myT[_i] !== null && _c <= myT[_i]);
color_cloud(high.map((_h, _i) => myUp[_i] ? _h : null), low.map((_l, _i) => myUp[_i] ? _l : null), 'rgba(0,180,0,0.1)', 'rgba(0,180,0,0.1)', 'Uptrend Up', 'Uptrend Dn');
color_cloud(high.map((_h, _i) => myDn[_i] ? _h : null), low.map((_l, _i) => myDn[_i] ? _l : null), 'rgba(200,0,0,0.1)', 'rgba(200,0,0,0.1)', 'Downtrend Up', 'Downtrend Dn');
register_signal(myLongEntry, 'Long Entry');
register_signal(myLongExit, 'Long Exit');
register_signal(myShortEntry, 'Short Entry');
register_signal(myShortExit, 'Short Exit');
