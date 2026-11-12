/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Підсвічування часу та лінія Понеділка
 * Author       : kopychyni
 * Source URL   : https://www.tradingview.com/script/Km1Wm3LK-start-week-working-hours
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Start Week working hours_TV
 *
 * The Pine original, in words: highlights working hours (17:00-22:00, UTC+3) and draws a line at the start of each
 *   Monday.
 *
 * Deviations from the original: TrendSpider name uses the listing title (Pine title is Ukrainian); hours as
 *   start/end inputs instead of a session string; candles coloured and a 'Mon' label
 *   instead of a background and a vertical line.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Start Week working hours_TV', 'price');

const myMoment = library('moment-timezone');
const myTz = input.select('Time zone', 'Etc/GMT-3', ['Etc/UTC', 'Etc/GMT-2', 'Etc/GMT-3', 'America/New_York', 'Europe/London']);
const myStart = input.number('Session start hour', 17, { min: 0, max: 23 });
const myEnd = input.number('Session end hour', 22, { min: 0, max: 23 });

// Etc/GMT-3 is UTC+3 (the POSIX sign is inverted) — the Pine default.
const myLocal = time.map(_t => myMoment.tz(_t * 1000, myTz));
const myInSession = myLocal.map(m => { const h = m.hours(); return myStart <= myEnd ? (h >= myStart && h < myEnd) : (h >= myStart || h < myEnd); });
const myDow = myLocal.map(m => m.isoWeekday());      // 1 = Monday
const myMonday = myDow.map((d, i) => i > 0 && d === 1 && myDow[i - 1] !== 1);

color_candles(for_every(myInSession, myMonday, (s, m) => m ? '#FF0000' : (s ? 'rgba(41,98,255,0.25)' : null)));
paint(myMonday.map(m => m ? 'Mon' : null), { name: 'Monday line', style: 'labels_above', color: 'red' });
register_signal(myInSession, 'In working hours');
register_signal(myMonday, 'Monday start');
