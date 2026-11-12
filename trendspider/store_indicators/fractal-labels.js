<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fractal Labels with Recent Lines (H,L)', 'price');

// Set the window length for identifying fractal highs and lows
const myFractalLength = input.number('Fractal Length', 21, { min: 3 });
const myNumRecentFractals = input.number('Number of Recent Fractals', 20, { min: 1, max: 50 });

// Identify the fractal highs
const myFractalHighs = fractal_high(high, myFractalLength);

// Identify the fractal lows
const myFractalLows = fractal_low(low, myFractalLength);

// Function to assign letters to recent fractals
const assignLetters = (fractals) => {
    const recentFractals = [];
    let letterCode = 65; // ASCII code for 'A'
    for (let i = fractals.length - 1; i >= 0 && recentFractals.length < myNumRecentFractals; i--) {
        if (fractals[i] !== null) {
            recentFractals.push({ index: i, value: fractals[i], letter: String.fromCharCode(letterCode) });
            letterCode++;
        }
    }
    return recentFractals;
};

// Get the most recent fractal highs and lows with assigned letters
const myRecentHighs = assignLetters(myFractalHighs);
const myRecentLows = assignLetters(myFractalLows);

// Prepare labels for fractal highs
const myFractalHighsLabels = for_every(myFractalHighs, (_h, _prevH, _i) => {
    if (_h === null) return null;
    const recentHigh = myRecentHighs.find(rh => rh.index === _i);
    if (recentHigh) {
        return `H-${recentHigh.letter}`;
    }
    return null;
});

// Prepare labels for fractal lows
const myFractalLowsLabels = for_every(myFractalLows, (_l, _prevL, _i) => {
    if (_l === null) return null;
    const recentLow = myRecentLows.find(rl => rl.index === _i);
    if (recentLow) {
        return `L-${recentLow.letter}`;
    }
    return null;
});

// Paint labels above the fractal highs
paint(myFractalHighsLabels, { style: 'labels_above', color: 'blue' });

// Paint labels below the fractal lows
paint(myFractalLowsLabels, { style: 'labels_below', color: 'red' });

</code>