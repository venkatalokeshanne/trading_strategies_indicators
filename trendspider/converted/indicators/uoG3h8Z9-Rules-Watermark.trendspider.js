/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : My Rules Watermark
 * Author       : IQ_Pips
 * Source URL   : https://www.tradingview.com/script/uoG3h8Z9-Rules-Watermark
 * Pine version : v6
 * Licence      : MPL 2.0
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : My Rules Watermark_TV
 *
 * Deviations from the original: Reviewed AI draft; text inputs are not available so the title and rules are edited
 *   in the code; static overlay table; fewer positions; sizes/colours fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('My Rules Watermark_TV', 'price');
const myPosition = input.select('Position', 'Top Right', ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right']);
const myShowSymbol = input.boolean('Show Symbol/TF', false);
const myPositionMap = { 'Top Left': 'top_left', 'Top Right': 'top_right', 'Bottom Left': 'bottom_left', 'Bottom Right': 'bottom_right' };
// Text inputs are not available: edit the title and the rules below (empty lines are skipped, up to 8 rules).
const myTitle = 'MY TRADING RULES';
const myRules = [
	'1. Trade only A+ setups',
	'2. Risk max 1% per trade',
	'3. Wait for confirmation',
	'4. No revenge trading',
	'5. Respect the stop loss',
	'6. 2 losses = stop for the day',
	'',
	''
].filter(_r => _r !== '');
const myRows = [{ cells: [{ text: myTitle, color: 'rgba(160,160,160,0.8)', background_color: 'rgba(0,0,0,0.05)' }] }];
if (myShowSymbol) myRows.push({ cells: [{ text: current.ticker + ' - ' + current.resolution, color: 'rgba(160,160,160,0.8)', background_color: 'rgba(0,0,0,0.05)' }] });
myRules.forEach(_r => myRows.push({ cells: [{ text: _r, color: 'rgba(160,160,160,0.8)', background_color: 'rgba(0,0,0,0.05)' }] }));
paint_overlay('Rules Watermark', { position: myPositionMap[myPosition] }, { rows: myRows });
register_signal(series_of(true), 'Watermark Active');
