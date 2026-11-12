<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volatility Stop Multi-Timeframe');

// Input for Volatility Stop calculation
const length = input.number('ATR Length', 14, { min: 1 });
const multiplier = input.number('ATR Multiplier', 3, { min: 0.1 });

// Function to calculate Volatility Stop
const calculateVolatilityStop = async (resolution) => {
    const data = await request.history(current.ticker, resolution);
    assert(!data.error, `Error fetching ${resolution} data: ${data.error}`);
    
    const atrData = atr(data.high, data.low, data.close, length);
    const highestHigh = highest(data.high, length);
    const lowestLow = lowest(data.low, length);
    
    const volatilityStop = for_every(
        data.close, atrData, highestHigh, lowestLow,
        (c, a, h, l) => c > h - multiplier * a ? h - multiplier * a : l + multiplier * a
    );
    
    return land_points_onto_series(data.time, volatilityStop, time, 'ge');
};

// Calculate Volatility Stop for different timeframes
const dailyStop = await calculateVolatilityStop('D');
const weeklyStop = await calculateVolatilityStop('W');
const monthlyStop = await calculateVolatilityStop('M');

// Interpolate the landed data
const dailyStopInterpolated = interpolate_sparse_series(dailyStop, 'constant');
const weeklyStopInterpolated = interpolate_sparse_series(weeklyStop, 'constant');
const monthlyStopInterpolated = interpolate_sparse_series(monthlyStop, 'constant');

// Determine candle colors
const candleColors = for_every(
    close, dailyStopInterpolated, weeklyStopInterpolated, monthlyStopInterpolated,
    (c, d, w, m) => c > d && c > w && c > m ? 'green' : 'violet'
);

// Color the candles
color_candles(candleColors);

// Paint the Volatility Stop lines
paint(dailyStopInterpolated, { name: 'Daily Volatility Stop', color: 'blue' });
paint(weeklyStopInterpolated, { name: 'Weekly Volatility Stop', color: 'orange' });
paint(monthlyStopInterpolated, { name: 'Monthly Volatility Stop', color: 'red' });
</code>