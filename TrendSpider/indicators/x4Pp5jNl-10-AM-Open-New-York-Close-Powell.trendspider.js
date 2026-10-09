/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : 10 AM Open → New York Close
 * Author       : HagenHoldings
 * Source URL   : https://www.tradingview.com/script/x4Pp5jNl-10-AM-Open-New-York-Close-Powell
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : 10 AM Open to NY Close_TV
 *
 * Deviations from the original: Reviewed AI draft; New York time via moment-timezone; labels only on the last 30
 *   days; line ends at the close bar.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('10 AM Open to NY Close_TV', 'price');
const myMoment = library('moment-timezone');
const myOpenHour = input.number('Open Hour', 10, { min: 0, max: 23 });
const myOpenMinute = input.number('Open Minute', 0, { min: 0, max: 59 });
const myCloseHour = input.number('NY Close Hour', 16, { min: 0, max: 23 });
const myCloseMinute = input.number('NY Close Minute', 0, { min: 0, max: 59 });
const myShowMarker = input.boolean('Show 10 AM Marker', true);
const myShowLabel = input.boolean('Show 10 AM Label', true);
const myLineSeries = series_of(null);
const myMarkerSeries = series_of(null);
const myIs10AMSignal = series_of(false);
const myOpenIndexes = [];
let myActive = null;
let myActiveDay = null;
for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myT = myMoment.tz(time[myIndex] * 1000, 'America/New_York');
	const myDayKey = myT.format('YYYY-MM-DD');
	const myMinutes = myT.hours() * 60 + myT.minutes();
	if (myActiveDay !== myDayKey) { myActive = null; }
	const myIsOpen = myMinutes === myOpenHour * 60 + myOpenMinute;
	if (myIsOpen) {
		myActive = open[myIndex];
		myActiveDay = myDayKey;
		myIs10AMSignal[myIndex] = true;
		myOpenIndexes.push(myIndex);
		if (myShowMarker) myMarkerSeries[myIndex] = open[myIndex];
	}
	if (myActive !== null && myMinutes <= myCloseHour * 60 + myCloseMinute) myLineSeries[myIndex] = myActive;
}
const myLinePainted = paint(myLineSeries, { name: 'Ten AM Open', color: 'orange', thickness: 2 });
paint(myMarkerSeries, { name: 'Ten AM Marker', color: 'orange', style: 'dotted', marker: 'circle' });
if (myShowLabel) {
	myOpenIndexes.slice(-30).forEach(_i => paint_label_at_line(myLinePainted, _i, '10 AM OPEN', { color: 'orange' }));
}
register_signal(myIs10AMSignal, 'Ten AM Open Bar');
