/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MA20 vs MA200 Fill
 * Author       : bayasharir
 * Source URL   : https://www.tradingview.com/script/nJFweuPA-MA20-vs-MA200-Fill
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MA20 vs MA200 Fill_TV
 *
 * The Pine original, in words: SMA 20 and SMA 200, filled green while SMA 20 is above, red while below.
 *
 * Deviations from the original: fill transparency is TrendSpider's default (Pine: 80 %). Cross signals added for
 *   scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MA20 vs MA200 Fill_TV', 'price');

const myMa20 = sma(close, 20);
const myMa200 = sma(close, 200);

paint(myMa20, { name: 'MA20', color: '#2962FF', thickness: 2 });
paint(myMa200, { name: 'MA200', color: '#FF9800', thickness: 2 });
color_cloud(myMa20, myMa200, '#4CAF50', '#FF5252', 'MA20 above', 'MA20 below');

const myAbove = for_every(myMa20, myMa200, (_a, _b) => _a !== null && _b !== null && _a > _b);
const myPrevAbove = shift(myAbove, 1);
register_signal(myAbove, 'MA20 Above MA200');
register_signal(for_every(myAbove, myPrevAbove, (_n, _p) => _n === true && _p === false), 'MA20 Crosses Above MA200');
register_signal(for_every(myAbove, myPrevAbove, (_n, _p) => _n === false && _p === true), 'MA20 Crosses Below MA200');
