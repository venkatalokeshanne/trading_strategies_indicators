/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 00:00 va 12:00 (Toshkent)
 * Author       : version
 * Source URL   : https://www.tradingview.com/script/gOjqnIJV-00-00-va-12-00-Toshkent
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 00:00 va 12:00 (Toshkent)_TV
 *
 * The Pine original, in words: vertical lines at 19:00 (green) and 22:00 (red) Tashkent time.
 *
 * Deviations from the original: TrendSpider has no full-height vertical lines: the bar is coloured and labelled with
 *   the time instead.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('00:00 va 12:00 (Toshkent)_TV', 'price');

// Tashkent is UTC+5 all year (no daylight saving).
const myHm = time.map(_t => { const s = (((_t + 5 * 3600) % 86400) + 86400) % 86400; return [Math.floor(s / 3600), Math.floor((s % 3600) / 60)]; });
const myAt19 = myHm.map(_x => _x[0] === 19 && _x[1] === 0);
const myAt22 = myHm.map(_x => _x[0] === 22 && _x[1] === 0);

color_candles(for_every(myAt19, myAt22, (_a, _b) => _a ? '#4CAF50' : (_b ? '#FF5252' : null)));
paint(for_every(myAt19, _a => _a ? '19:00' : null), { name: '19:00 marker', style: 'labels_above', color: '#4CAF50' });
paint(for_every(myAt22, _b => _b ? '22:00' : null), { name: '22:00 marker', style: 'labels_above', color: '#FF5252' });
register_signal(myAt19, 'Tashkent 19:00');
register_signal(myAt22, 'Tashkent 22:00');
