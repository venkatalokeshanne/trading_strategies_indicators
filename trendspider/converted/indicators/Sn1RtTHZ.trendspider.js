/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Volume (Previous Bar Comparison)
 * Author       : simonstertrading
 * Source URL   : https://www.tradingview.com/script/Sn1RtTHZ
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Volume (Previous Bar Comparison)_TV
 *
 * The Pine original, in words: volume columns, teal when volume > previous bar's volume,
 * red otherwise.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Volume (Previous Bar Comparison)_TV', 'lower');

const myIsGrow = for_every(volume, shift(volume, 1), (_v, _p) => _p !== null && _v > _p);
const myVolColor = for_every(myIsGrow, _g => _g ? '#26A69A' : '#EF5350');

paint(volume, { name: 'Volume', style: 'column', color: myVolColor });
register_signal(myIsGrow, 'Volume Increased');
