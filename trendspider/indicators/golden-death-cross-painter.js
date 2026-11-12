<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Golden/Death Cross Painter');

// Input for SMA periods
const fastPeriod = input.number('Fast SMA Period', 50, { min: 1 });
const slowPeriod = input.number('Slow SMA Period', 200, { min: 1 });

// Input for candle colors
const myGoldenColor = input.color('Golden Cross Color', 'gold');
const myDeathColor = input.color('Death Cross Color', 'red');
const myNeutralColor = input.color('Neutral Color', 'grey');

// Calculate SMAs
const fastSMA = sma(close, fastPeriod);
const slowSMA = sma(close, slowPeriod);

// Paint SMAs
paint(fastSMA, { name: 'Fast SMA', color: 'blue' });
paint(slowSMA, { name: 'Slow SMA', color: 'purple' });

// Initialize cross state
let myLastCrossState = 'none';

// Function to determine cross state
const myGetCrossState = (fast, slow) => {
    if (fast > slow) return 'golden';
    if (fast < slow) return 'death';
    return 'none';
};

// Determine candle colors and generate signals
const myGoldenSignal = series_of(false);
const myDeathSignal = series_of(false);
const myNeutralSignal = series_of(true);

const myCandleColors = for_every(close, fastSMA, slowSMA, (c, f, s, prevColor, i) => {
    const myCurrentCrossState = myGetCrossState(f, s);
    
    // Detect cross
    if (myCurrentCrossState !== myLastCrossState) {
        myLastCrossState = myCurrentCrossState;
    }
    
    // Golden Cross condition
    if (myLastCrossState === 'golden' && c > f && c > s) {
        myGoldenSignal[i] = true;
        myDeathSignal[i] = false;
        myNeutralSignal[i] = false;
        return myGoldenColor;
    }
    
    // Death Cross condition
    if (myLastCrossState === 'death' && c < f && c < s) {
        myGoldenSignal[i] = false;
        myDeathSignal[i] = true;
        myNeutralSignal[i] = false;
        return myDeathColor;
    }
    
    // No condition met, paint the candles with neutral color
    myGoldenSignal[i] = false;
    myDeathSignal[i] = false;
    myNeutralSignal[i] = true;
    return myNeutralColor;
});

// Register signals
register_signal(myGoldenSignal, 'Golden Cross Bullish');
register_signal(myDeathSignal, 'Death Cross Bearish');
register_signal(myNeutralSignal, 'Neutral');

// Paint candles
color_candles(myCandleColors);</code>