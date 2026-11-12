/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Simple Price Display
 * Author       : Vicleelive
 * Source URL   : https://www.tradingview.com/script/d1OhRYuD-Simple-Price-Display
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Simple Price Display_TV
 *
 * The Pine original, in words: a corner table with the last close and its % change vs the previous close, green if
 *   up, red if down.
 *
 * Deviations from the original: price with 2 decimals (Pine: symbol mintick); default text size.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Simple Price Display_TV', 'price');

const myPrevClose = shift(close, 1);
const myChgPct = for_every(close, myPrevClose, (_c, _p) => _p ? (_c - _p) / _p * 100 : null);
const myLast = close.length - 1;
const myChg = myChgPct[myLast];
const myBull = myChg !== null && myChg >= 0;
const myText = close[myLast].toFixed(2) + '  (' + (myBull ? '+' : '') + (myChg === null ? 'na' : myChg.toFixed(2)) + '%)';

paint_overlay('Price Display', { position: 'top_right' }, {
    rows: [{ cells: [{ text: myText, color: myBull ? '#35ff00' : '#ff0000' }] }]
});
