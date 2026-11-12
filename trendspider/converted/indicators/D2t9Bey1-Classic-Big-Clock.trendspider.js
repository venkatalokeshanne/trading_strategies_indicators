/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Classic Big Clock
 * Author       : Aleksin_Aleksandar
 * Source URL   : https://www.tradingview.com/script/D2t9Bey1-Classic-Big-Clock
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Classic Big Clock_TV
 *
 * Deviations from the original: Reviewed AI draft; static overlay image showing the time of the last calculation;
 *   Exchange time zone replaced by New York; style options dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Classic Big Clock_TV', 'price');
const myMoment = library('moment-timezone');
const myPosition = input.select('Position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);
const myTzInput = input.select('Timezone', 'UTC-5 (EST)', ['UTC-12', 'UTC-11', 'UTC-10 (HST)', 'UTC-9 (AKST)', 'UTC-8 (PST)', 'UTC-7 (MST)', 'UTC-6 (CST)', 'UTC-5 (EST)', 'UTC-4 (AST)', 'UTC-3 (BRT)', 'UTC-2', 'UTC-1', 'UTC', 'UTC+1 (CET)', 'UTC+2 (EET)', 'UTC+3 (MSK)', 'UTC+4 (GST)', 'UTC+5 (PKT)', 'UTC+5:30 (IST)', 'UTC+6 (BST)', 'UTC+7 (ICT)', 'UTC+8 (SGT/HKT)', 'UTC+9 (JST)', 'UTC+10 (AEST)', 'UTC+11', 'UTC+12 (NZST)', 'UTC+13', 'UTC+14']);
const myTzMap = {
	'UTC-12': 'Etc/GMT+12', 'UTC-11': 'Etc/GMT+11', 'UTC-10 (HST)': 'Pacific/Honolulu', 'UTC-9 (AKST)': 'America/Anchorage',
	'UTC-8 (PST)': 'America/Los_Angeles', 'UTC-7 (MST)': 'America/Denver', 'UTC-6 (CST)': 'America/Chicago', 'UTC-5 (EST)': 'America/New_York',
	'UTC-4 (AST)': 'America/Halifax', 'UTC-3 (BRT)': 'America/Sao_Paulo', 'UTC-2': 'Etc/GMT+2', 'UTC-1': 'Etc/GMT+1', 'UTC': 'UTC',
	'UTC+1 (CET)': 'Europe/Belgrade', 'UTC+2 (EET)': 'Europe/Athens', 'UTC+3 (MSK)': 'Europe/Moscow', 'UTC+4 (GST)': 'Asia/Dubai',
	'UTC+5 (PKT)': 'Asia/Karachi', 'UTC+5:30 (IST)': 'Asia/Kolkata', 'UTC+6 (BST)': 'Asia/Dhaka', 'UTC+7 (ICT)': 'Asia/Bangkok',
	'UTC+8 (SGT/HKT)': 'Asia/Singapore', 'UTC+9 (JST)': 'Asia/Tokyo', 'UTC+10 (AEST)': 'Australia/Sydney', 'UTC+11': 'Pacific/Noumea',
	'UTC+12 (NZST)': 'Pacific/Auckland', 'UTC+13': 'Pacific/Tongatapu', 'UTC+14': 'Pacific/Kiritimati'
};
const myPositionMap = { 'Top Right': 'top_right', 'Top Left': 'top_left', 'Bottom Right': 'bottom_right', 'Bottom Left': 'bottom_left' };
// static image: shows the time of the last calculation; the "Exchange" time zone option is replaced by New York time
const myNow = myMoment.tz(myTzMap[myTzInput]).format('HH:mm:ss');
paint_overlay('Big Clock', { position: myPositionMap[myPosition] }, {
	rows: [{ cells: [{ text: myNow, color: '#F8FC04', background_color: 'rgba(0,0,0,0.6)' }] }]
});
register_signal(series_of(true), 'Clock Active');
