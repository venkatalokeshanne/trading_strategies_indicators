/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : SMA 50 / 100 / 150 / 200 / SSMA 360
 * Author       : AbaddonPL
 * Source URL   : https://www.tradingview.com/script/XgFMoS4t
 * Pine version : v?
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : SMA 50 100 150 200 SSMA 360_TV
 *
 * Deviations from the original: Reviewed TrendSpider-AI draft, live-tested. Colour/width/extend-right options not
 *   available; higher-timeframe values lag one completed HTF bar (non-repainting).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('SMA 50 100 150 200 SSMA 360_TV', 'price');
const myTab = input.tab('Lines');
const myShow50 = myTab.boolean('Show SMA 50', true);
const myShow100 = myTab.boolean('Show SMA 100', true);
const myShow150 = myTab.boolean('Show SMA 150', true);
const myShow200 = myTab.boolean('Show SMA 200', true);
const myShow360 = myTab.boolean('Show SSMA 360', true);
const mySma50 = sma(close, 50);
const mySma100 = sma(close, 100);
const mySma150 = sma(close, 150);
const mySma200 = sma(close, 200);
const mySsma360 = sma(sma(close, 360), 360);
const myGate = (_s, _show) => for_every(_s, _v => _show ? _v : null);
paint(myGate(mySma50, myShow50), { name: 'SMA 50', color: 'blue', thickness: 1 });
paint(myGate(mySma100, myShow100), { name: 'SMA 100', color: 'orange', thickness: 2 });
paint(myGate(mySma150, myShow150), { name: 'SMA 150', color: 'green', thickness: 3 });
paint(myGate(mySma200, myShow200), { name: 'SMA 200', color: 'red', thickness: 4 });
paint(myGate(mySsma360, myShow360), { name: 'SSMA 360', color: 'purple', thickness: 5 });
const myUp = (_ma) => for_every(close, open, _ma, (_c, _o, _m) => _m !== null && _c > _m && _o <= _m);
const myDown = (_ma) => for_every(close, open, _ma, (_c, _o, _m) => _m !== null && _c < _m && _o >= _m);
register_signal(myUp(mySma50), 'Cross Above SMA50');
register_signal(myDown(mySma50), 'Cross Below SMA50');
register_signal(myUp(mySma100), 'Cross Above SMA100');
register_signal(myDown(mySma100), 'Cross Below SMA100');
register_signal(myUp(mySma150), 'Cross Above SMA150');
register_signal(myDown(mySma150), 'Cross Below SMA150');
register_signal(myUp(mySma200), 'Cross Above SMA200');
register_signal(myDown(mySma200), 'Cross Below SMA200');
register_signal(myUp(mySsma360), 'Cross Above SSMA360');
register_signal(myDown(mySsma360), 'Cross Below SSMA360');
