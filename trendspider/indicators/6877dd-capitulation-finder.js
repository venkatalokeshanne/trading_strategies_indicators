<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Capitulation Finder');

// Input parameters
const rsiLength = input.number('RSI Length', 14, { min: 1 });
const rsiOversold = input.number('RSI Oversold Level', 30, { min: 1, max: 100 });
const rsiOverbought = input.number('RSI Overbought Level', 70, { min: 1, max: 100 });
const maType = input.select('Moving Average Type', 'sma', constants.ma_types);
const maLength = input.number('Moving Average Length', 50, { min: 1 });
const percentageThreshold = input.number('Distance from MA (%)', 5, { min: 1, max: 100 });
const volumeMultiplier = input.number('Volume Multiplier', 1.2, { min: 1 });
const volumeLength = input.number('Volume Average Length', 20, { min: 1 });

// Calculate indicators
const myRsi = rsi(close, rsiLength);
const myMa = indicators[maType](close, maLength);
const myVolumeAvg = sma(volume, volumeLength);

// Define conditions
const myOversoldConditions = for_every(myRsi, close, myMa, volume, myVolumeAvg,
    (r, c, m, v, va) => 
        r <= rsiOversold &&
        c < m * (1 - percentageThreshold / 100) &&
        v >= va * volumeMultiplier);

const myOverboughtConditions = for_every(myRsi, close, myMa, volume, myVolumeAvg,
    (r, c, m, v, va) => 
        r >= rsiOverbought &&
        c > m * (1 + percentageThreshold / 100) &&
        v >= va * volumeMultiplier);

// Additional confirmation conditions
const myOversoldConfirmation = for_every(myRsi, volume, myVolumeAvg,
    (r, v, va) => 
        r <= rsiOversold &&
        v >= va * volumeMultiplier);

const myOverboughtConfirmation = for_every(myRsi, volume, myVolumeAvg,
    (r, v, va) => 
        r >= rsiOverbought &&
        v >= va * volumeMultiplier);

// Color candles
const myColors = for_every(myOversoldConditions, myOverboughtConditions,
    (oversold, overbought) => 
        oversold ? '#39FF14' :  // Neon Green
        overbought ? '#FF3131' :  // Neon Red
        '#808080');  // Grey for all other candles

color_candles(myColors);

// Register signals
register_signal(myOversoldConditions, 'Bullish Capitulation');
register_signal(myOverboughtConditions, 'Bearish Capitulation');
register_signal(for_every(myOversoldConditions, myOverboughtConditions, (o, b) => !o && !b), 'No Capitulation');
register_signal(myOversoldConfirmation, 'Oversold Confirmation');
register_signal(myOverboughtConfirmation, 'Overbought Confirmation');
</code>