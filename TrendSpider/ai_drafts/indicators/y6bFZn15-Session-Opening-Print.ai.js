describe_indicator('Session Opening Print', 'price');

// NOTE: TrendSpider's time_of() always uses the exchange timezone of the
// current ticker; there is no way to force an arbitrary IANA timezone like
// in Pine's hour(time, tz). So the "Timezone" selector from the original
// script cannot be honored exactly - we always use the chart's exchange tz.
// (Shortened the input title below since the platform rejects overly long
// input names.)
const myTimezone = input.select('Timezone (info only)', 'America/New_York', [
	'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'UTC', 'Europe/London', 'Asia/Tokyo'
]);

const mySessionHour = input.number('Open Hour', 9, { min: 0, max: 23 });
const mySessionMinute = input.number('Open Minute', 30, { min: 0, max: 59 });
const myExtendRight = input.boolean('Extend Line to Right Edge', true);
const myShowLabel = input.boolean('Show Price Label', true);
const myNewLineEachDay = input.boolean('New Line Each Day', true);

// Build a sparse series which has the session open price on the bar
// matching the configured hour/minute, once per calendar day.
const myOpenPriceSparse = series_of(null);
const mySessionBarFlag = series_of(false);
let myLastSessionDay = null;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myIsSessionBar = myTimeInfo.hours === mySessionHour && myTimeInfo.minutes === mySessionMinute;
	const myCurrentDay = myTimeInfo.dayOfMonth;

	if (myIsSessionBar && (myLastSessionDay === null || myCurrentDay !== myLastSessionDay)) {
		myOpenPriceSparse[myIndex] = open[myIndex];
		mySessionBarFlag[myIndex] = true;
		myLastSessionDay = myCurrentDay;
	}
}

// "New Line Each Day" draws a stepped line that holds the open price
// constant until the next session's open (approximating Pine's rays).
// Unchecking it keeps a single persistent line that always carries the
// latest known open price forward - both are approximated here using
// constant interpolation since arbitrary multi-ray line objects (as in
// Pine's line.new per day) are not expressible in this API.
const myOpenPriceLine = myNewLineEachDay
	? interpolate_sparse_series(myOpenPriceSparse, 'constant')
	: interpolate_sparse_series(myOpenPriceSparse, 'constant');

const myLinePainted = paint(myOpenPriceLine, {
	name: 'SessionOpenPrint',
	color: 'yellow',
	thickness: 1,
	style: 'ladder'
});

// Place a label on the most recent known open price point, if enabled.
const myLastKnownIndex = (() => {
	for (let myIndex = myOpenPriceSparse.length - 1; myIndex >= 0; myIndex -= 1) {
		if (myOpenPriceSparse[myIndex] !== null) return myIndex;
	}
	return -1;
})();

if (myShowLabel && myLastKnownIndex >= 0) {
	paint_label_at_line(myLinePainted, myLastKnownIndex, 'Open', {
		color: 'yellow',
		background_color: 'rgba(255,255,0,0.15)',
		vertical_align: 'middle'
	});
}

// Expose the session-open-bar event for Scanners, Alerts and Strategies.
register_signal(mySessionBarFlag, 'Session Open Bar');