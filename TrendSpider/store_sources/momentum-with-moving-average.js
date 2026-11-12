<code x-ref="code" class="hljs" data-clipboard-text>// This was generated with AI and did not pass any quality assurance processes used at TrendSpider
// As a result, I can’t guarantee that it will operate as expected in all cases and you should
// use caution when using this indicator. Consider it for informational purposes only.

// Define the Momentum with Custom Moving Average Indicator
describe_indicator('Momentum with Custom Moving Average', 'lower', {
    shortName: 'MoMA',
    decimals: 2
});

// Input parameters for the Momentum, Moving Average, and Price Source
const momentumLength = input.number('Momentum Length', 14, { min: 1, max: 100 });
const maType = input('MA type', 'sma', constants.ma_types); // Dynamically get all available MA types
const priceSource = input('Price Source', 'close', constants.price_source_options); // Dynamically get available price sources
const maLength = input.number('Moving Average Length', 20, { min: 1, max: 100 });

// Get the selected price source
const priceData = prices[priceSource];

// Calculate the Momentum based on the selected price source
const momentumValues = priceData.map((value, index) => {
    if (index < momentumLength) return null;
    return value - priceData[index - momentumLength];
});

// Function to calculate different types of moving averages
function calculateMA(data, length, type) {
    let maValues = [];
    switch (type) {
        case 'ema':
            maValues = ema(data, length);
            break;
        case 'wma':
            maValues = wma(data, length);
            break;
        default:
            maValues = sma(data, length);
            break;
    }
    return maValues;
}

// Calculate the selected Moving Average on Momentum
const maValues = calculateMA(momentumValues, maLength, maType);

// Paint the Momentum line (Green color)
const paintedMomentum = paint(momentumValues, {
    name: 'Momentum',
    color: 'green',
    thickness: 2
});

// Paint the Moving Average line (Black color)
const paintedMA = paint(maValues, {
    name: 'MA',
    color: 'black',
    thickness: 2
});

// Use color_cloud to fill green when MA < Momentum and red when MA > Momentum
color_cloud(
    maValues,
    momentumValues,
    'red',  // Fill green when MA < Momentum
    'green'     // Fill red when MA > Momentum
);

</code>