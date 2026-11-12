/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : HTF CHOC detector by Tao Woy
 * Author       : angkoon167
 * Source URL   : https://www.tradingview.com/script/BXLigfcw-HTF-CHOC-detector-by-Tao-Woy
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : HTF CHOC detector by Tao Woy_TV
 *
 * The Pine original, in words: a notice only: a table saying a new version exists. No calculations.
 *
 * Deviations from the original: note in the top-right corner instead of the middle.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('HTF CHOC detector by Tao Woy_TV', 'price');

// The published script is only a notice pointing to a newer version.
paint_overlay('HTF CHOC note', { position: 'top_right' }, {
    rows: [{ cells: [{ text: 'New version: HTF CHOC by Tao Woy\nSearch: HTF CHOC by Tao Woy (angkoon167)', color: 'gray' }] }]
});
