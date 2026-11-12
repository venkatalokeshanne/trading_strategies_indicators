<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fearzone - Contrarian Indicator (Zeiierman)', 'price', { shortName: 'Fearzone (Zeiierman)' });

// Input Settings
const mySource = input.select('Source', 'ohlc4', constants.price_source_options);
const myPrice = market[mySource];
const myHighPeriod = input.number('High Period', 30, { min: 1, max: 500 });
const myStdevPeriod = input.number('Stdev Period', 50, { min: 1, max: 500 });
const myMaType = input.select('Select Moving Average', 'wma', constants.ma_types);

// User settings for alert circles
const myAlertCircle = input.boolean('Show FearZone Circle?', true);
const myAlertCircleColor = input.color('FearZone Circle Color', '#FC6C85');

// User settings for coloring candles when FearZone condition is met
const myColorCandles = input.boolean('Color Candles in FearZone?', true);
const myCandleColor = input.color('Candle Color in FearZone', 'red');

// Function to calculate the selected moving average
const myComputeMA = indicators[myMaType];

// Function to calculate FZ1 values
const myCalcFZ1 = (_source, _highPeriod, _stdevPeriod) => {
    const myHighestSource = highest(_source, _highPeriod);
    const myFZ1 = for_every(_source, myHighestSource, (_s, _h) => (_h - _s) / _h);
    const myAVG1 = myComputeMA(myFZ1, _stdevPeriod);
    const mySTDEV1 = stdev(myFZ1, _stdevPeriod);
    const myFZ1Limit = add(myAVG1, mySTDEV1);
    return { myFZ1, myFZ1Limit };
};

// Function to calculate FZ2 values
const myCalcFZ2 = (_source, _highPeriod, _stdevPeriod) => {
    const myFZ2 = myComputeMA(_source, _highPeriod);
    const myAVG2 = myComputeMA(myFZ2, _stdevPeriod);
    const mySTDEV2 = stdev(myFZ2, _stdevPeriod);
    const myFZ2Limit = sub(myAVG2, mySTDEV2);
    return { myFZ2, myFZ2Limit };
};

// Calculate FZ1 and FZ2
const { myFZ1, myFZ1Limit } = myCalcFZ1(myPrice, myHighPeriod, myStdevPeriod);
const { myFZ2, myFZ2Limit } = myCalcFZ2(myPrice, myHighPeriod, myStdevPeriod);

// FearZone Condition: FZ1 > FZ1Limit and FZ2 < FZ2Limit
const myFearzoneCondition = for_every(
    myFZ1, 
    myFZ1Limit, 
    myFZ2, 
    myFZ2Limit, 
    (_fz1, _fz1Limit, _fz2, _fz2Limit) => _fz1 > _fz1Limit && _fz2 < _fz2Limit
);

// Color candles based on user settings when FearZone condition is met
const myCandleColors = for_every(
    myFearzoneCondition,
    (_condition) => {
        return (_condition && myColorCandles) ? myCandleColor : null;
    }
);
color_candles(myCandleColors);

// Calculate True Range for each candle
const myTrueRange = for_every(high, low, close, (_h, _l, _c, _prevOutput, _index) => {
    if (_index === 0) return _h - _l;
    const myPrevClose = close[_index - 1];
    return Math.max(_h - _l, Math.abs(_h - myPrevClose), Math.abs(_l - myPrevClose));
});

// Calculate bubble positions close to the price
// Creating circular bubbles by painting filled areas
const myBubbleSize = mult(myTrueRange, 0.3);

// Top of bubble: positioned just below the lows
const myBubbleTop = for_every(
    myFearzoneCondition, 
    low, 
    (_condition, _low) => _condition ? _low : null
);

// Bottom of bubble: positioned a small distance below the top
const myBubbleBottom = for_every(
    myFearzoneCondition, 
    low, 
    myBubbleSize,
    (_condition, _low, _bubbleSize) => _condition ? _low - _bubbleSize : null
);

// Circle symbols (●) shown on every bar when FearZone condition is met
const myAlertCircleValues = for_every(
    myFearzoneCondition, 
    (_condition) => {
        return _condition && myAlertCircle ? constants.icons.circle : null;
    }
);
paint(myAlertCircleValues, { 
    style: 'labels_below',
    color: myAlertCircleColor,
    name: 'FearZone Circles' 
});

// Signal for when FearZone condition changes from false to true
const myFearZoneSignal = for_every(
    myFearzoneCondition,
    (_condition, _prevOutput, _index) => {
        if (_index === 0) return false;
        const myPrevCondition = myFearzoneCondition[_index - 1];
        return _condition && !myPrevCondition;
    }
);
register_signal(myFearZoneSignal, 'FearZone detected');
</code>