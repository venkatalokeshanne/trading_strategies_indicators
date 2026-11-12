<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Bearish Doji Candle Identifier', 'price');

// Input for Doji body size tolerance (as a percentage of the candle's range)
const myDojiTolerance = input.number('Doji Tolerance (%)', 5, { min: 0, max: 20, step: 0.1 });

// Input for minimum candle size (as a percentage of the average true range)
const myMinCandleSize = input.number('Min Candle Size (% ATR)', 50, { min: 10, max: 200, step: 5 });

// Calculate ATR for reference
const myAtrLength = 14;
const myAtr = atr(high, low, close, myAtrLength);

// Function to identify a bearish doji candle
const isBearishDoji = (_open, _high, _low, _close, _atr, _index) => {
    const myRange = _high - _low;
    const myBody = Math.abs(_open - _close);
    const myBodyPercentage = (myBody / myRange) * 100;
    const myCandleSizePercentage = (myRange / _atr) * 100;
    
    return _close < _open && // Bearish
           myBodyPercentage <= myDojiTolerance && // Doji
           myCandleSizePercentage >= myMinCandleSize && // Significant size
           _high > Math.max(_open, _close) && // Upper wick
           _low < Math.min(_open, _close); // Lower wick
};

// Identify bearish doji candles
const myBearishDoji = for_every(open, high, low, close, myAtr, (_o, _h, _l, _c, _atr, _i) => 
    isBearishDoji(_o, _h, _l, _c, _atr, _i) ? _l : null);

// Paint bearish doji candles
paint(myBearishDoji, {
    name: 'Bearish Doji',
    color: 'red',
    style: 'labels_below',
    text: '▼'
});

// Add labels for each bearish doji
const lineRef = paint(myBearishDoji);
for (let i = 0; i < myBearishDoji.length; i++) {
    if (myBearishDoji[i] !== null) {
        paint_label_at_line(
            lineRef,
            i,
            'Bearish Doji',
            { color: 'white', background_color: 'red', border_color: 'darkred', vertical_align: 'bottom' }
        );
    }
}
</code>