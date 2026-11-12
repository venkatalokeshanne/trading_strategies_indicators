<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Drawdown from ATH %', 'lower');

// Calculate the all-time high for each candle
const myAllTimeHigh = for_every(close, (_close, _prevATH) => {
    if (_prevATH === null) {
        return _close;
    }
    return Math.max(_close, _prevATH);
});

// Calculate the drawdown percentage from ATH
const myDrawdownPercent = for_every(close, myAllTimeHigh, (_close, _ath) => {
    return ((_close - _ath) / _ath) * 100;
});

// Paint the drawdown as a red area chart (stacked column)
paint(myDrawdownPercent, { 
    name: 'Drawdown %', 
    color: '#ff3333', 
    style: 'stacked_column' 
});

// Paint a zero line for reference
paint(horizontal_line(0), { 
    name: 'Zero Line', 
    color: 'gray', 
    style: 'dotted' 
});
</code>