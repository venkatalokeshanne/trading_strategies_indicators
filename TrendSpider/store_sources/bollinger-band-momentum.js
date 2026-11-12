<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Bollinger Band Momentum');

// This indicator combines Bollinger Bands and MACD histogram to generate
// momentum-based signals. It's an experimental approach and may not guarantee
// accurate trading signals. Please use with caution and always backtest
// before using in live trading.

// Bollinger Bands inputs
const bbPeriod = input.number('BB Period', 20, { min: 1 });
const bbDeviation = input.number('BB Deviation', 2, { min: 0.1, step: 0.1 });

// MACD inputs
const macdFastPeriod = input.number('MACD Fast Period', 12, { min: 1 });
const macdSlowPeriod = input.number('MACD Slow Period', 26, { min: 1 });
const macdSignalPeriod = input.number('MACD Signal Period', 9, { min: 1 });

// Color inputs
const bullishColor = input.color('Bullish Color', 'green');
const bearishColor = input.color('Bearish Color', 'red');
const neutralColor = input.color('Neutral Color', 'grey');

// Calculate Bollinger Bands
const bbMA = sma(close, bbPeriod);
const bbStdDev = stdev(close, bbPeriod);
const bbUpper = add(bbMA, mult(bbStdDev, bbDeviation));
const bbLower = sub(bbMA, mult(bbStdDev, bbDeviation));

// Calculate MACD
const macdFast = ema(close, macdFastPeriod);
const macdSlow = ema(close, macdSlowPeriod);
const macdLine = sub(macdFast, macdSlow);
const signalLine = ema(macdLine, macdSignalPeriod);
const macdHistogram = sub(macdLine, signalLine);

// Generate signals and color candles
const candleColors = for_every(close, bbUpper, bbLower, macdHistogram, (_close, _bbUpper, _bbLower, _macdHistogram) => {
    if (_close > _bbUpper && _macdHistogram > 0) {
        return bullishColor;
    } else if (_close < _bbLower && _macdHistogram < 0) {
        return bearishColor;
    } else {
        return neutralColor;
    }
});

// Paint candles
color_candles(candleColors);

// Register signals for potential use in alerts or further analysis
register_signal(for_every(close, bbUpper, macdHistogram, (_close, _bbUpper, _macdHistogram) => 
    _close > _bbUpper && _macdHistogram > 0), 'Bullish Signal');
register_signal(for_every(close, bbLower, macdHistogram, (_close, _bbLower, _macdHistogram) => 
    _close < _bbLower && _macdHistogram < 0), 'Bearish Signal');</code>