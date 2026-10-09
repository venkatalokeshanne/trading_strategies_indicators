// This indicator reproduces the "Classic Big Clock" Pine Script, which simply
// shows the current real time (not candle time) in a floating table overlay.
// NOTE: this indicator has no actual trading logic (it just displays a live
// clock), so there is nothing meaningful to expose as scanner/strategy
// signals. See the flagged note below.
describe_indicator('Classic Big Clock');

const myMoment = library('moment-timezone');

// --- Appearance inputs ---
const myAppearanceTab = input.tab('Appearance');
const myPosition = myAppearanceTab.select('Position', 'Top Right', ['Top Right', 'Top Left', 'Bottom Right', 'Bottom Left']);
const mySize = myAppearanceTab.select('Clock Size', 'Huge', ['Huge', 'Large', 'Normal', 'Small']);
const myExtraPadding = myAppearanceTab.boolean('Enlarge Cell Frame (Make Huge Bigger)', true);

const myColorsRow = myAppearanceTab.row();
const myTextColor = myColorsRow.text('Text Color', '#F8FC04');
const myBgColor = myColorsRow.text('Background Color', 'rgba(0,0,0,0.6)');
const myFrameColor = myColorsRow.text('Border Color', 'gray');
const myFrameWidth = myAppearanceTab.number('Border Width (px)', 2, { min: 0, max: 10 });

// --- Timezone input ---
const myTimeTab = input.tab('Time Settings');
const myTimezoneOptions = [
	'Exchange', 'UTC-12', 'UTC-11', 'UTC-10 (HST)', 'UTC-9 (AKST)', 'UTC-8 (PST)', 'UTC-7 (MST)',
	'UTC-6 (CST)', 'UTC-5 (EST)', 'UTC-4 (AST)', 'UTC-3 (BRT)', 'UTC-2', 'UTC-1',
	'UTC', 'UTC+1 (CET)', 'UTC+2 (EET)', 'UTC+3 (MSK)', 'UTC+4 (GST)', 'UTC+5 (PKT)',
	'UTC+5:30 (IST)', 'UTC+6 (BST)', 'UTC+7 (ICT)', 'UTC+8 (SGT/HKT)', 'UTC+9 (JST)',
	'UTC+10 (AEST)', 'UTC+11', 'UTC+12 (NZST)', 'UTC+13', 'UTC+14'
];
const myTzInput = myTimeTab.select('Timezone', 'Exchange', myTimezoneOptions);

// map the Pine timezone options to IANA timezone names used by moment-timezone
const myTzMap = {
	'Exchange': null, // resolved to exchange session timezone below
	'UTC-12': 'Etc/GMT+12',
	'UTC-11': 'Etc/GMT+11',
	'UTC-10 (HST)': 'Pacific/Honolulu',
	'UTC-9 (AKST)': 'America/Anchorage',
	'UTC-8 (PST)': 'America/Los_Angeles',
	'UTC-7 (MST)': 'America/Denver',
	'UTC-6 (CST)': 'America/Chicago',
	'UTC-5 (EST)': 'America/New_York',
	'UTC-4 (AST)': 'America/Halifax',
	'UTC-3 (BRT)': 'America/Sao_Paulo',
	'UTC-2': 'Etc/GMT+2',
	'UTC-1': 'Etc/GMT+1',
	'UTC': 'UTC',
	'UTC+1 (CET)': 'Europe/Belgrade',
	'UTC+2 (EET)': 'Europe/Athens',
	'UTC+3 (MSK)': 'Europe/Moscow',
	'UTC+4 (GST)': 'Asia/Dubai',
	'UTC+5 (PKT)': 'Asia/Karachi',
	'UTC+5:30 (IST)': 'Asia/Kolkata',
	'UTC+6 (BST)': 'Asia/Dhaka',
	'UTC+7 (ICT)': 'Asia/Bangkok',
	'UTC+8 (SGT/HKT)': 'Asia/Singapore',
	'UTC+9 (JST)': 'Asia/Tokyo',
	'UTC+10 (AEST)': 'Australia/Sydney',
	'UTC+11': 'Pacific/Noumea',
	'UTC+12 (NZST)': 'Pacific/Auckland',
	'UTC+13': 'Pacific/Tongatapu',
	'UTC+14': 'Pacific/Kiritimati'
};

const myResolvedTz = myTzMap[myTzInput] || current.session.timezone;

// current.now gives the real "now" server time, equivalent to Pine's timenow
const myNowMoment = myMoment.tz(current.now * 1000, myResolvedTz);
const myTimeString = myNowMoment.format('HH:mm:ss');

// map "position" input to the overlay position option
const myPositionMap = {
	'Top Right': 'top_right',
	'Top Left': 'top_left',
	'Bottom Right': 'bottom_right',
	'Bottom Left': 'bottom_left'
};

// map "size" input to a font size (px), approximating TradingView's size.* options
const mySizeMap = {
	'Huge': 32,
	'Large': 24,
	'Normal': 16,
	'Small': 12
};

const myFontSize = mySizeMap[mySize];
const myCellPaddingY = (myExtraPadding && mySize === 'Huge') ? 32 : 8;
const myCellPaddingX = (myExtraPadding && mySize === 'Huge') ? 48 : 8;

paint_overlay('ClockTable', { position: myPositionMap[myPosition] }, {
	rows: [{
		cells: [{
			text: myTimeString,
			color: myTextColor,
			background_color: myBgColor,
			border_color: myFrameColor,
			border_width: myFrameWidth,
			font_size: myFontSize,
			padding_top: myCellPaddingY,
			padding_bottom: myCellPaddingY,
			padding_left: myCellPaddingX,
			padding_right: myCellPaddingX
		}]
	}]
});

// This indicator is purely a visual clock widget and has no trading
// condition in the original Pine script, so there is no meaningful
// true/false signal to register for scanners/alerts/strategies.
// We register a constant "false" signal so the indicator remains
// loadable in Visual Script contexts without implying false signals.
const myNoSignal = series_of(false);
register_signal(myNoSignal, 'Clock Tick (always false, no real signal)');