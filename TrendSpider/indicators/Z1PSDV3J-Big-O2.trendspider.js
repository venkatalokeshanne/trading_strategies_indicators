/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : My script (listed as "Big O2.")
 * Author       : BigOJR12
 * Source URL   : https://www.tradingview.com/script/Z1PSDV3J-Big-O2
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : My script_TV
 *
 * The Pine original, in words: plots the close in its own pane. Nothing else.
 *
 * Deviations from the original: none.
 * Not carried over: none. (The AI draft's always-true signal was removed — not in the Pine.)
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('My script_TV', 'lower');

paint(close, { name: 'Plot', color: '#2962FF', thickness: 1 });
