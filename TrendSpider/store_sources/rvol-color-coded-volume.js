<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('RVOL Color-Coded Volume', 'lower');

// Input parameters
const lookbackPeriod = input.number('RVOL Lookback Period', 20, { min: 5, max: 100 });
const moderateThreshold = input.number('Moderate RVOL Threshold', 1.0, { min: 0.5, max: 2.0, step: 0.1 });
const highThreshold = input.number('High RVOL Threshold', 2.0, { min: 1.0, max: 3.0, step: 0.1 });
const extremeThreshold = input.number('Extreme RVOL Threshold', 3.0, { min: 2.0, max: 5.0, step: 0.1 });

// Color inputs
const lowRvolColor = input.color('Low RVOL Color', '#808080'); // Neutral gray
const moderateBullishColor = input.color('Moderate Bullish RVOL Color', '#8fc9f9'); // Light blue
const highBullishColor = input.color('High Bullish RVOL Color', '#0da8f4'); // Bright blue
const extremeBullishColor = input.color('Extreme Bullish RVOL Color', '#00ffff'); // Cyan
const moderateBearishColor = input.color('Moderate Bearish RVOL Color', '#FF6666'); // Light red
const highBearishColor = input.color('High Bearish RVOL Color', '#FF0000'); // Bright red
const extremeBearishColor = input.color('Extreme Bearish RVOL Color', '#FF1493'); // Neon pink

// Calculate Volume Moving Average (VMA)
const myVma = sma(volume, lookbackPeriod);

// Calculate RVOL
const myRvol = div(volume, myVma);

// Function to determine volume color based on RVOL and price action
const getVolumeColor = (rvolValue, openPrice, closePrice) => {
    if (rvolValue < moderateThreshold) return lowRvolColor;
    if (closePrice > openPrice) { // Bullish
        if (rvolValue >= extremeThreshold) return extremeBullishColor;
        if (rvolValue >= highThreshold) return highBullishColor;
        return moderateBullishColor;
    } else if (closePrice < openPrice) { // Bearish
        if (rvolValue >= extremeThreshold) return extremeBearishColor;
        if (rvolValue >= highThreshold) return highBearishColor;
        return moderateBearishColor;
    }
    return lowRvolColor; // Neutral (close = open)
};

// Generate color series for volume
const myVolumeColors = for_every(myRvol, open, close, (_rvol, _open, _close) => 
    getVolumeColor(_rvol, _open, _close));

// Paint the volume with colors in a lower indicator
paint(volume, { style: 'column', color: myVolumeColors, name: 'Colored Volume' });

// Register signals for scanning and alerts
register_signal(for_every(myRvol, _r => _r >= moderateThreshold), 'Moderate RVOL');
register_signal(for_every(myRvol, _r => _r >= highThreshold), 'High RVOL');
register_signal(for_every(myRvol, _r => _r >= extremeThreshold), 'Extreme RVOL');

// Additional signals for bullish and bearish extreme RVOL
register_signal(
    for_every(myRvol, close, open, (_r, _c, _o) => _r >= extremeThreshold && _c > _o),
    'Extreme Bullish RVOL');
register_signal(
    for_every(myRvol, close, open, (_r, _c, _o) => _r >= extremeThreshold && _c < _o),
    'Extreme Bearish RVOL');</code>