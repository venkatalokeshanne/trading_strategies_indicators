<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('LRI Pivot');

// Input for Linear Regression length
const myLength = input.number('LR Length', 17, { min: 1 });

// Input for delay
const myDelay = input.number('Delay', 16, { min: 0 });

// Input for EMA length
const myEmaLength = input.number('EMA Length', 13, { min: 1 });

// Input for LRI smoothing
const myLriSmoothLength = input.number('LRI Smooth Length', 5, { min: 1 });

// Calculate Linear Regression Intercept
const myLri = linreg(close, myLength);

// Smooth the LRI using EMA
const mySmoothLri = ema(myLri, myLriSmoothLength);

// Shift the smoothed LRI by the delay amount
const myShiftedLri = shift(mySmoothLri, myDelay);

// Calculate EMA
const myEma = ema(close, myEmaLength);

// Initialize color series
const myColors = series_of(null);

// Determine candle colors based on price position relative to shifted LRI and EMA
for (let i = Math.max(myDelay, myEmaLength, myLriSmoothLength, 1); i < close.length; i++) {
    if (
        (close[i] > myShiftedLri[i] && close[i - 1] <= myShiftedLri[i - 1]) ||
        (close[i] < myShiftedLri[i] && close[i - 1] >= myShiftedLri[i - 1])
    ) {
        // Candle crosses through the LRI
        myColors[i] = 'orange';
    } else if (close[i] > myShiftedLri[i] && close[i] > myEma[i]) {
        // Price above LRI and above EMA
        myColors[i] = 'darkgreen';
    } else if (close[i] > myShiftedLri[i] && close[i] <= myEma[i]) {
        // Price above LRI but below or equal to EMA
        myColors[i] = 'lightgreen';
    } else if (close[i] <= myShiftedLri[i] && close[i] > myEma[i]) {
        // Price below or equal to LRI but above EMA
        myColors[i] = 'pink';
    } else {
        // Price below or equal to LRI and below or equal to EMA
        myColors[i] = 'darkred';
    }
}

// Paint the shifted and smoothed LRI line
paint(myShiftedLri, { color: 'purple', name: 'Shifted Smoothed LRI' });

// Paint the EMA line
paint(myEma, { color: 'white', name: '13 EMA' });

// Color the candles
color_candles(myColors);
</code>