/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Frankfurt Open
 * Author       : REUBEN_THE_FUCKER
 * Source URL   : https://www.tradingview.com/script/LlBP9CcU-Frankfurt-Open
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Frankfurt Open_TV
 *
 * The Pine original, in words: a box around each 08:00-09:00 Frankfurt (Europe/Berlin) session with a 0.5 level
 *   inside it.
 *
 * Deviations from the original: box drawn as filled high/low lines; hours as inputs instead of a session string;
 *   colour inputs dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Frankfurt Open_TV', 'price');

const myMoment = library('moment-timezone');
const myTz = input.select('Time zone', 'Europe/Berlin', ['Europe/Berlin', 'Europe/London', 'America/New_York', 'Etc/UTC']);
const myStartH = input.number('Session start hour', 8, { min: 0, max: 23 });
const myEndH = input.number('Session end hour', 9, { min: 0, max: 23 });
const myShowFib = input.boolean('Show level', true);
const myFibLevel = input.number('Level', 0.5, { min: 0, max: 1, step: 0.001 });

const myIn = time.map(_t => { const h = myMoment.tz(_t * 1000, myTz).hours(); return h >= myStartH && h < myEndH; });
const myTop = series_of(null), myBottom = series_of(null), myFib = series_of(null);
let hi = null, lo = null;
for (let i = 0; i < close.length; i++) {
    if (myIn[i] && (i === 0 || !myIn[i - 1])) { hi = high[i]; lo = low[i]; }
    else if (myIn[i] && hi !== null) { hi = Math.max(hi, high[i]); lo = Math.min(lo, low[i]); }
    if (myIn[i] && hi !== null) { myTop[i] = hi; myBottom[i] = lo; myFib[i] = lo + (hi - lo) * myFibLevel; }
}
const myTopP = paint(myTop, { name: 'Session High', color: 'gray', thickness: 1 });
const myBotP = paint(myBottom, { name: 'Session Low', color: 'gray', thickness: 1 });
fill(myTopP, myBotP, 'gray', 0.08);
paint(myShowFib ? myFib : series_of(null), { name: 'Fib Level', color: 'gray', thickness: 1 });
register_signal(myIn.map((v, i) => v && (i === 0 || !myIn[i - 1])), 'Session start');
