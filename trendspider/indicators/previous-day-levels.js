<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Previous Day Levels');

// User-configurable inputs
const lookbackPeriod = input.number('Lookback Period', 1, { min: 1, max: 10 });
const highLineColor = input.color('High Line Color', '#39FF14'); // Neon green
const lowLineColor = input.color('Low Line Color', '#FF3131'); // Neon red
const midLineColor = input.color('50% Line Color', 'white');

// Updated inputs for line styles
const highLineStyle = input.select('High Line Style', 'line', ['line', 'dotted']);
const lowLineStyle = input.select('Low Line Style', 'line', ['line', 'dotted']);
const midLineStyle = input.select('50% Line Style', 'line', ['line', 'dotted']);

// New input for line thickness
const lineThickness = input.number('Line Thickness', 2, { min: 1, max: 5 });

// Fetch daily data
const dailyData = await request.history(current.ticker, 'D');
assert(!dailyData.error, `Error fetching daily data: ${dailyData.error}`);

// Initialize arrays for high, low, and mid levels
const highLevels = series_of(null);
const lowLevels = series_of(null);
const midLevels = series_of(null);

// Calculate levels for the specified lookback period
for (let i = 0; i < lookbackPeriod; i++) {
    const dailyIndex = dailyData.close.length - 2 - i; // -2 to get the previous completed day
    if (dailyIndex >= 0) {
        const prevDayHigh = dailyData.high[dailyIndex];
        const prevDayLow = dailyData.low[dailyIndex];
        const prevDayMid = (prevDayHigh + prevDayLow) / 2;
        
        // Find the corresponding index in the current timeframe
        const startIndex = time.findIndex(t => t >= dailyData.time[dailyIndex + 1]);
        
        if (startIndex !== -1) {
            for (let j = startIndex; j < time.length; j++) {
                highLevels[j] = prevDayHigh;
                lowLevels[j] = prevDayLow;
                midLevels[j] = prevDayMid;
            }
        }
    }
}

// Paint the levels with correct line style and thickness
paint(highLevels, { color: highLineColor, style: highLineStyle, name: 'Previous Day High', linewidth: lineThickness });
paint(lowLevels, { color: lowLineColor, style: lowLineStyle, name: 'Previous Day Low', linewidth: lineThickness });
paint(midLevels, { color: midLineColor, style: midLineStyle, name: 'Previous Day 50%', linewidth: lineThickness });</code>