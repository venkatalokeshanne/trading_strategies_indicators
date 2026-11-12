/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MA9 vs ma26 Fill
 * Author       : bayasharir
 * Source URL   : https://www.tradingview.com/script/MEEuE1hC-MA9-vs-ma26-Fill
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MA9 vs ma26 Fill_TV
 *
 * The Pine original, in words: SMA 9 and SMA 26, filled green while SMA 9 is above, red
 * while below.
 *
 * Deviations from the original: fill transparency is TrendSpider's default (Pine: 80 %).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MA9 vs ma26 Fill_TV', 'price');

const myMa9 = sma(close, 9);
const myMa26 = sma(close, 26);

paint(myMa9, { name: 'MA9', color: '#2962FF', thickness: 2 });
paint(myMa26, { name: 'MA26', color: '#363A45', thickness: 2 });
color_cloud(myMa9, myMa26, '#4CAF50', '#FF5252', 'MA9 above', 'MA9 below');

register_signal(for_every(myMa9, myMa26, (_a, _b) => _a !== null && _b !== null && _a > _b), 'MA9 Above MA26');
