<code x-ref="code" class="hljs" data-clipboard-text>
describe_indicator('RSI with Seasonality', 'lower');

const moment = library('moment-timezone');

// Input parameters
const length = input.number('RSI Length', 14, { min: 1 });
const overboughtLevel = input.number('Overbought', 70, { min: 50, max: 100 });
const oversoldLevel = input.number('Oversold', 30, { min: 0, max: 50 });

// Fetch seasonality data
const seasonalityData = await request.seasonality(current.ticker, 'week_of_year', 'change');
assert(!seasonalityData.error, `Error fetching seasonality data: ${seasonalityData.error}`);

// Calculate RSI
const myRsi = rsi(close, length);

// Function to get seasonality data for a given week
const getSeasonalityForWeek = (weekNumber) => {
    const weekData = seasonalityData.dataByCategory[weekNumber];
    if (!weekData) return { winRate: 0, meanChange: 0 };
    
    const winRate = 100 * weekData.filter(record => record.value > 0).length / weekData.length;
    const meanChange = weekData.reduce((sum, record) => sum + record.value, 0) / weekData.length;
    
    return { winRate, meanChange };
};

// Function to get color based on win rate
const getColorForWinRate = (winRate) => {
    if (winRate > 65) return '#00FF00'; // Bright green
    if (winRate > 50) return '#008000'; // Green
    if (winRate > 35) return '#FF0000'; // Red
    return '#8B0000'; // Dark red
};

// Generate RSI color series
const rsiColor = for_every(time, (t, i) => {
    const weekNumber = moment(t * 1000).isoWeek();
    const { winRate } = getSeasonalityForWeek(weekNumber);
    return getColorForWinRate(winRate);
});

// Paint RSI
paint(myRsi, { style: 'line', color: rsiColor, name: 'RSI' });

// Paint overbought and oversold levels
paint(horizontal_line(overboughtLevel), { color: 'gray', style: 'dotted' });
paint(horizontal_line(oversoldLevel), { color: 'gray', style: 'dotted' });

// Current week info for overlay
const currentWeek = moment().isoWeek();
const { winRate, meanChange } = getSeasonalityForWeek(currentWeek);

// Paint overlay with current week info
paint_overlay('WeekInfo', { position: 'top_right' }, {
    rows: [{
        cells: [{
            text: `Week ${currentWeek} Win Rate: ${winRate.toFixed(2)}%`,
            color: getColorForWinRate(winRate)
        }]
    }, {
        cells: [{
            text: `Avg Weekly Change: ${(meanChange * 100).toFixed(2)}%`,
            color: meanChange > 0 ? 'green' : 'red'
        }]
    }]
});
</code>