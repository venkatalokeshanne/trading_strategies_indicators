<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.
describe_indicator('Cumulative Intraday Volume', 'lower', { decimals: 'by_symbol_2x' });

// Define the regular market session times (9:30 am to 3:59 pm EST)
const marketStartHour = 9;
const marketStartMinute = 30;
const marketEndHour = 15;
const marketEndMinute = 59;

// Initialize the cumulative volume series
const cumulativeIntradayVolume = series_of(null);
let currentDay = null;
let dailyIntradayVolume = 0;

// Function to check if the current candle is in the regular market session
function isRegularMarket(date) {
    return (
        (date.hours > marketStartHour || (date.hours === marketStartHour && date.minutes >= marketStartMinute)) &&
        (date.hours < marketEndHour || (date.hours === marketEndHour && date.minutes <= marketEndMinute))
    );
}

// Loop through all candles and calculate cumulative volume during the regular market session
for (let i = 0; i < time.length; i++) {
    const date = time_of(time[i]);
    const day = date.dayOfYear;
    
    // If a new day starts, reset the daily intraday volume
    if (day !== currentDay) {
        currentDay = day;
        dailyIntradayVolume = 0; // Reset for the new day
    }
    
    // If the current candle is in the regular market session, accumulate volume
    if (isRegularMarket(date)) {
        dailyIntradayVolume += volume[i]; // Accumulate volume
    }
    
    // Hold the intraday cumulative volume for the remainder of the day
    cumulativeIntradayVolume[i] = dailyIntradayVolume;
}

// Paint the cumulative intraday volume as a histogram
paint(cumulativeIntradayVolume, { 
    name: 'Intraday Cumulative Vol',
    color: '#0000ff',
    thickness: 2,
    style: 'column' // This changes the visualization to a histogram
});
</code>