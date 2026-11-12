/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : NQ 50-Point Grid
 * Author       : ISneakyNeeks
 * Source URL   : https://www.tradingview.com/script/pJVm8oDj-NQ-50-Point-Grid
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : NQ 50 Point Grid_TV
 *
 * Deviations from the original: Reviewed AI draft; NQ-only check and warning table dropped (grid shows on any
 *   symbol); colour/width inputs fixed; max 20 levels each side.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('NQ 50 Point Grid_TV', 'price');
const GRID_SIZE = 50;
const MAX_EACH_SIDE = 20;
const myLevelsEachSide = input.number('Levels each side', 20, { min: 1, max: MAX_EACH_SIDE });
const myShowPriceLabels = input.boolean('Show price labels', true);
const myEmphasizeHundreds = input.boolean('Emphasize 100 pt', true);
const myLastIndex = close.length - 1;
const myCenterLevel = Math.floor(close[myLastIndex] / GRID_SIZE) * GRID_SIZE;
for (let myIndex = 0; myIndex < MAX_EACH_SIDE * 2 + 1; myIndex += 1) {
	const myOffset = myIndex - MAX_EACH_SIDE;
	const myActive = Math.abs(myOffset) <= myLevelsEachSide;
	const myPrice = myCenterLevel + myOffset * GRID_SIZE;
	const myIsHundred = Math.round(myPrice / GRID_SIZE) % 2 === 0;
	const myEmph = myEmphasizeHundreds && myIsHundred;
	const myPainted = paint(myActive ? horizontal_line(myPrice) : series_of(null), {
		name: 'Level ' + myIndex,
		color: myEmph ? 'rgba(0,80,220,0.8)' : 'rgba(128,128,128,0.45)',
		thickness: myEmph ? 2 : 1
	});
	if (myShowPriceLabels && myActive) {
		paint_label_at_line(myPainted, myLastIndex, String(myPrice), { color: myEmph ? 'rgba(0,80,220,0.8)' : 'gray' });
	}
}
