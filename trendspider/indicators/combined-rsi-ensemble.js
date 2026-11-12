<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Combined RSI Ensemble');

// Input for RSI levels
const OVERBOUGHT_LEVEL = input.number('Overbought Level', 80, { min: 50, max: 100 });
const OVERSOLD_LEVEL = input.number('Oversold Level', 30, { min: 0, max: 50 });

// Inputs for colors
const COLOR_SURELY_OVERBOUGHT = input.color('Surely Overbought Color', '#ff0000');
const COLOR_PROBABLY_OVERBOUGHT = input.color('Probably Overbought Color', '#ffa500');
const COLOR_SLIGHTLY_OVERBOUGHT = input.color('Slightly Overbought Color', '#ffff00');
const COLOR_SURELY_OVERSOLD = input.color('Surely Oversold Color', '#00ff3c');
const COLOR_PROBABLY_OVERSOLD = input.color('Probably Oversold Color', '#2ecc53');
const COLOR_SLIGHTLY_OVERSOLD = input.color('Slightly Oversold Color', '#c4e0a3');
const COLOR_NEUTRAL = input.color('Neutral Color', 'gray');

const rsi14 = rsi(close, 14);
const rsi9 = rsi(close, 9);
const rsi5 = rsi(close, 5);

const scoreRSI = (rsi, threshold, isOverbought) => {
    return for_every(rsi, r => isOverbought ? (r > threshold ? 1 : 0) : (r < threshold ? 1 : 0));
};

const overboughtScore = add(
    scoreRSI(rsi14, OVERBOUGHT_LEVEL, true),
    scoreRSI(rsi9, OVERBOUGHT_LEVEL, true),
    scoreRSI(rsi5, OVERBOUGHT_LEVEL, true)
);

const oversoldScore = add(
    scoreRSI(rsi14, OVERSOLD_LEVEL, false),
    scoreRSI(rsi9, OVERSOLD_LEVEL, false),
    scoreRSI(rsi5, OVERSOLD_LEVEL, false)
);

const candleColors = for_every(overboughtScore, oversoldScore, (ob, os) => {
    if (os > 0) {
        return os === 3 ? COLOR_SURELY_OVERSOLD : os === 2 ? COLOR_PROBABLY_OVERSOLD : COLOR_SLIGHTLY_OVERSOLD;
    } else if (ob > 0) {
        return ob === 3 ? COLOR_SURELY_OVERBOUGHT : ob === 2 ? COLOR_PROBABLY_OVERBOUGHT : COLOR_SLIGHTLY_OVERBOUGHT;
    }
    return COLOR_NEUTRAL;
});

color_candles(candleColors);

// Define signals for different conditions
const mySurelyOverbought = for_every(overboughtScore, s => s === 3);
const myProbablyOverbought = for_every(overboughtScore, s => s === 2);
const mySlightlyOverbought = for_every(overboughtScore, s => s === 1);
const mySurelyOversold = for_every(oversoldScore, s => s === 3);
const myProbablyOversold = for_every(oversoldScore, s => s === 2);
const mySlightlyOversold = for_every(oversoldScore, s => s === 1);
const myNeutral = for_every(overboughtScore, oversoldScore, (ob, os) => ob === 0 && os === 0);

// Register signals for use in strategy tester and scanner
register_signal(mySurelyOverbought, 'Surely Overbought');
register_signal(myProbablyOverbought, 'Probably Overbought');
register_signal(mySlightlyOverbought, 'Slightly Overbought');
register_signal(mySurelyOversold, 'Surely Oversold');
register_signal(myProbablyOversold, 'Probably Oversold');
register_signal(mySlightlyOversold, 'Slightly Oversold');
register_signal(myNeutral, 'Neutral');</code>