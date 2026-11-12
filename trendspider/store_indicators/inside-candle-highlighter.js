<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Inside Candle Highlighter', 'candles');

// Define color for inside candles
const COLOR_INSIDE = 'blue'; // Blue for all inside candles

// Series to store inside candle conditions
const isInsideCandle = series_of(false);
const candleColors = series_of(null);

// Loop through each candle to check for inside candle conditions
for (let i = 1; i < close.length; i++) {
    if (high[i] < high[i - 1] && low[i] > low[i - 1]) { // Inside candle condition
        isInsideCandle[i] = true;
        candleColors[i] = COLOR_INSIDE;
    }
}

// Apply the colors to the candles
color_candles(candleColors);

// Register signal for scanning and alerts
register_signal(isInsideCandle, 'Inside Candle');
</code>