/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : My script
 * Author       : BigOJR12
 * Source URL   : https://www.tradingview.com/script/Z1PSDV3J-Big-O2
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Big O2_TV
 *
 * The Pine original, in words: plots the close in its own pane. Nothing else.
 *
 * Deviations from the original: TrendSpider name uses the TradingView listing title (Big O2) because the Pine title
 *   'My script' is generic.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Big O2_TV', 'lower');

paint(close, { name: 'Plot', color: '#2962FF', thickness: 1 });
