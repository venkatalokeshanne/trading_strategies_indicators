<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('EMA Crossover Candle Colors');

// Input parameters for EMA lengths
const fastLength = input.number('Fast EMA Length', 8, { min: 1 });
const slowLength = input.number('Slow EMA Length', 21, { min: 1 });

// Input parameters for candle colors
const bullishColor = input.color('Bullish Candle Color', 'green');
const bearishColor = input.color('Bearish Candle Color', 'red');
const neutralColor = input.color('Neutral Candle Color', 'gray');

// Calculate EMAs
const fastEMA = ema(close, fastLength);
const slowEMA = ema(close, slowLength);

// Register signals for strategy tester and market scanner
register_signal(for_every(fastEMA, slowEMA, (_fast, _slow) => _fast > _slow), 'Bullish');
register_signal(for_every(fastEMA, slowEMA, (_fast, _slow) => _fast < _slow), 'Bearish');

// Determine candle colors based on EMA crossover
const candleColors = for_every(fastEMA, slowEMA, (_fast, _slow) => {
    if (_fast > _slow) {
        return bullishColor;
    } else if (_fast < _slow) {
        return bearishColor;
    }
    return neutralColor; // Use neutral color if EMAs are equal
});

// Color the candles
color_candles(candleColors);

// Paint EMAs for reference
paint(fastEMA, { color: 'blue', name: `${fastLength} EMA` });
paint(slowEMA, { color: 'orange', name: `${slowLength} EMA` });</code>