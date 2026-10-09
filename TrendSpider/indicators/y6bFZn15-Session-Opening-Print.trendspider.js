/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Session Opening Print
 * Author       : kale_stately
 * Source URL   : https://www.tradingview.com/script/y6bFZn15-Session-Opening-Print
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Session Opening Print_TV
 *
 * Deviations from the original: Reviewed TrendSpider-AI draft, live-tested. Colour/width/extend-right options not
 *   available; higher-timeframe values lag one completed HTF bar (non-repainting).
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Session Opening Print_TV', 'price');
const myMoment = library('moment-timezone');
const mySessionHour = input.number('Open Hour', 9, { min: 0, max: 23 });
const mySessionMinute = input.number('Open Minute', 30, { min: 0, max: 59 });
const myTimezone = input.select('Timezone', 'America/New_York', [
	'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'UTC', 'Europe/London', 'Asia/Tokyo'
]);
const myShowLabel = input.boolean('Show Price Label', true);
const myOpenPriceSparse = series_of(null);
const mySessionBarFlag = series_of(false);
let myLastSessionDay = null;
let myLastIndex = -1;
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myT = myMoment.tz(time[myIndex] * 1000, myTimezone);
	const myDay = myT.date();
	if (myT.hours() === mySessionHour && myT.minutes() === mySessionMinute && myDay !== myLastSessionDay) {
		myOpenPriceSparse[myIndex] = open[myIndex];
		mySessionBarFlag[myIndex] = true;
		myLastSessionDay = myDay;
		myLastIndex = myIndex;
	}
}
const myOpenLine = interpolate_sparse_series(myOpenPriceSparse, 'constant');
const myLinePainted = paint(myOpenLine, { name: 'Session Open Print', color: 'yellow', thickness: 1 });
if (myShowLabel && myLastIndex >= 0) {
	paint_label_at_line(myLinePainted, myLastIndex, String(open[myLastIndex]), { color: 'yellow' });
}
register_signal(mySessionBarFlag, 'Session Open Bar');
