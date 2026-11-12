<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('RSI, MACD Confluence');

// Input parameters
const rsiLength = input.number('RSI Length', 14, { min: 1 });
const macdFastLength = input.number('MACD Fast Length', 12, { min: 1 });
const macdSlowLength = input.number('MACD Slow Length', 26, { min: 1 });
const macdSignalLength = input.number('MACD Signal Length', 9, { min: 1 });

// Calculate RSI
const myRsi = rsi(close, rsiLength);

// Calculate MACD
const myMacdLine = sub(ema(close, macdFastLength), ema(close, macdSlowLength));
const mySignalLine = ema(myMacdLine, macdSignalLength);
const myHistogram = sub(myMacdLine, mySignalLine);

// Define conditions
const rsiCondition = for_every(myRsi, r => r > 50);
const macdOverSignalCondition = for_every(myMacdLine, mySignalLine, (m, s) => m > s);

// Combine conditions and determine candle colors
const candleColors = for_every(
    rsiCondition,
    macdOverSignalCondition,
    (rsi, macdSignal) => {
        const trueCount = [rsi, macdSignal].filter(Boolean).length;
        if (trueCount === 2) return '#2fcc56';
        if (trueCount > 0) return 'lightgray';
        return 'red';
    }
);

// Color the candles
color_candles(candleColors);

// Register signals for scanner and strategy tester
register_signal(
    for_every(candleColors, c => c === '#2fcc56'),
    "Strong Bullish (Green)"
);

register_signal(
    for_every(candleColors, c => c === 'lightgray'),
    "Neutral (Gray)"
);

register_signal(
    for_every(candleColors, c => c === 'red'),
    "Bearish (Red)"
);</code>