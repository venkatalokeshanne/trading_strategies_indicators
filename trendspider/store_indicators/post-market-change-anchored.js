<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for informational purposes only.
describe_indicator('Post-Market Change % (Anchored)', 'lower', { shortName: 'PostM Change%', decimals: 'by_symbol_2x' });

// Define the pre-market open time (4:00 AM EST)
const preMarketOpenHour = 16;

// Series to store the percentage change from 4:00 AM open
const percentChangeSeries = series_of(null);

// Function to calculate percentage change
function calculatePercentageChange(currentPrice, openPrice) {
    return ((currentPrice - openPrice) / openPrice) * 100;
}

// Variables to track the pre-market open price and current day
let preMarketOpenPrice = null;
let anchorCandleFound = false; // To ensure the anchor is set correctly
let currentDay = null;

// Loop through all candles and calculate the percentage change from 4:00 AM open
for (let i = 0; i < time.length; i++) {
    const date = time_of(time[i]);
    const day = date.dayOfYear;

    // Reset at the start of each new day
    if (day !== currentDay) {
        currentDay = day;
        preMarketOpenPrice = null;
        anchorCandleFound = false; // Reset anchor flag for the new day
    }

    // Set the pre-market open price when the first candle at or after 4:00 AM appears
    if (!anchorCandleFound && date.hours >= preMarketOpenHour) {
        preMarketOpenPrice = close[i]; // Set pre-market open price
        anchorCandleFound = true; // Anchor found, no need to check further
    }

    // Calculate and store the percentage change if the pre-market open price is set
    if (preMarketOpenPrice !== null) {
        percentChangeSeries[i] = calculatePercentageChange(close[i], preMarketOpenPrice);
    } else {
        percentChangeSeries[i] = null; // No percentage change before 4:00 AM
    }
}

// Paint the percentage change as a line plot
paint(percentChangeSeries, { name: 'PostM Change %', color: '#ff0000', thickness: 2, style: 'line' });

// Paint a horizontal line at 0% level
paint(horizontal_line(0), 'Zero Level', 'black');


</code>