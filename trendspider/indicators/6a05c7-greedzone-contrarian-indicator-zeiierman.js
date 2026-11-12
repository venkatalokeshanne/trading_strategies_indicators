<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Greedzone - Contrarian Indicator (Zeiierman)', 'price', {
    mainColorInheritFrom: 'text',
    shortName: 'Greedzone (Zeiierman)'
});

// Input Settings
const mySource = input.select('Source', 'ohlc4', constants.price_source_options);
const myPrice = market[mySource];
const myLowPeriod = input.number('Low Period', 30, { min: 1, max: 500 });
const myStdevPeriod = input.number('Stdev Period', 50, { min: 1, max: 500 });
const myMaType = input.select('Select Moving Average', 'wma', constants.ma_types);

// Visual settings
const myShowGreedZoneCircles = input.boolean('Show GreedZone Circles?', true);
const myColorCandles = input.boolean('Color Candles in GreedZone?', true);
const myGreedZoneColor = input.color('GreedZone Color', '#90EE90');

// Function to calculate the selected moving average
const myComputeMA = indicators[myMaType];

// Function to calculate GZ1 values
const myCalcGZ1 = (_source, _lowPeriod, _stdevPeriod) => {
    const myLowestSource = lowest(_source, _lowPeriod);
    const myGZ1 = for_every(_source, myLowestSource, (_s, _l) => (_l - _s) / _l);
    const myAVG1 = myComputeMA(myGZ1, _stdevPeriod);
    const mySTDEV1 = stdev(myGZ1, _stdevPeriod);
    const myGZ1Limit = sub(myAVG1, mySTDEV1);
    return { myGZ1, myGZ1Limit };
};

// Function to calculate GZ2 values
const myCalcGZ2 = (_source, _lowPeriod, _stdevPeriod) => {
    const myGZ2 = myComputeMA(_source, _lowPeriod);
    const myAVG2 = myComputeMA(myGZ2, _stdevPeriod);
    const mySTDEV2 = stdev(myGZ2, _stdevPeriod);
    const myGZ2Limit = add(myAVG2, mySTDEV2);
    return { myGZ2, myGZ2Limit };
};

// Calculate GZ1 and GZ2
const { myGZ1, myGZ1Limit } = myCalcGZ1(myPrice, myLowPeriod, myStdevPeriod);
const { myGZ2, myGZ2Limit } = myCalcGZ2(myPrice, myLowPeriod, myStdevPeriod);

// GreedZone Condition: GZ1 < GZ1Limit and GZ2 > GZ2Limit
const myGreedzoneCondition = for_every(
    myGZ1,
    myGZ1Limit,
    myGZ2,
    myGZ2Limit,
    (_gz1, _gz1Limit, _gz2, _gz2Limit) => _gz1 < _gz1Limit && _gz2 > _gz2Limit
);

// Color candles based on user settings when GreedZone condition is met
const myCandleColors = for_every(
    myGreedzoneCondition,
    (_condition) => {
        return (_condition && myColorCandles) ? myGreedZoneColor : null;
    }
);

color_candles(myCandleColors);

// Circle symbols shown on every bar when GreedZone condition is met
const myAlertCircleValues = for_every(
    myGreedzoneCondition,
    (_condition) => {
        return (_condition && myShowGreedZoneCircles) ? constants.icons.circle : null;
    }
);

paint(myAlertCircleValues, {
    style: 'labels_above',
    color: myGreedZoneColor,
    name: 'GreedZone Circles'
});

// Signal for when GreedZone condition changes from false to true
const myGreedZoneSignal = for_every(
    myGreedzoneCondition,
    (_condition, _prevOutput, _index) => {
        if (_index === 0) return false;
        const myPrevCondition = myGreedzoneCondition[_index - 1];
        return _condition && !myPrevCondition;
    }
);

register_signal(myGreedZoneSignal, 'GreedZone detected');</code>