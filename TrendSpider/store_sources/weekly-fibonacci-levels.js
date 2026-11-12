<code x-ref="code" class="hljs" data-clipboard-text>// This indicator code was generated using AI. It was not checked by Quality Assurance
// and did not pass any quality assurance processes that we normally would use at TrendSpider
// As a result, we can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.
describe_indicator('Weekly Fibonacci Levels', 'price', { shortName: 'WeeklyFibEdges', decimals: 2 });

const showEdges = input.boolean('Show Edges', true);
const showLabels = input.boolean('Show Labels', true);
const moment = library('moment-timezone');

// Function to get weekly OHLC data
const getWeeklyData = async () => {
    const weeklyData = await request.history(current.ticker, 'W');
    assert(!weeklyData.error, `Error fetching weekly data: ${weeklyData.error}`);
    return weeklyData;
};

// Get weekly data
const weeklyData = await getWeeklyData();

// Function to calculate Fibonacci levels
const calculateFibLevels = (high, low) => {
    const range = high - low;
    return {
        level161: high + range * 0.618,
        level138: high + range * 0.382,
        level100: high,
        level786: low + range * 0.786,
        level618: low + range * 0.618,
        level50: low + range * 0.5,
        level236: low + range * 0.236,
        level0: low
    };
};

// Function to get the last completed week's high and low
const getLastCompletedWeekHighLow = (currentTime) => {
    const currentWeekStart = moment(currentTime * 1000).startOf('week').unix();
    let lastCompletedWeekIndex = weeklyData.time.length - 1;
    while (lastCompletedWeekIndex >= 0 && weeklyData.time[lastCompletedWeekIndex] >= currentWeekStart) {
        lastCompletedWeekIndex--;
    }
    return {
        high: weeklyData.high[lastCompletedWeekIndex],
        low: weeklyData.low[lastCompletedWeekIndex]
    };
};

// Initialize series for each Fibonacci level
const myLevel161 = series_of(null);
const myLevel138 = series_of(null);
const myLevel100 = series_of(null);
const myLevel786 = series_of(null);
const myLevel618 = series_of(null);
const myLevel50 = series_of(null);
const myLevel236 = series_of(null);
const myLevel0 = series_of(null);

// Calculate and update Fibonacci levels for each candle
let currentWeekStart = 0;
for (let i = 0; i < time.length; i++) {
    const candleWeekStart = moment(time[i] * 1000).startOf('week').unix();
    
    if (candleWeekStart !== currentWeekStart) {
        // New week started, recalculate levels
        currentWeekStart = candleWeekStart;
        const { high: lastWeekHigh, low: lastWeekLow } = getLastCompletedWeekHighLow(time[i]);
        const currentWeekFibLevels = calculateFibLevels(lastWeekHigh, lastWeekLow);
        
        myLevel161[i] = currentWeekFibLevels.level161;
        myLevel138[i] = currentWeekFibLevels.level138;
        myLevel100[i] = currentWeekFibLevels.level100;
        myLevel786[i] = currentWeekFibLevels.level786;
        myLevel618[i] = currentWeekFibLevels.level618;
        myLevel50[i] = currentWeekFibLevels.level50;
        myLevel236[i] = currentWeekFibLevels.level236;
        myLevel0[i] = currentWeekFibLevels.level0;
        
        // Log weekly high, low, and Fibonacci values
        console.log(`Weekly High: ${lastWeekHigh}, Low: ${lastWeekLow}, Fib 161.8%: ${currentWeekFibLevels.level161}, Fib 138.2%: ${currentWeekFibLevels.level138}, Fib 100%: ${currentWeekFibLevels.level100}, Fib 78.6%: ${currentWeekFibLevels.level786}, Fib 61.8%: ${currentWeekFibLevels.level618}, Fib 50%: ${currentWeekFibLevels.level50}, Fib 23.6%: ${currentWeekFibLevels.level236}, Fib 0%: ${currentWeekFibLevels.level0}`);
    } else {
        // Within the same week, use the same levels
        myLevel161[i] = myLevel161[i - 1];
        myLevel138[i] = myLevel138[i - 1];
        myLevel100[i] = myLevel100[i - 1];
        myLevel786[i] = myLevel786[i - 1];
        myLevel618[i] = myLevel618[i - 1];
        myLevel50[i] = myLevel50[i - 1];
        myLevel236[i] = myLevel236[i - 1];
        myLevel0[i] = myLevel0[i - 1];
    }
    
    // If it's the last candle of the week, set levels to null to create a gap
    if (i < time.length - 1) {
        const nextCandleWeekStart = moment(time[i + 1] * 1000).startOf('week').unix();
        if (nextCandleWeekStart !== currentWeekStart) {
            myLevel161[i] = null;
            myLevel138[i] = null;
            myLevel100[i] = null;
            myLevel786[i] = null;
            myLevel618[i] = null;
            myLevel50[i] = null;
            myLevel236[i] = null;
            myLevel0[i] = null;
        }
    }
}

// Paint the edges
if (showEdges) {
    const level161 = paint(myLevel161, { name: '161.8% Extension', color: 'purple', style: 'line' });
    const level138 = paint(myLevel138, { name: '138.2% Extension', color: 'blue', style: 'line' });
    const level100 = paint(myLevel100, { name: '100% Retracement', color: 'white', style: 'line' });
    const level786 = paint(myLevel786, { name: '78.6% Retracement', color: 'green', style: 'line' });
    const level618 = paint(myLevel618, { name: '61.8% Retracement', color: 'orange', style: 'line' });
    const level50 = paint(myLevel50, { name: '50% Retracement', color: 'yellow', style: 'line' });
    const level236 = paint(myLevel236, { name: '23.6% Retracement', color: 'red', style: 'line' });
    const level0 = paint(myLevel0, { name: '0% Retracement', color: 'white', style: 'line' });

    // Add labels for each level
    if (showLabels) {
        paint_label_at_line(level161, close.length - 1, '161.8%', { color: 'purple', vertical_align: 'top' });
        paint_label_at_line(level138, close.length - 1, '138.2%', { color: 'blue', vertical_align: 'top' });
        paint_label_at_line(level100, close.length - 1, '100%', { color: 'white', vertical_align: 'top' });
        paint_label_at_line(level786, close.length - 1, '78.6%', { color: 'green', vertical_align: 'top' });
        paint_label_at_line(level618, close.length - 1, '61.8%', { color: 'orange', vertical_align: 'top' });
        paint_label_at_line(level50, close.length - 1, '50%', { color: 'yellow', vertical_align: 'top' });
        paint_label_at_line(level236, close.length - 1, '23.6%', { color: 'red', vertical_align: 'top' });
        paint_label_at_line(level0, close.length - 1, '0%', { color: 'white', vertical_align: 'top' });
    }
}

// Register signals for each level
register_signal(for_every(close, myLevel161, (c, l) => c > l), 'Price above 161.8% level');
register_signal(for_every(close, myLevel138, (c, l) => c > l), 'Price above 138.2% level');
register_signal(for_every(close, myLevel100, (c, l) => c > l), 'Price above 100% level');
register_signal(for_every(close, myLevel786, (c, l) => c > l), 'Price above 78.6% level');
register_signal(for_every(close, myLevel618, (c, l) => c > l), 'Price above 61.8% level');
register_signal(for_every(close, myLevel50, (c, l) => c > l), 'Price above 50% level');
register_signal(for_every(close, myLevel236, (c, l) => c > l), 'Price above 23.6% level');
register_signal(for_every(close, myLevel0, (c, l) => c > l), 'Price above 0% level');
</code>