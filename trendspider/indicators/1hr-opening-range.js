<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for entertainment purposes only.

describe_indicator('1hr Opening Range High and Low', 'price', { shortName: 'ORHL' });

// Ensure the indicator does not work on Session, Daily, Weekly, Monthly, Quarterly, or Yearly charts
assert(
    !['D','W', 'M', 'Q', 'Y'].includes(constants.resolution),
    `not applicable to "${constants.resolution}" charts`
);

// Define NYSE market hours
const nyseStartHour = 9; // 09:00 NY time
const nyseStartMinute = 30;
const openingRangeEndHour = 10; // 10:30 NY time
const openingRangeEndMinute = 30;

// Function to get opening range high and low for each day
function getOpeningRangeHighLow() {
    const openingRangeHighs = series_of(null);
    const openingRangeLows = series_of(null);
    let currentDay = null;
    let openingRangeHigh = -Infinity;
    let openingRangeLow = Infinity;

    for (let i = 0; i < time.length; i++) {
        const date = time_of(time[i]);
        const day = date.dayOfYear;

        if (day !== currentDay) {
            currentDay = day;
            openingRangeHigh = -Infinity;
            openingRangeLow = Infinity;
        }

        if ((date.hours > nyseStartHour || (date.hours === nyseStartHour && date.minutes >= nyseStartMinute)) &&
            (date.hours < openingRangeEndHour || (date.hours === openingRangeEndHour && date.minutes <= openingRangeEndMinute))) {
            if (high[i] > openingRangeHigh) {
                openingRangeHigh = high[i];
            }
            if (low[i] < openingRangeLow) {
                openingRangeLow = low[i];
            }
        }

        openingRangeHighs[i] = openingRangeHigh;
        openingRangeLows[i] = openingRangeLow;
    }
    return { openingRangeHighs, openingRangeLows };
}

// Get the opening range high and low series
const { openingRangeHighs, openingRangeLows } = getOpeningRangeHighLow();

// Paint the opening range high and low on the chart
paint(openingRangeHighs, { style: 'line', color: 'red', thickness: 2, name: 'ORBH' });
paint(openingRangeLows, { style: 'line', color: 'blue', thickness: 2, name: 'ORBL' });</code>