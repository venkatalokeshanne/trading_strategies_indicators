<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Distance between MAs', 'lower', { warmup: 250 });

const maType = input('MA type', 'sma', constants.ma_types);
const priceSource = input('Price', 'close', constants.price_source_options);

// Define the lengths of the moving averages
const length1 = input("Length 1", 20, { min: 1, max: 200 });
const length2 = input("Length 2", 50, { min: 1, max: 200 });

// Calculate the moving averages
const ma1 = indicators[maType](prices[priceSource], length1);
const ma2 = indicators[maType](prices[priceSource], length2);

// Calculate the distance between the two moving averages
const distance = for_every(ma1, ma2, (ma1, ma2) => ma1 - ma2);

// Paint the distance as a histogram
paint(distance, {
    style: 'histogram',
    color: for_every(distance, d => d > 0 ? 'green' : 'red')
});
</code>