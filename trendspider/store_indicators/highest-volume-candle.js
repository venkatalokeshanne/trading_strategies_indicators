<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Highest Volume Candle');

// This indicator highlights the candle with the highest volume 
// in the last 50 candles by painting it yellow.

// Input for the lookback period
const lookback = input.number('Lookback Period', 50, { min: 1 });

// Function to find the index of the highest volume candle
const findHighestVolumeIndex = (volumeSeries, length) => {
    let maxVolume = -Infinity;
    let maxIndex = -1;
    
    for (let i = volumeSeries.length - length; i < volumeSeries.length; i++) {
        if (volumeSeries[i] > maxVolume) {
            maxVolume = volumeSeries[i];
            maxIndex = i;
        }
    }
    
    return maxIndex;
};

// Find the index of the highest volume candle
const highestVolumeIndex = findHighestVolumeIndex(volume, Math.min(lookback, volume.length));

// Create a series for coloring
const candleColors = for_every(close, (_c, _p, i) => 
    i === highestVolumeIndex ? 'yellow' : null);

// Color the candles
color_candles(candleColors);

// Add a label to the highest volume candle
paint_label_at_line(
    paint(close, { hidden: true }),
    highestVolumeIndex,
    'Highest Volume',
    { color: 'black', background_color: 'yellow' }
);

// Register a signal for the highest volume candle
const highestVolumeSignal = for_every(close, (_c, _p, i) => 
    i === highestVolumeIndex ? 1 : 0);

register_signal(highestVolumeSignal, 'Highest Volume Candle');</code>