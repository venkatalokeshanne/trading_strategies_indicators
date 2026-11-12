<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator("Jerry McGuire");
// Define lengths for EMAs
const lengthShort = 8; // 8 period EMA
const lengthLong = 21; // 21 period EMA

// Calculate EMAs
const emaShort = ema(close, lengthShort);
const emaLong = ema(close, lengthLong);

// Define candle colors based on conditions
const candleColors = for_every(close, emaShort, emaLong, (price, shortEMA, longEMA) => {
    if (price > shortEMA && price > longEMA) {
        return 'green'; // Above both EMAs
    } else if (price > shortEMA && price < longEMA) {
        return 'yellow'; // Above 8EMA, below 21EMA
    } else if (price < shortEMA && price > longEMA) {
        return 'orange'; // Below 8EMA, above 21EMA
    } else if (price < shortEMA && price < longEMA) {
        return 'red'; // Below both EMAs
    } else {
        return null; // Default color if none of the conditions are met
    }
});

// Apply the color scheme to the candles
color_candles(candleColors);</code>