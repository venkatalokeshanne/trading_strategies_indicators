/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : News Event Price Bands
 * Author       : WaffleTime
 * Source URL   : https://www.tradingview.com/script/W15MAajQ-News-Trading-Stop-Levels
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : News Event Price Bands_TV
 *
 * Deviations from the original: Reviewed AI draft; bands drawn as full-width lines at the last close; label offset
 *   and line extension options dropped.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('News Event Price Bands_TV', 'price');
const myEventPreset = input.select('Event preset', 'Core CPI (High Probability)', [
	'Core CPI (High Probability)',
	'NFP (Medium Probability)'
]);
const myLineWidth = input.number('Line width', 1, { min: 1, max: 4 });
const mySpreadPoints = myEventPreset === 'Core CPI (High Probability)' ? 40 : 30;
const myLastIndex = close.length - 1;
const myLastClose = close[myLastIndex];
const myUpperLine = paint(horizontal_line(myLastClose + mySpreadPoints), { name: 'Upper Band', color: '#4CAF50', thickness: myLineWidth });
const myLowerLine = paint(horizontal_line(myLastClose - mySpreadPoints), { name: 'Lower Band', color: '#F44336', thickness: myLineWidth });
paint_label_at_line(myUpperLine, myLastIndex, 'Buy stops here', { color: '#4CAF50' });
paint_label_at_line(myLowerLine, myLastIndex, 'Sell stops here', { color: '#F44336' });
