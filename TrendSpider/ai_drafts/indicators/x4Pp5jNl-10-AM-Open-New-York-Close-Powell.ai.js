describe_indicator('10 AM Open to New York Close', 'price');

// NOTE: TrendSpider's time_of() always uses the EXCHANGE time zone of
// the current symbol, there is no way to force an arbitrary time zone
// (like "America/New_York") the way Pine's timestamp()/time_of() with a
// TZ argument does. For US equities this is normally the same thing,
// but for symbols on other exchanges results will differ from the
// original Pine script. This is a platform limitation.

const myOpenHour = input.number('Open Hour', 10, { min: 0, max: 23 });
const myOpenMinute = input.number('Open Minute', 0, { min: 0, max: 59 });
const myCloseHour = input.number('NY Close Hour', 16, { min: 0, max: 23 });
const myCloseMinute = input.number('NY Close Minute', 0, { min: 0, max: 59 });

const myShowMarker = input.boolean('Show 10 AM Marker', true);
const myShowLabel = input.boolean('Show 10 AM Label', true);

const myLineSeries = series_of(null);
const myMarkerSeries = series_of(null);
const myIs10AMSignal = series_of(false);
const myIsCloseSignal = series_of(false);

let myActiveOpenValue = null;
let myActiveDay = null;

for (let myIndex = 0; myIndex < time.length; myIndex += 1) {
	const myTimeInfo = time_of(time[myIndex]);
	const myDayKey = `${myTimeInfo.year}-${myTimeInfo.dayOfYear}`;

	// reset the active session whenever a new day starts
	if (myActiveDay !== myDayKey && myActiveOpenValue !== null) {
		myActiveOpenValue = null;
	}

	const myIs10AM = myTimeInfo.hours === myOpenHour && myTimeInfo.minutes === myOpenMinute;
	const myIsCloseTime = myTimeInfo.hours === myCloseHour && myTimeInfo.minutes === myCloseMinute;

	myIs10AMSignal[myIndex] = myIs10AM;
	myIsCloseSignal[myIndex] = myIsCloseTime;

	if (myIs10AM) {
		myActiveOpenValue = open[myIndex];
		myActiveDay = myDayKey;
	}

	if (myActiveOpenValue !== null && myActiveDay === myDayKey) {
		myLineSeries[myIndex] = myActiveOpenValue;
	}

	if (myShowMarker && myIs10AM) {
		myMarkerSeries[myIndex] = open[myIndex];
	}

	// stop extending the line right after the close bar of the same session
	if (myIsCloseTime) {
		myActiveOpenValue = null;
	}
}

const myLinePainted = paint(myLineSeries, { name: 'Ten AM Open', color: 'orange', thickness: 2, style: 'ladder' });
paint(myMarkerSeries, { name: 'Ten AM Marker', color: 'orange', thickness: 6, style: 'line' });

if (myShowLabel) {
	const myPoints = indexed_points_of(myMarkerSeries);
	for (const myPoint of myPoints) {
		paint_label_at_line(myLinePainted, myPoint.candleIndex, 'Ten AM Open', {
			color: 'orange',
			vertical_align: 'top'
		});
	}
}

register_signal(myIs10AMSignal, 'Ten AM Open Bar');
register_signal(myIsCloseSignal, 'NY Close Bar');