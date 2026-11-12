<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator("Range Close Coloring");

// This indicator colors candles based on their proximity to their high
// It's an experimental approach and may need adjustments based on specific needs

// Input for the threshold percentage
const myThresholdPercent = input.number("Threshold %", 25, { min: 0, max: 100 });

// Input for the candle color
const myCandleColor = input.color("Candle Color", "yellow");

// Calculate the threshold as a decimal
const myThreshold = myThresholdPercent / 100;

// Calculate the difference between close and high as a percentage of the candle range
const myCloseToHighRatio = for_every(high, low, close, (_h, _l, _c) => {
    const myCandleRange = _h - _l;
    if (myCandleRange === 0) return 0; // Avoid division by zero
    return (_h - _c) / myCandleRange;
});

// Create a color series based on the ratio
const myColors = for_every(myCloseToHighRatio, _ratio => 
    _ratio <= myThreshold ? myCandleColor : null);

// Color the candles
color_candles(myColors);

// Create a signal for candles meeting the criteria
const mySignal = for_every(myCloseToHighRatio, _ratio => _ratio <= myThreshold);

// Register the signal
register_signal(mySignal, "Close Near High");</code>