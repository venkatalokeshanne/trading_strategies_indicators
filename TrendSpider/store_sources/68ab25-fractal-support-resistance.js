<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fractal Support & Resistance', 'price', { 
    decimals: 'by_symbol', 
    shortName: 'Frac.SR' 
});

const length = input('Fractal Length', 5, { min: 3, max: 21 });
const showLevels = input('Show Levels', 29, { min: 1, max: 70 });

const fractalHighs = fractal_high(high, length);
const fractalLows = fractal_low(low, length);

const indexedHighs = indexed_points_of(fractalHighs);
const indexedLows = indexed_points_of(fractalLows);

const fractalHighDots = series_of(null);
const fractalLowDots = series_of(null);

// Support levels (from fractal lows)
const supportLevels = [];
for (let i = 0; i < showLevels && i < indexedLows.length; i++) {
    const fractalLow = indexedLows[indexedLows.length - 1 - i];
    fractalLowDots[fractalLow.candleIndex] = fractalLow.value;
    supportLevels.push(horizontal_line(fractalLow.value, fractalLow.candleIndex));
}

// Resistance levels (from fractal highs)  
const resistanceLevels = [];
for (let i = 0; i < showLevels && i < indexedHighs.length; i++) {
    const fractalHigh = indexedHighs[indexedHighs.length - 1 - i];
    fractalHighDots[fractalHigh.candleIndex] = fractalHigh.value;
    resistanceLevels.push(horizontal_line(fractalHigh.value, fractalHigh.candleIndex));
}

// Paint fractal dots
paint(fractalHighDots, 'Fractal Highs', '#ee5451', 'dotted', 3);
paint(fractalLowDots, 'Fractal Lows', '#2ca599', 'dotted', 3);

// Paint support levels
for (let i = 0; i < supportLevels.length; i++) {
    const alpha = 100 - (i * 2); // Fade older levels
    paint(supportLevels[i], `Support ${i + 1}`, `#2ca599${alpha.toString(16).padStart(2, '0')}`);
}

// Paint resistance levels
for (let i = 0; i < resistanceLevels.length; i++) {
    const alpha = 100 - (i * 2); // Fade older levels  
    paint(resistanceLevels[i], `Resistance ${i + 1}`, `#ee5451${alpha.toString(16).padStart(2, '0')}`);
}</code>