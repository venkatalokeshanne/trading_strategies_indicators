<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('MA Channel');

// User inputs for MA type and length
const maType = input.select('MA Type', 'sma', constants.ma_types);
const length = input.number('Length', 20, { min: 1, max: 300 });

// Get the selected MA function
const computeMA = indicators[maType];

// Calculate MAs based on high, close, and low
const maHigh = computeMA(high, length);
const maClose = computeMA(close, length);
const maLow = computeMA(low, length);

// Paint the three MAs
paint(maHigh, { name: 'MA High', color: '#2962ff', style: 'line' });
paint(maClose, { name: 'MA Close', color: '#787b86', style: 'line' });
paint(maLow, { name: 'MA Low', color: '#f23645', style: 'line' });

// Fill the channel areas
fill(
    paint(maHigh, { hidden: true }),
    paint(maClose, { hidden: true }),
    '#2962ff',
    0.1
);

fill(
    paint(maClose, { hidden: true }),
    paint(maLow, { hidden: true }),
    '#f23645',
    0.1
);
</code>