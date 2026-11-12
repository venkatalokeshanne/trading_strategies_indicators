<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volume-Driven Momentum');

// Input for RVOL threshold
const rvolThreshold = input.number('RVOL Threshold', 2, { min: 1 });

// Input for RVOL lookback period
const rvolPeriod = input.number('RVOL Lookback Period', 20, { min: 1 });

// Input for candle colors
const bullishColor = input.color('Bullish Candle Color', 'cyan');
const bearishColor = input.color('Bearish Candle Color', '#FF69B4');

// Calculate RVOL
const myVolumeSMA = sma(volume, rvolPeriod);
const myRVOL = div(volume, myVolumeSMA);

// Function to check if a candle has a large body
const hasLargeBody = (o, h, l, c) => {
    const bodySize = Math.abs(c - o);
    const totalWickSize = (h - l) - bodySize;
    return bodySize >= 2 * totalWickSize;
};

// Determine candle colors based on conditions
const candleColors = for_every(open, high, low, close, myRVOL, (_o, _h, _l, _c, _rvol) => {
    if (_rvol >= rvolThreshold && hasLargeBody(_o, _h, _l, _c)) {
        return _c > _o ? bullishColor : bearishColor;
    }
    return null;
});

// Paint the candles
color_candles(candleColors);

// Register signals for bullish and bearish large body candles
const bullishSignal = for_every(open, high, low, close, myRVOL, (_o, _h, _l, _c, _rvol) => 
    _c > _o && _rvol >= rvolThreshold && hasLargeBody(_o, _h, _l, _c));
register_signal(bullishSignal, 'Bullish Volume-Driven Momentum');

const bearishSignal = for_every(open, high, low, close, myRVOL, (_o, _h, _l, _c, _rvol) => 
    _o > _c && _rvol >= rvolThreshold && hasLargeBody(_o, _h, _l, _c));
register_signal(bearishSignal, 'Bearish Volume-Driven Momentum');</code>