/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : HORARIOS TRAMPA ARELISFX
 * Author       : Arelisfx
 * Source URL   : https://www.tradingview.com/script/g049pZgm
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : HORARIOS TRAMPA ARELISFX_TV
 *
 * The Pine original, in words: marks the 'trap' hours 06:00-08:00, 13:00-14:30 and 17:00-18:30 in a chosen time
 *   zone on intraday charts.
 *
 * Deviations from the original: the three windows are fixed at the Pine defaults (TrendSpider has no session-string
 *   input); candles coloured instead of the background; transparency input dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('HORARIOS TRAMPA ARELISFX_TV', 'price');

const myMoment = library('moment-timezone');
const myTimeZone = input.select('Zona horaria', 'Europe/Madrid', ['Europe/Madrid', 'Europe/London', 'America/New_York', 'America/Bogota', 'America/Mexico_City', 'UTC']);
const myTrapColor = input.color('Color', 'rgba(255,0,0,0.15)');

// The Pine's default windows (local time in the chosen zone): 06:00-08:00, 13:00-14:30, 17:00-18:30.
const myWindows = [[6 * 60, 8 * 60], [13 * 60, 14 * 60 + 30], [17 * 60, 18 * 60 + 30]];
const myIntraday = !isNaN(current.resolution);
const myTrap = time.map(_t => {
    if (!myIntraday) return false;
    const m = myMoment.tz(_t * 1000, myTimeZone);
    const mins = m.hours() * 60 + m.minutes();
    return myWindows.some(w => mins >= w[0] && mins < w[1]);
});
color_candles(myTrap.map(_f => _f ? myTrapColor : null));
register_signal(myTrap, 'No operar');
