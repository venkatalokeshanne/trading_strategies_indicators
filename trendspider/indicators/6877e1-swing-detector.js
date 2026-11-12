<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Swing Detector');

// Input for swing type selection
const swingType = input.select('Swing Type', 'Both', ['Bullish', 'Bearish', 'Both']);

const myBullishSwing = series_of(false);
const myBearishSwing = series_of(false);

for (let i = 2; i < close.length; i++) {
    // Bullish Swing Pattern
    if ((swingType === 'Bullish' || swingType === 'Both') &&
        low[i-1] < low[i-2] && close[i-1] > low[i-2] && close[i] > high[i-1]) {
        myBullishSwing[i-2] = true;
        myBullishSwing[i-1] = true;
        myBullishSwing[i] = true;
    }
    // Bearish Swing Pattern
    else if ((swingType === 'Bearish' || swingType === 'Both') &&
             high[i-1] > high[i-2] && close[i-1] < high[i-2] && close[i] < low[i-1]) {
        myBearishSwing[i-2] = true;
        myBearishSwing[i-1] = true;
        myBearishSwing[i] = true;
    }
}

const myCandleColors = for_every(myBullishSwing, myBearishSwing, (_bull, _bear) => {
    if (_bull && (swingType === 'Bullish' || swingType === 'Both')) return '#39FF14'; // Neon Green
    if (_bear && (swingType === 'Bearish' || swingType === 'Both')) return '#FF3131'; // Neon Red
    return 'grey';
});

color_candles(myCandleColors);

// Register signals for scanning
register_signal(myBullishSwing, 'Bullish Swing');
register_signal(myBearishSwing, 'Bearish Swing');</code>