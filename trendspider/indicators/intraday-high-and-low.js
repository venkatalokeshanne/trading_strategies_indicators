<code x-ref="code" class="hljs" data-clipboard-text>// This script was generated using AI. It has not been quality assured and should be used for informational purposes only.
describe_indicator('Intraday High and Low', 'price', { shortName: 'Intraday High/Low' });

// Define NYSE market hours
const nyseStartHour = 9; // 09:00 NY time
const nyseStartMinute = 30;
const nyseEndHour = 16; // 16:00 NY time
const nyseEndMinute = 0;

// Function to get intraday high and low for each day
function getIntradayHighLow() {
    const intradayLows = series_of(null);
    const intradayHighs = series_of(null);
    let currentDay = null;
    let intradayLow = Infinity;
    let intradayHigh = -Infinity;

    for (let i = 0; i < time.length; i++) {
        const date = time_of(time[i]);
        const day = date.dayOfYear;

        if (day !== currentDay) {
            currentDay = day;
            intradayLow = Infinity;
            intradayHigh = -Infinity;
        }

        if ((date.hours > nyseStartHour || (date.hours === nyseStartHour && date.minutes >= nyseStartMinute)) &&
            (date.hours < nyseEndHour || (date.hours === nyseEndHour && date.minutes <= nyseEndMinute))) {
            if (low[i] < intradayLow) {
                intradayLow = low[i];
            }
            if (high[i] > intradayHigh) {
                intradayHigh = high[i];
            }
        }

        intradayLows[i] = intradayLow;
        intradayHighs[i] = intradayHigh;
    }
    return { intradayLows, intradayHighs };
}

// Get the intraday high and low series
const { intradayLows, intradayHighs } = getIntradayHighLow();

// Paint the intraday low and intraday high
paint(intradayLows, { style: 'line', color: 'red', thickness: 2, name: 'Intraday Low' });
paint(intradayHighs, { style: 'line', color: 'green', thickness: 2, name: 'Intraday High' });
</code>