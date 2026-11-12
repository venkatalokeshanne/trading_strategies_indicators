/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA 20/200/500/1500
 * Author       : lglmoura
 * Source URL   : https://www.tradingview.com/script/HDOtGyzw-EMA-20-200-500-1500
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : EMA 20/200/500/1500_TV
 *
 * The Pine original, in words: EMA 20, 200, 500 and 1500 of the close.
 *
 * Deviations from the original: trend signals added for scanning.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('EMA 20/200/500/1500_TV', 'price');

const myAbove = (_a, _b) => for_every(_a, _b, (a, b) => a !== null && b !== null && a > b);

const myEma20 = ema(close, 20);
const myEma200 = ema(close, 200);
const myEma500 = ema(close, 500);
const myEma1500 = ema(close, 1500);
paint(myEma20, { name: 'EMA 20', color: '#2962FF', thickness: 1 });
paint(myEma200, { name: 'EMA 200', color: '#FF5252', thickness: 1 });
paint(myEma500, { name: 'EMA 500', color: '#FFEB3B', thickness: 1 });
paint(myEma1500, { name: 'EMA 1500', color: '#FF9800', thickness: 1 });

register_signal(myAbove(myEma20, myEma200), 'EMA20 Above EMA200');
register_signal(myAbove(myEma200, myEma20), 'EMA20 Below EMA200');
register_signal(for_every(myEma20, myEma200, myEma500, myEma1500, (a, b, c, d) => d !== null && a > b && b > c && c > d), 'Bullish Stacked Trend');
register_signal(for_every(myEma20, myEma200, myEma500, myEma1500, (a, b, c, d) => d !== null && a < b && b < c && c < d), 'Bearish Stacked Trend');
