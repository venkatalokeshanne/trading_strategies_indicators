/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Shadow Break Reversal - Dr-Ram
 * Author       : Dr-Ram
 * Source URL   : https://www.tradingview.com/script/TNLBIcYd-Shadow-Break-Reversal-Dr-Ram
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Shadow Break Reversal - Dr-Ram_TV
 *
 * The Pine original, in words: bearish: high > previous high and close < previous low; bullish: low < previous low
 *   and close > previous high. Coloured candles and triangles.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Shadow Break Reversal - Dr-Ram_TV', 'price');

const myPrevHigh = shift(high, 1);
const myPrevLow = shift(low, 1);
const myBear = for_every(high, close, myPrevHigh, myPrevLow, (_h, _c, _ph, _pl) => _ph !== null && _h > _ph && _c < _pl);
const myBull = for_every(low, close, myPrevHigh, myPrevLow, (_l, _c, _ph, _pl) => _pl !== null && _l < _pl && _c > _ph);

color_candles(for_every(myBear, myBull, (_be, _bu) => _be ? '#FF6D00' : (_bu ? '#00E5FF' : null)));
paint(for_every(myBear, _b => _b ? constants.icons.triangle_down : null), { style: 'labels_above', color: '#FF6D00', name: 'Bearish Shadow Break' });
paint(for_every(myBull, _b => _b ? constants.icons.triangle_up : null), { style: 'labels_below', color: '#00E5FF', name: 'Bullish Shadow Break' });
register_signal(myBear, 'Bearish Shadow Break Signal');
register_signal(myBull, 'Bullish Shadow Break Signal');
