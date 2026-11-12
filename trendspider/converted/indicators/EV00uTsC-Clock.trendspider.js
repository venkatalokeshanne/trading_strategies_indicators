/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Clock
 * Author       : bynummm
 * Source URL   : https://www.tradingview.com/script/EV00uTsC-Clock
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Clock_TV
 *
 * Deviations from the original: Reviewed AI draft; clock drawn as a static overlay image showing the time of the
 *   last calculation; fewer position choices; style options dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Clock_TV', 'price');
const myMoment = library('moment-timezone');
const myTimeZone = input.select('Time zone', 'America/Chicago', ['America/Chicago', 'America/New_York', 'America/Los_Angeles', 'Etc/UTC', 'Europe/London', 'Asia/Tokyo']);
const myUse24Hour = input.boolean('Use 24-hour time', false);
const myShowSeconds = input.boolean('Show seconds', false);
const myPosition = input.select('Clock position', 'Top Right', ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']);
const myPositionMap = { 'Top Left': 'top_left', 'Top Right': 'top_right', 'Bottom Left': 'bottom_left', 'Bottom Right': 'bottom_right' };
const myFormat = myUse24Hour ? (myShowSeconds ? 'HH:mm:ss' : 'HH:mm') : (myShowSeconds ? 'h:mm:ss A' : 'h:mm A');
// the clock is a static image: it shows the time at which the indicator was last calculated
const myNow = myMoment.tz(myTimeZone).format(myFormat);
paint_overlay('Clock Table', { position: myPositionMap[myPosition] }, {
	rows: [{ cells: [{ text: myNow, color: '#ffffff', background_color: 'rgba(0,0,0,0.5)' }] }]
});
register_signal(series_of(true), 'Clock Active');
