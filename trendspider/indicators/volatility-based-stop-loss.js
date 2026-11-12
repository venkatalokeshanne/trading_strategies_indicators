<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volatility-Based Stop Loss');

// This is an experimental indicator based on the given request.
// It's designed to provide a visual guide for potential exit points
// in trending markets, but please use it with caution and in conjunction
// with other analysis methods.

const length = input.number('ATR Length', 14, { min: 1 });
const multiplier = input.number('ATR Multiplier', 2, { min: 0.1, step: 0.1 });

const myAtr = atr(length);
const stopLoss = series_of(null);

for_every(close, myAtr, (c, a, prev, i) => {
    if (i === 0) {
        stopLoss[i] = c - a * multiplier;
    } else {
        const prevStop = stopLoss[i - 1];
        if (c > prevStop) {
            // In an uptrend
            stopLoss[i] = Math.max(c - a * multiplier, prevStop);
        } else {
            // In a downtrend
            stopLoss[i] = Math.min(c + a * multiplier, prevStop);
        }
    }
});

const stopColor = for_every(close, stopLoss, (c, s) => 
    c > s ? 'green' : 'red'
);

paint(stopLoss, { 
    name: 'Volatility Stop', 
    color: stopColor, 
    style: 'line', 
    linewidth: 2 
});</code>