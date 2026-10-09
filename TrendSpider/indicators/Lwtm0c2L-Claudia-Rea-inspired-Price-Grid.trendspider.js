/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Price Grid (Fixed Interval) v4
 * Author       : feedya
 * Source URL   : https://www.tradingview.com/script/Lwtm0c2L-Claudia-Rea-inspired-Price-Grid
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Price Grid Fixed Interval_TV
 *
 * Deviations from the original: Reviewed AI draft; grid lines are full-width (history span and extend-right options
 *   dropped), max 20 lines each side; colour inputs fixed.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Price Grid Fixed Interval_TV', 'price');
const MAX_EACH_SIDE = 20;
const myGridSpacing = input.number('Grid Spacing', 25, { min: 0.01, max: 100000 });
const myMajorEvery = input.number('Major Line Every N', 4, { min: 1, max: 100 });
const myLinesEachSide = input.number('Lines Each Side', 10, { min: 1, max: MAX_EACH_SIDE });
const myShowLabels = input.boolean('Show Price Labels', true);
const myLastIndex = close.length - 1;
const myCenter = Math.floor(close[myLastIndex] / myGridSpacing) * myGridSpacing;
for (let myOffset = -MAX_EACH_SIDE; myOffset <= MAX_EACH_SIDE; myOffset += 1) {
	const myActive = Math.abs(myOffset) <= myLinesEachSide;
	const myLevel = myCenter + myOffset * myGridSpacing;
	const myIsMajor = Math.round(myLevel / myGridSpacing) % myMajorEvery === 0;
	const myPainted = paint(myActive ? horizontal_line(myLevel) : series_of(null), {
		name: 'Grid Line ' + (myOffset + MAX_EACH_SIDE),
		color: myIsMajor ? 'rgba(255,235,0,0.7)' : 'rgba(0,128,0,0.35)',
		thickness: myIsMajor ? 2 : 1
	});
	if (myActive && myShowLabels && myIsMajor) {
		paint_label_at_line(myPainted, myLastIndex, myLevel.toFixed(2), { color: 'rgba(255,235,0,0.9)' });
	}
}
