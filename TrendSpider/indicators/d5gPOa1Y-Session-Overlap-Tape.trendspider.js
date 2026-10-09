/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Session Overlap Tape
 * Author       : prafulparhate
 * Source URL   : https://www.tradingview.com/script/d5gPOa1Y-Session-Overlap-Tape
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : lower pane
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Session Overlap Tape_TV
 *
 * The Pine original, in words: three bars at heights 3/2/1 showing when the Asia (23-08 UTC), London (07-16) and
 *   New York (12-21) sessions are open.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Session Overlap Tape_TV', 'lower');

// Pine's time(timeframe.period, "HHMM-HHMM", "UTC") checks whether the
// current bar's time falls into a UTC-based session window. Since Unix
// timestamps are UTC-based, we can derive the UTC hour/minute directly
// from the timestamp with modulo arithmetic, without needing a timezone
// library. This reproduces the Pine logic exactly for UTC sessions.

function myUtcMinutesOfDay(_timestamp) {
	const mySecondsOfDay = ((_timestamp % 86400) + 86400) % 86400;
	return Math.floor(mySecondsOfDay / 60);
}

// Checks whether a given UTC minute-of-day falls within a session window
// defined by start/end minute-of-day. Handles sessions that wrap past
// midnight (like Asia: 23:00 to 08:00).
function myIsInSession(_minuteOfDay, _startMinute, _endMinute) {
	if (_startMinute <= _endMinute) {
		return _minuteOfDay >= _startMinute && _minuteOfDay < _endMinute;
	}
	else {
		return _minuteOfDay >= _startMinute || _minuteOfDay < _endMinute;
	}
}

const myAsiaStart = 23 * 60;
const myAsiaEnd = 8 * 60;

const myLondonStart = 7 * 60;
const myLondonEnd = 16 * 60;

const myNyStart = 12 * 60;
const myNyEnd = 21 * 60;

const myInAsia = time.map(_t => myIsInSession(myUtcMinutesOfDay(_t), myAsiaStart, myAsiaEnd) ? 3 : null);
const myInLondon = time.map(_t => myIsInSession(myUtcMinutesOfDay(_t), myLondonStart, myLondonEnd) ? 2 : null);
const myInNy = time.map(_t => myIsInSession(myUtcMinutesOfDay(_t), myNyStart, myNyEnd) ? 1 : null);

// Mirrors Pine's plot.style_linebr behavior: segments are drawn only
// where the value is non-null, breaking the line otherwise.
paint(myInAsia, { name: 'Asia Session', color: '#FFD54F', thickness: 6, style: 'line' });
paint(myInLondon, { name: 'London Session', color: '#2962FF', thickness: 6, style: 'line' });
paint(myInNy, { name: 'NY Session', color: '#EF5350', thickness: 6, style: 'line' });

// Invisible boundary lines, mirroring Pine's fully transparent hline(0) and hline(4),
// used only to keep the pane's vertical scale fixed.
paint(series_of(0), { name: 'Lower Bound', color: 'rgba(0,0,0,0)' });
paint(series_of(4), { name: 'Upper Bound', color: 'rgba(0,0,0,0)' });

// Signals for scanners, alerts and strategies.
register_signal(myInAsia.map(_v => _v === 3), 'Asia Session Active');
register_signal(myInLondon.map(_v => _v === 2), 'London Session Active');
register_signal(myInNy.map(_v => _v === 1), 'NY Session Active');
