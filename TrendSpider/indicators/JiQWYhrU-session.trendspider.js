/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Session
 * Author       : YarSl
 * Source URL   : https://www.tradingview.com/script/JiQWYhrU-session
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Trading Sessions USA Asia Europe_TV
 *
 * Deviations from the original: Reviewed AI draft; bgcolor not available - sessions shaded as high-low bands;
 *   sessions use the chosen UTC offset; weekend option follows the Pine behaviour (on =
 *   Mon-Fri only).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Trading Sessions USA Asia Europe_TV', 'price');
const myShowUsa = input.boolean('USA', true);
const myShowAsia = input.boolean('Asia', true);
const myShowEur = input.boolean('Europe', true);
const myExcludeWeekends = input.boolean('Exclude Weekends', false);
const myTz = input.select('Time zone', 'UTC', ['UTC', 'UTC+1', 'UTC+2', 'UTC+3', 'UTC+4', 'UTC+5', 'UTC+6', 'UTC+7', 'UTC+8', 'UTC+9', 'UTC+10', 'UTC+11', 'UTC+12']);
const myUsaStart = input.number('USA Start HHMM', 1330, { min: 0, max: 2359 });
const myUsaEnd = input.number('USA End HHMM', 2200, { min: 0, max: 2359 });
const myAsiaStart = input.number('Asia Start HHMM', 0, { min: 0, max: 2359 });
const myAsiaEnd = input.number('Asia End HHMM', 900, { min: 0, max: 2359 });
const myEurStart = input.number('Europe Start HHMM', 600, { min: 0, max: 2359 });
const myEurEnd = input.number('Europe End HHMM', 1500, { min: 0, max: 2359 });
const myOffsetHours = myTz === 'UTC' ? 0 : Number(myTz.replace('UTC+', ''));
const myMinutes = (_hhmm) => Math.floor(_hhmm / 100) * 60 + (_hhmm % 100);
const myIn = (_m, _s, _e) => { const myS = myMinutes(_s), myE = myMinutes(_e); return myS <= myE ? (_m >= myS && _m < myE) : (_m >= myS || _m < myE); };
const myLocal = time.map(_t => _t + myOffsetHours * 3600);
const myMinuteOfDay = myLocal.map(_t => Math.floor((_t % 86400) / 60));
// day of week in the chosen zone, 0 = Sunday (epoch day 0 was a Thursday)
const myWeekend = myLocal.map(_t => { const myDow = (Math.floor(_t / 86400) + 4) % 7; return myDow === 0 || myDow === 6; });
const myOk = (_i) => !(myExcludeWeekends && myWeekend[_i]);
const myUsa = myMinuteOfDay.map((_m, _i) => myShowUsa && myOk(_i) && myIn(_m, myUsaStart, myUsaEnd));
const myAsia = myMinuteOfDay.map((_m, _i) => myShowAsia && myOk(_i) && myIn(_m, myAsiaStart, myAsiaEnd));
const myEur = myMinuteOfDay.map((_m, _i) => myShowEur && myOk(_i) && myIn(_m, myEurStart, myEurEnd));
// bgcolor is not available: each session is shaded as a band over every bar's high-low range
const myGate = (_s, _f) => _s.map((_v, _i) => _f[_i] ? _v : null);
color_cloud(myGate(high, myUsa), myGate(low, myUsa), 'rgba(149,253,204,0.3)', 'rgba(149,253,204,0.3)', 'USA Up', 'USA Dn');
color_cloud(myGate(high, myAsia), myGate(low, myAsia), 'rgba(252,145,131,0.3)', 'rgba(252,145,131,0.3)', 'Asia Up', 'Asia Dn');
color_cloud(myGate(high, myEur), myGate(low, myEur), 'rgba(90,78,253,0.3)', 'rgba(90,78,253,0.3)', 'Europe Up', 'Europe Dn');
register_signal(myUsa, 'In USA Session');
register_signal(myAsia, 'In Asia Session');
register_signal(myEur, 'In Europe Session');
