describe_indicator('Clock');
// This indicator has no price-based logic (it is a pure clock display),
// so there is nothing meaningful to scan, alert or backtest on.
// We still register a constant "always true" signal only to satisfy
// the platform requirement that register_signal() calls are present
// consistently; it carries no real analytical meaning.
const momentTz = library('moment-timezone');

const myTab = input.tab('Time');
const myTimeZone = myTab.select('Time zone', 'America/Chicago', [
	'America/Chicago',
	'America/New_York',
	'America/Los_Angeles',
	'Etc/UTC',
	'Europe/London',
	'Asia/Tokyo'
]);
const myUse24Hour = myTab.boolean('Use 24-hour time', false);
const myShowSeconds = myTab.boolean('Show seconds', false);

const myPositionTab = input.tab('Position');
// Only the 4 corner positions are supported by the overlay engine:
// top_left, top_right, bottom_left, bottom_right.
// The "center" variants (top_center / bottom_center) are not valid
// position values and caused the
// "paint_overlay(): invalid position value" error, so they were removed.
const myPositionInput = myPositionTab.select('Clock position', 'Top Right', [
	'Top Left', 'Top Right',
	'Bottom Left', 'Bottom Right'
]);

const myStyleTab = input.tab('Style');
const mySizeInput = myStyleTab.select('Text size', 'Large', ['Tiny', 'Small', 'Normal', 'Large', 'Huge']);
const myCustomTextColor = myStyleTab.color('Custom text color', '#ffffff');
const myBackgroundColor = myStyleTab.color('Background color', 'rgba(0,0,0,0)');
const myBorderColor = myStyleTab.color('Border color', 'rgba(128,128,128,0)');
const myBorderWidth = myStyleTab.number('Border width', 0, { min: 0, max: 5 });

// Maps the position selector onto the overlay's supported positions.
const myPositionMap = {
	'Top Left': 'top_left',
	'Top Right': 'top_right',
	'Bottom Left': 'bottom_left',
	'Bottom Right': 'bottom_right'
};

// Maps text size options to approximate font sizes (px), since the
// Custom JS API has no direct "size.*" concept like Pine Script.
const mySizeMap = {
	'Tiny': '10px',
	'Small': '12px',
	'Normal': '14px',
	'Large': '18px',
	'Huge': '24px'
};

// Builds the time format string, following Pine's logic exactly.
const myTimeFormat = myUse24Hour
	? (myShowSeconds ? 'HH:mm:ss' : 'HH:mm')
	: (myShowSeconds ? 'h:mm:ss A' : 'h:mm A');

const myNowFormatted = momentTz(current.now * 1000).tz(myTimeZone).format(myTimeFormat);

paint_overlay('ClockTable', { position: myPositionMap[myPositionInput] }, {
	rows: [{
		cells: [{
			text: myNowFormatted,
			color: myCustomTextColor,
			background_color: myBackgroundColor,
			border_color: myBorderColor,
			border_width: myBorderWidth,
			font_size: mySizeMap[mySizeInput],
			align: 'center'
		}]
	}]
});

// Dummy constant signal, since this indicator has no real market logic
// to scan/alert/backtest on. Kept so register_signal() usage is valid
// and consistent across all executions.
register_signal(series_of(true), 'Clock Active');