/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Andrey Colored Volume
 * Author       : Andreyor
 * Source URL   : https://www.tradingview.com/script/muhLYKgi-Group-Colored-Volume
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Andrey Colored Volume_TV
 *
 * The Pine original, in words: volume columns: green when volume rises vs the previous bar, red when it falls,
 *   yellow when equal.
 *
 * Deviations from the original: lower pane instead of the Pine's overlay=true (volume on the price scale is
 *   unreadable); values identical.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Andrey Colored Volume_TV', 'lower');

const myPrev = shift(volume, 1);
const myColor = for_every(volume, myPrev, (_v, _p) => _p === null ? 'yellow' : _v > _p ? 'green' : _v < _p ? 'red' : 'yellow');

paint(volume, { name: 'Volume', style: 'column', color: myColor });
register_signal(for_every(volume, myPrev, (_v, _p) => _p !== null && _v > _p), 'Volume Up');
register_signal(for_every(volume, myPrev, (_v, _p) => _p !== null && _v < _p), 'Volume Down');
