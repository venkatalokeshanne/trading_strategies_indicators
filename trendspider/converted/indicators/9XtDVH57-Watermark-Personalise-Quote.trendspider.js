/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Watermark V6.2
 * Author       : LionTheories
 * Source URL   : https://www.tradingview.com/script/9XtDVH57-Watermark-Personalise-Quote
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Watermark V6.2_TV
 *
 * The Pine original, in words: a fixed quote shown as a watermark table.
 *
 * Deviations from the original: middle positions and centre positions are mapped to the nearest TrendSpider corner.
 * Not carried over: background colour, text size and alignment options.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Watermark V6.2_TV', 'price');

// This Pine script only draws a static text watermark table on the
// chart - there is no numeric calculation, no signal, nothing that
// could be scanned, alerted on, or backtested. The closest
// TrendSpider equivalent is a paint_overlay() table showing the
// same text. Position/alignment options from Pine's table.new are
// mapped to the overlay's "position" param (TrendSpider does not
// support all 9 Pine positions, so we map to the closest
// equivalent among top_left, top_right, bottom_left, bottom_right
// and center variants where available).

const myShowWatermark = input.boolean('Show Watermark', true);

const myPosition = input.select('Watermark Position', 'top_center', [
	'top_left', 'top_center', 'top_right',
	'bottom_left', 'bottom_center', 'bottom_right'
]);

const myTextColor = input.color('Text Color', 'rgba(255,255,255,0.7)');

// Map our select values to overlay-supported position keywords.
// TrendSpider overlays support corner positions; "center" variants
// fall back to the nearest supported corner.
const myPositionMap = {
	top_left: 'top_left',
	top_center: 'top_right',
	top_right: 'top_right',
	bottom_left: 'bottom_left',
	bottom_center: 'bottom_right',
	bottom_right: 'bottom_right'
};

const myWatermarkText = 'No matter how hungry, the Lion never eats grass';

paint_overlay('WatermarkTable', { position: myPositionMap[myPosition], offset_x: 10, offset_y: 10 }, {
	rows: myShowWatermark ? [{
		cells: [{
			text: myWatermarkText,
			color: myTextColor
		}]
	}] : []
});
