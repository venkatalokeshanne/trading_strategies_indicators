<code x-ref="code" class="hljs" data-clipboard-text>// This indicator was made by AI and has not been QA checked by the TrendSpider development team. The indicator is for informational purposes only.
describe_indicator('MACD & RSI Based Momentum', 'price', {
    shortName: 'MACD RSI Momentum',
    warmup: 250, // Defines the warm-up period for this indicator
});

// Inputs for MACD and RSI lengths
const fastLength = input('MACD Fast Length', 12, { min: 1, max: 100 });
const slowLength = input('MACD Slow Length', 26, { min: 1, max: 100 });
const signalSmoothing = input('MACD Signal Length', 9, { min: 1, max: 100 });
const rsiLength = input('RSI Length', 14, { min: 1, max: 100 });

// MACD components
const fastMA = ema(close, fastLength);
const slowMA = ema(close, slowLength);
const macdLine = sub(fastMA, slowMA);
const signalLine = sma(macdLine, signalSmoothing);
const histogram = sub(macdLine, signalLine);

// RSI calculation
const rsiValues = rsi(close, rsiLength);

// Coloring logic
const candleColors = for_every(histogram, rsiValues, (hist, rsi) => {
    if (hist > 0 && rsi > 50) {
        return 'blue'; // Strong upward trend
    } else if (hist > 0 && rsi <= 50) {
        return 'lightblue'; // Upward trend losing strength
    } else if (hist < 0 && rsi < 50) {
        return 'red'; // Strong downward trend
    } else {
        return 'pink'; // Downward trend losing momentum
    }
});

// Applying the color to candles
color_candles(candleColors);

// Register signals for visual scripting
const strongUptrendSignal = for_every(histogram, rsiValues, (hist, rsi) => hist > 0 && rsi > 50);
const weakUptrendSignal = for_every(histogram, rsiValues, (hist, rsi) => hist > 0 && rsi <= 50);
const strongDowntrendSignal = for_every(histogram, rsiValues, (hist, rsi) => hist < 0 && rsi < 50);
const weakDowntrendSignal = for_every(histogram, rsiValues, (hist, rsi) => hist < 0 && rsi >= 50);

register_signal(strongUptrendSignal, 'Strong Uptrend');
register_signal(weakUptrendSignal, 'Weak Uptrend');
register_signal(strongDowntrendSignal, 'Strong Downtrend');
register_signal(weakDowntrendSignal, 'Weak Downtrend');



</code>