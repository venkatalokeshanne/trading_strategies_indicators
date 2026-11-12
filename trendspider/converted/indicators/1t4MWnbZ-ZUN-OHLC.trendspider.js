/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Hiển thị giá OHLC trên nến (v6)
 * Author       : DHVK1369
 * Source URL   : https://www.tradingview.com/script/1t4MWnbZ-ZUN-OHLC
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : ZUN OHLC_TV
 *
 * The Pine original, in words: a label above every candle with its H, O, C, L prices (each optional).
 *
 * Deviations from the original: TrendSpider name uses the TradingView listing title (ZUN OHLC); input titles in
 *   English; prices always with one decimal (Pine '#.#' drops a trailing .0).
 * Not carried over: text size option.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('ZUN OHLC_TV', 'price');

// ==========================================
// Display options (grouped like the original Tabs/Groups)
// ==========================================
const myDisplayTab = input.tab('Display Options');

const myShowOpen = myDisplayTab.boolean('Show Open (O)', true);
const myShowHigh = myDisplayTab.boolean('Show High (H)', true);
const myShowLow = myDisplayTab.boolean('Show Low (L)', true);
const myShowClose = myDisplayTab.boolean('Show Close (C)', true);

const myTextFormatTab = input.tab('Text Format');
const myTextColor = myTextFormatTab.color('Text Color', 'white');

// Builds the OHLC text for every candle, following the same
// concatenation order as the Pine script: H, O, C, L (newline separated).
const myLabelText = for_every(open, high, low, close, (_o, _h, _l, _c) => {
	const myLines = [];

	if (myShowHigh) {
		myLines.push('H: ' + _h.toFixed(1));
	}
	if (myShowOpen) {
		myLines.push('O: ' + _o.toFixed(1));
	}
	if (myShowClose) {
		myLines.push('C: ' + _c.toFixed(1));
	}
	if (myShowLow) {
		myLines.push('L: ' + _l.toFixed(1));
	}

	return myLines.length > 0 ? myLines.join('\n') : null;
});

// Paints the OHLC text above each bar, matching the Pine script's
// label.new(..., yloc=yloc.abovebar) behavior.
paint(myLabelText, { style: 'labels_above', color: myTextColor, name: 'OHLCLabels' });
