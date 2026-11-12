<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Ichimoku TK Crossover Candle Coloring');

// Input parameters for Ichimoku Cloud
const conversionPeriods = input.number('Conversion Line Periods', 9, { min: 1 });
const basePeriods = input.number('Base Line Periods', 26, { min: 1 });
const laggingSpan2Periods = input.number('Lagging Span 2 Periods', 52, { min: 1 });
const displacement = input.number('Displacement', 26, { min: 1 });

// Calculate Ichimoku Cloud components
const donchian = (myHigh, myLow, length) => {
    const myHighest = highest(myHigh, length);
    const myLowest = lowest(myLow, length);
    return div(add(myHighest, myLowest), 2);
};

const tenkanSen = donchian(high, low, conversionPeriods);
const kijunSen = donchian(high, low, basePeriods);

// Determine crossovers
const bullishCross = for_every(tenkanSen, kijunSen, (_tenkan, _kijun, _prevCross, i) => {
    if (i === 0) return false;
    return tenkanSen[i] > kijunSen[i] && tenkanSen[i - 1] <= kijunSen[i - 1];
});

const bearishCross = for_every(tenkanSen, kijunSen, (_tenkan, _kijun, _prevCross, i) => {
    if (i === 0) return false;
    return tenkanSen[i] < kijunSen[i] && tenkanSen[i - 1] >= kijunSen[i - 1];
});

// Determine candle colors
const myColors = for_every(bullishCross, bearishCross, (_bull, _bear, _prevColor, i) => {
    if (i === 0) return null;
    if (bullishCross[i]) return 'cyan';
    if (bearishCross[i]) return '#DDA0DD'; // Lighter shade of purple (Plum)
    return _prevColor;
});

// Paint the candles
color_candles(myColors);

// Paint Ichimoku Cloud components for reference
paint(tenkanSen, { color: 'red', name: 'Tenkan-sen' });
paint(kijunSen, { color: 'blue', name: 'Kijun-sen' });

// Register signals for scanner / strategy
register_signal(bullishCross, 'Bullish Ichimoku Cross');
register_signal(bearishCross, 'Bearish Ichimoku Cross');
</code>