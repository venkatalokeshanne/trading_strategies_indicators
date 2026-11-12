<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Balloon Raindrop Painter');

// This is an experimental indicator based on the concept of Raindrop Candles
// and volume imbalance. It may not perfectly replicate TrendSpider's implementation
// and its effectiveness should be carefully evaluated before use in trading decisions.

const volumeThreshold = input.number('Volume Imbalance Threshold', 2, { min: 1.1, max: 10 });

// Helper function to calculate VWAP for a single candle
const calculateVWAP = (high, low, volume) => {
    const avgPrice = (high + low) / 2;
    return avgPrice * volume / volume;
};

// Calculate VWAP for each candle
const myVwap = for_every(high, low, volume, (h, l, v) => calculateVWAP(h, l, v));

// Calculate volume on the low and high side of each candle
const lowVolume = for_every(close, low, myVwap, volume, (c, l, v, vol) => 
    v > l ? vol * (v - l) / (c - l) : vol);
const highVolume = for_every(close, high, myVwap, volume, (c, h, v, vol) => 
    v < h ? vol * (h - v) / (h - c) : vol);

// Determine candle color based on volume imbalance
const candleColor = for_every(lowVolume, highVolume, (lv, hv) => {
    if (hv > lv * volumeThreshold) {
        return '#00FF00'; // Neon green for bullish balloon
    } else if (lv > hv * volumeThreshold) {
        return '#FF0000'; // Neon red for bearish balloon
    } else {
        return '#808080'; // Gray for neutral candles
    }
});

// Color the candles
color_candles(candleColor);

// Define bullish and bearish balloon signals
const bullishBalloon = for_every(lowVolume, highVolume, (lv, hv) => 
    hv > lv * volumeThreshold ? 1 : 0);
const bearishBalloon = for_every(lowVolume, highVolume, (lv, hv) => 
    lv > hv * volumeThreshold ? 1 : 0);

// Register signals for scanning and strategy testing
register_signal(bullishBalloon, 'Bullish Balloon');
register_signal(bearishBalloon, 'Bearish Balloon');</code>