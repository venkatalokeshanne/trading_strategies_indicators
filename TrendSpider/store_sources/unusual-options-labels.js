<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was generated using AI. Please note that it has not passed any formal QA process.
// Use it for informational purposes only.

describe_indicator('Unusual Options Labels', 'price');

// Minimum cost basis to filter out small trades
const minimumCostBasis = input.number('Minimum Cost Basis', 100000);

async function fetchUnusualOptionsData() {
    try {
        // Fetch unusual options data
        const optionsData = await request.unusual_options(constants.ticker);
        if (!optionsData || optionsData.length === 0) {
            return {
                bullishSignals: Array(close.length).fill(null),
                bearishSignals: Array(close.length).fill(null),
                neutralSignals: Array(close.length).fill(null)
            }; // No data available
        }

        // Separate the trades by their tags (bullish, bearish, neutral)
        const bullishTrades = optionsData.filter(trade => trade.tags.includes('bullish') && trade.costBasis > minimumCostBasis);
        const bearishTrades = optionsData.filter(trade => trade.tags.includes('bearish') && trade.costBasis > minimumCostBasis);
        const neutralTrades = optionsData.filter(trade => trade.tags.includes('neutral') && trade.costBasis > minimumCostBasis);

        // Land the signals onto the current candles
        const bullishSignals = land_points_onto_series(
            bullishTrades.map(item => item.timestamp),
            bullishTrades.map(() => 'Bullish'),
            time,
            'ge'
        );

        const bearishSignals = land_points_onto_series(
            bearishTrades.map(item => item.timestamp),
            bearishTrades.map(() => 'Bearish'),
            time,
            'ge'
        );

        const neutralSignals = land_points_onto_series(
            neutralTrades.map(item => item.timestamp),
            neutralTrades.map(() => 'Neutral'),
            time,
            'ge'
        );

        return { bullishSignals, bearishSignals, neutralSignals };

    } catch (error) {
        console.error("Error fetching or processing data:", error);
        return {
            bullishSignals: Array(close.length).fill(null),
            bearishSignals: Array(close.length).fill(null),
            neutralSignals: Array(close.length).fill(null)
        }; // Return empty series in case of error
    }
}

// Fetch the unusual options sentiment data
const { bullishSignals, bearishSignals, neutralSignals } = await fetchUnusualOptionsData();

// Paint the labels on the chart
paint(bullishSignals, {
    style: 'labels_above',
    color: 'green',
    backgroundColor: 'green',
    backgroundBorderRadius: 3,
    name: 'Bullish Signal'
});

paint(bearishSignals, {
    style: 'labels_below',
    color: 'red',
    backgroundColor: 'red',
    backgroundBorderRadius: 3,
    name: 'Bearish Signal'
});

paint(neutralSignals, {
    style: 'labels_above',
    color: 'gray',
    backgroundColor: 'gray',
    backgroundBorderRadius: 3,
    name: 'Neutral Signal'
});

// Register the signals for visual scripting
const buySignal = bullishSignals.map(signal => signal === 'Bullish');
const sellSignal = bearishSignals.map(signal => signal === 'Bearish');
const neutralSignal = neutralSignals.map(signal => signal === 'Neutral');

// Register for alerts or visual scripting usage
register_signal(buySignal, 'Bullish Unusual Options');
register_signal(sellSignal, 'Bearish Unusual Options');
register_signal(neutralSignal, 'Neutral Unusual Options');
</code>