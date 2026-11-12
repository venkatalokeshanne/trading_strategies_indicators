<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Seasonality Moving Average');

const maLength = input.number('MA Length', 20, { min: 1 });
const maType = input.select('MA Type', 'sma', constants.ma_types);
const computeMA = indicators[maType];

const ma = computeMA(close, maLength);

// Import the moment library
const moment = library('moment-timezone');

// Fetch weekly seasonality data
const seasonalityData = await request.seasonality(current.ticker, 'week_of_year', 'change');
assert(!seasonalityData.error, `Error fetching seasonality data: ${seasonalityData.error}`);

// Calculate win rate percentage for each week
const weeklyWinRates = seasonalityData.categories.map(week => {
    const weekData = seasonalityData.dataByCategory[week];
    const winCount = weekData.filter(d => d.value > 0).length;
    return (winCount / weekData.length) * 100;
});

// Function to get color based on win rate
const getColor = (winRate) => {
    if (winRate >= 75) return '#00FF00'; // Bright green
    if (winRate >= 51) return '#008000'; // Green
    if (winRate >= 25) return '#FF0000'; // Red
    return '#FF00FF'; // Bright red
};

// Map each candle to its corresponding week and color
const myColor = for_every(time, (_t) => {
    const weekOfYear = moment(_t * 1000).week() - 1; // Moment weeks are 1-indexed
    const winRate = weeklyWinRates[weekOfYear];
    return getColor(winRate);
});

paint(ma, { name: 'MA', color: myColor });

// Add a comment explaining the color coding
paint_label_at_line(
    paint(series_of(null), { hidden: true }),
    close.length - 1,
    "MA Color Legend:n≥75%: Bright Greenn51-74%: Greenn25-50%: Redn<25%: Bright Red",
    { vertical_align: 'top' }
);</code>