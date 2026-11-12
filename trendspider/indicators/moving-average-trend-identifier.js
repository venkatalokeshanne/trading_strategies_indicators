<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Moving Average Trend Identifier');

// Define the key moving averages
const lengths = [10, 20, 50, 100, 200];
const mas = lengths.map(length => sma(close, length));

// Function to check if a value is above all MAs
const isAboveAll = (value, maValues) => maValues.every(ma => value > ma);

// Function to check if a value is below all MAs
const isBelowAll = (value, maValues) => maValues.every(ma => value < ma);

// Compute the candle colors
const candleColors = for_every(open, close, (o, c, _, i) => {
    const maValues = mas.map(ma => ma[i]);
    if (isAboveAll(o, maValues) && isAboveAll(c, maValues)) {
        return '#2fcc56';
    } else if (isBelowAll(o, maValues) && isBelowAll(c, maValues)) {
        return 'red';
    } else {
        return 'grey';
    }
});

// Color the candles
color_candles(candleColors);

// Create signals for red, green, and grey candles
const greenSignal = for_every(candleColors, color => color === '#2fcc56' ? 1 : 0);
const redSignal = for_every(candleColors, color => color === 'red' ? 1 : 0);
const greySignal = for_every(candleColors, color => color === 'grey' ? 1 : 0);

register_signal(greenSignal, "Green Candle Signal");
register_signal(redSignal, "Red Candle Signal");
register_signal(greySignal, "Grey Candle Signal");
</code>