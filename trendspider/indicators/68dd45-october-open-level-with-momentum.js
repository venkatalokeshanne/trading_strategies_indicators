<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('October Open Level with Momentum');

// Input for line color
const lineColor = input.color('Line Color', 'teal');

// Input to toggle candle coloring
const colorCandles = input.boolean('Color Candles', true);

// Input for candle colors
const candleColorPositiveMomentum = input.color('Candle Color (Positive Momentum)', 'lightgreen');
const candleColorZeroMomentum = input.color('Candle Color (Zero Momentum)', 'darkgreen');
const candleColorNegativeMomentum = input.color('Candle Color (Negative Momentum)', 'green');
const candleColorTouchingLevel = input.color('Candle Color (Touching Level)', '#39FF14'); // Neon Green

// Input for momentum length
const momentumLength = input.number('Momentum Length', 14, { min: 1, max: 50 });

// Function to check if a given timestamp is in October
const isOctober = (timestamp) => {
    const date = time_of(timestamp);
    return date.month === 10; // October is 10 in time_of() function
};

// Find October open levels
const octoberOpenLevels = [];
let currentOctoberOpen = null;
let currentYear = null;
for (let i = 0; i < time.length; i++) {
    const date = time_of(time[i]);
    if (isOctober(time[i])) {
        if (currentOctoberOpen === null) {
            currentOctoberOpen = open[i];
            currentYear = date.year;
            octoberOpenLevels.push({ startIndex: i, level: currentOctoberOpen, year: currentYear });
        }
    } else {
        currentOctoberOpen = null;
    }
}

// Create series for painting
const levelSeries = series_of(null);

// Fill the series with October open levels
for (let i = 0; i < octoberOpenLevels.length; i++) {
    const currentLevel = octoberOpenLevels[i];
    const nextLevel = octoberOpenLevels[i + 1];
    
    const endIndex = nextLevel ? nextLevel.startIndex - 1 : time.length - 1;
    
    for (let j = currentLevel.startIndex; j <= endIndex; j++) {
        levelSeries[j] = currentLevel.level;
    }
}

// Paint the October open level
const lineId = paint(levelSeries, { 
    name: 'October Open Level',
    color: lineColor,
    style: 'line'
});

// Add year labels at the start and end of each October level
for (let i = 0; i < octoberOpenLevels.length; i++) {
    const currentLevel = octoberOpenLevels[i];
    const nextLevel = octoberOpenLevels[i + 1];
    
    const endIndex = nextLevel ? nextLevel.startIndex - 1 : time.length - 1;
    
    // Label at the start of the level
    paint_label_at_line(lineId, currentLevel.startIndex, currentLevel.year.toString(), {
        color: lineColor,
        vertical_align: 'top'
    });
    
    // Label at the end of the level
    paint_label_at_line(lineId, endIndex, currentLevel.year.toString(), {
        color: lineColor,
        vertical_align: 'bottom'
    });
}

// Calculate momentum
const myMomentum = momentum(close, momentumLength);

// Color candles when price is at or below the October open level, considering momentum and touching the level
if (colorCandles) {
    const candleColors = for_every(close, high, low, levelSeries, myMomentum, (_close, _high, _low, _level, _momentum) => {
        if (_level !== null) {
            if (_high >= _level && _low <= _level) {
                return candleColorTouchingLevel;
            } else if (_close <= _level) {
                if (_momentum > 0) {
                    return candleColorPositiveMomentum;
                } else if (_momentum < 0) {
                    return candleColorNegativeMomentum;
                } else {
                    return candleColorZeroMomentum;
                }
            }
        }
        return null;
    });
    color_candles(candleColors);
} else {
    color_candles(series_of(null));
}
</code>