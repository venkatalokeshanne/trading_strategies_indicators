/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Nifty Gann & Strike Levels
 * Author       : Vishvajeet-D-Tonde
 * Source URL   : https://www.tradingview.com/script/E0JnLKgM-Nifty-Gann-Strike-Levels-VDT
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Nifty Gann Strike Levels_TV
 *
 * Deviations from the original: Reviewed AI draft; static levels around the last close (up to 10 each side);
 *   previous completed daily high/low; line styles and widths fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Nifty Gann Strike Levels_TV', 'price');
const MAX_LEVELS = 10;
const myShowGann = input.boolean('Show Gann Levels', true);
const myGannLevels = input.number('Gann Levels Each Side', 5, { min: 1, max: MAX_LEVELS });
const myShowInterval = input.boolean('Show 100 Interval', true);
const myIntervalLevels = input.number('Interval Levels Each Side', 5, { min: 1, max: MAX_LEVELS });
const myShowPrev = input.boolean('Show Prev Day H/L', true);
const myDaily = await request.history(current.ticker, 'D');
assert(!myDaily.error, 'Error fetching daily data: ' + myDaily.error);
// previous completed day: the daily bar before the one that contains the last chart bar
let myPrevHigh = null, myPrevLow = null;
const myLastDayStart = myDaily.time[myDaily.time.length - 1];
const myLastBar = time[time.length - 1];
const myTodayIsLast = myLastBar >= myLastDayStart;
const myPrevIdx = myTodayIsLast ? myDaily.time.length - 2 : myDaily.time.length - 1;
if (myPrevIdx >= 0) { myPrevHigh = myDaily.high[myPrevIdx]; myPrevLow = myDaily.low[myPrevIdx]; }
const myCloseLast = close[close.length - 1];
const myBaseStep = Math.round(Math.sqrt(myCloseLast) / 0.125);
const myBaseInterval = Math.round(myCloseLast / 100) * 100;
const myEmpty = () => close.map(() => null);
for (let myK = -MAX_LEVELS; myK <= MAX_LEVELS; myK += 1) {
	const myOn = myShowGann && Math.abs(myK) <= myGannLevels;
	paint(myOn ? horizontal_line(Math.pow((myBaseStep + myK) * 0.125, 2)) : myEmpty(), { name: 'Gann Level ' + (myK + MAX_LEVELS), color: '#9e9e9e', thickness: 2 });
}
for (let myK = -MAX_LEVELS; myK <= MAX_LEVELS; myK += 1) {
	const myOn = myShowInterval && Math.abs(myK) <= myIntervalLevels;
	paint(myOn ? horizontal_line(myBaseInterval + myK * 100) : myEmpty(), { name: 'Interval Level ' + (myK + MAX_LEVELS), color: '#e0a94e', thickness: 2 });
}
paint((myShowPrev && myPrevHigh !== null) ? horizontal_line(myPrevHigh) : myEmpty(), { name: 'Previous Day High', color: '#ff5252', thickness: 2 });
paint((myShowPrev && myPrevLow !== null) ? horizontal_line(myPrevLow) : myEmpty(), { name: 'Previous Day Low', color: '#4caf50', thickness: 2 });
register_signal(close.map((_c, _i) => myPrevHigh !== null && _i > 0 && close[_i - 1] <= myPrevHigh && _c > myPrevHigh), 'Cross Above Previous Day High');
register_signal(close.map((_c, _i) => myPrevLow !== null && _i > 0 && close[_i - 1] >= myPrevLow && _c < myPrevLow), 'Cross Below Previous Day Low');
